from twisted.internet import defer
from twisted.internet import error

from buildbot.plugins import *
from buildbot.status.results import *
from buildbot.process import remotecommand
from buildbot.process import logobserver
from buildbot.process import buildstep

import subprocess
import networkx as nx
import os.path
import re

class CleanChrootAction(buildstep.ShellMixin, steps.BuildStep):
    
    def __init__(self, arch, command, **kwargs):
        steps.BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        
        self.bits = '32' if arch == 'i686' else '64'
        self.command = command
        self.arch = arch
        self.name = 'ccm{} {}'.format(self.bits, self.command)

    @defer.inlineCallbacks
    def run(self):  ## new style
        cmd = yield self.makeCCMCommand(self.command)
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        else:
            defer.returnValue(SUCCESS)

    def makeCCMCommand(self, command):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command=['sudo', 'ccm' + self.bits, command])

    def getCurrentSummary(self):
        return {u'step': u'running'}

    def getResultSummary(self):
        return {u'step': u'success'}


class ArchPackage(CleanChrootAction):
    artifacts = []
    current = False
    
    def __init__(self, name, arch, depends, provides, **kwargs):
        CleanChrootAction.__init__(self, 
                arch=arch, command='s',
                description='building package',
                workdir='build/packages/' + name, **kwargs)
        
        self.name = 'pkg/' + name
        self.package = name
        self.depends = depends
        self.provides = provides

    @defer.inlineCallbacks
    def run(self):  ## new style
        log = yield self.addLog('logs')

        yield log.addStdout(u'Provides: {}\n'.format(self.provides))
        yield log.addStdout(u'Dependencies: {}\n'.format(self.depends))

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, stdioLogName=None,
                command=['pkgver', '--latest'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        # /srv/http/repos/papyros/x86_64/greenisland-git-20150428.e41b7b3-1-x86_64.pkg.tar.xz
        self.latest_version = cmd.stdout.strip()
        yield log.addStdout(u'Latest version: {}\n'.format(self.latest_version))

        self.package_file = self.package + '-' + self.latest_version + '-' + self.arch + '.pkg.tar.xz'
        yield log.addStdout(u'Package file: {}\n'.format(self.package_file))

        if self.alreadyBuilt():
            self.current = True
            yield log.addStdout(u'Package already built!\n')
        else:
            cmd = yield self.makeCCMCommand('s')
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            cmd = yield self.makeRemoteShellCommand(collectStdout=True,
                command='ls')
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            r = re.compile(r'.*\-{}\-{}\.pkg\.tar\.xz'.format(self.latest_version, self.arch))
            self.artifacts = filter(r.match, cmd.stdout.split())

            if len(self.artifacts) == 0:
                yield log.addStdout(u'Error: no packages built!\n')
                defer.returnValue(FAILURE)

            yield log.addStdout(u'Built the following packages: {}\n'.format(self.artifacts))

            for pkg in self.artifacts:
                # Copy the built packages
                cmd = yield self.makeRemoteShellCommand(collectStdout=True,
                    command=('cp {0} ../../built_packages'.format(pkg)))
                yield self.runCommand(cmd)
                if cmd.didFail():
                    defer.returnValue(FAILURE)
                cmd = yield self.makeRemoteShellCommand(collectStdout=True,
                    command=('repo-add ../../built_packages/papyros.db.tar.gz ' +
                            '../../built_packages/{0}'.format(pkg)))
                yield self.runCommand(cmd)
                if cmd.didFail():
                    defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def alreadyBuilt(self):
        existing_packages = self.getProperty('existing_packages')
        return self.package_file in existing_packages

    def getCurrentSummary(self):
        return {u'step': u'building'}

    def getResultSummary(self):
        if self.current:
            return {u'step': u'skipped'}
        elif len(self.artifacts) == 0:
            return {u'step': u'failed'}
        else:
            return {u'step': u'built'}


class ScanRepository(buildstep.ShellMixin, steps.BuildStep):
    name = "scan_repo"
    description = "generating package steps"
    pkgs = None

    def __init__(self, arch, **kwargs):
        self.arch = arch

        kwargs = self.setupShellMixin(kwargs, prohibitArgs=['command'])
        steps.BuildStep.__init__(self, **kwargs)

    @defer.inlineCallbacks
    def run(self):  ## new style
        log = yield self.addLog('logs')

        # Get already built packages

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command=['ls', 'built_packages'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        prebuilt_packages = cmd.stdout.split()
        self.setProperty("existing_packages", prebuilt_packages, "Repository Scan")

        # Generate a list of packages

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command=['find', '-name', 'PKGBUILD', '-printf', '%h\\n'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        # Create steps for the packages

        self.pkgs = [os.path.basename(path) for path in cmd.stdout.split()]

        pkg_info = []
        
        for pkgname in self.pkgs:

            # Get the dependencies for the package
            cmd = yield self.makeRemoteShellCommand(collectStdout=True, stdioLogName=None,
                command=['pkgdeps'], workdir=self.workdir + '/packages/' + pkgname)
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            depends = cmd.stdout.split()

            # Get the package names this package provides
            cmd = yield self.makeRemoteShellCommand(collectStdout=True, stdioLogName=None,
                command=['pkgprovides'], workdir=self.workdir + '/packages/' + pkgname)
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            provides = cmd.stdout.split()

            pkg_info.append({
                'name': pkgname,
                'depends': depends,
                'provides': provides
            })

        # Update the list of dependencies for each package, removing system-provided ones
        for job in pkg_info:
            new_deps = []
            for dep in job['depends']:
                providers = [pkg for pkg in pkg_info if dep in pkg['provides'] or pkg['name'] == dep]
                if len(providers) > 0:
                    new_deps.append(providers[0]['name'])
            job['depends'] = new_deps

        # Now sort the packages based on their dependencies

        job_names = [job['name'] for job in pkg_info]

        graph = nx.DiGraph()
    
        for job in pkg_info:
            if len(job['depends']) == 0:
                graph.add_node(job['name'])
            else:
                for dependency in job['depends']:
                    graph.add_edge(dependency, job['name'])

        sorted_package_names = nx.topological_sort(graph)

        steps = []

        for name in sorted_package_names:
            info = pkg_info[job_names.index(name)]
            steps.append(ArchPackage(name,self.arch,
                    depends=info['depends'],provides=info['provides']))

        yield log.addStdout(u'Sorted packages: {}\n'.format(sorted_package_names))

        self.build.addStepsAfterCurrentStep(steps)
        self.setProperty("packages", sorted_package_names, "Repository Scan")

        log.finish()

        if len(self.pkgs) == 0:
            defer.returnValue(WARNINGS)  # Warn if no packages found
        else:
            defer.returnValue(SUCCESS)

    def getCurrentSummary(self):
        return {u'step': u'scanning packages'}

    def getResultSummary(self):
        return {u'step': u'{} packages'.format(len(self.pkgs))}


class ArchRepositoryFactory(util.BuildFactory):
    def __init__(self, source, arch):
        util.BuildFactory.__init__(self, [source])


        self.addStep(steps.ShellCommand(command='mkdir -p built_packages'))
        self.addStep(CleanChrootAction(arch, 'u'))
        self.addStep(ScanRepository(arch))
        self.addStep(steps.DirectoryUpload('built_packages', '/srv/http/repos/papyros/' + arch))
