import itertools
import os
import re
import urllib
import subprocess
import networkx as nx
import os.path
import re
import time

from twisted.internet import defer
from twisted.internet import error
from twisted.internet import utils
from twisted.python import log

from buildbot.plugins import *
from buildbot.status.results import *
from buildbot.process import remotecommand
from buildbot.process import logobserver
from buildbot.process import buildstep
from buildbot import config
from buildbot.changes import base
from buildbot.util import ascii2unicode
from buildbot.util.state import StateMixin

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

        # Get the latest package version and check if it has already been built

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, stdioLogName=None,
                command=['pkgver', '--latest'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        self.latest_version = cmd.stdout.strip()
        
        self.package_file = self.package + '-' + self.latest_version + '-' + self.arch + '.pkg.tar.xz'
        
        yield log.addStdout(u'Latest version: {}\n'.format(self.latest_version))
        yield log.addStdout(u'Expected package file: {}\n'.format(self.package_file))

        r = re.compile(r'{}.*\-.*\-{}\.pkg\.tar\.xz'.format(self.package, self.arch))
        already_built_packages = filter(r.match, self.getProperty('existing_packages'))

        yield log.addStdout(u'Existing packages: {}\n'.format(already_built_packages))

        r = re.compile(r'{}.*\-{}\-{}\.pkg\.tar\.xz'.format(self.package, self.latest_version, self.arch))
        already_built_same_version = filter(r.match, self.getProperty('existing_packages'))

        if len(already_built_same_version) > 0:
            self.current = True
            yield log.addStdout(u'Package already built, skipping!\n')
        else:

            # Build the package

            cmd = yield self.makeCCMCommand('s')
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            # Collect the built package artifacts

            cmd = yield self.makeRemoteShellCommand(collectStdout=True,
                command='ls')
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            r = re.compile(r'.*\-{}\-{}\.pkg\.tar\.xz'.format(self.latest_version, self.arch))
            self.artifacts = filter(r.match, cmd.stdout.split())

            r = re.compile(r'.*\-.*\-{}\.pkg\.tar\.xz'.format(self.arch))
            already_built_packages = filter(r.match, cmd.stdout.split())

            yield log.addStdout(u'Packages after building: {}\n'.format(already_built_packages))

            if len(self.artifacts) == 0:
                yield log.addStdout(u'Error: no packages built!\n')
                defer.returnValue(FAILURE)

            yield log.addStdout(u'Built the following packages: {}\n'.format(self.artifacts))

            # Copy the built packages
                
            for pkg in self.artifacts:
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

    def getCurrentSummary(self):
        return {u'step': u'building'}

    def getResultSummary(self):
        if self.current:
            return {u'step': u'skipped'}
        elif len(self.artifacts) == 0:
            return {u'step': u'failed'}
        else:
            return {u'step': u'built'}


class PushRepositoryChanges(buildstep.ShellMixin, steps.BuildStep):
    name = "push_changes"

    def __init__(self, arch, **kwargs):
        self.arch = arch 
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=['command'])
        steps.BuildStep.__init__(self, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog('logs')

        # Get a list of already built packages

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command='git add "./*PKGBUILD"')
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command='git commit --allow-empty -m "Build {} at {} for {}"'.format(
                    self.build.number, time.strftime("%c"), self.arch))
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command='git push')
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def getCurrentSummary(self):
        return {u'step': u'pushing'}

    def getResultSummary(self):
        return {u'step': u'pushed'}


class ScanRepository(buildstep.ShellMixin, steps.BuildStep):
    name = "scan_repo"
    description = "generating package steps"
    pkgs = None

    def __init__(self, arch, **kwargs):
        self.arch = arch

        kwargs = self.setupShellMixin(kwargs, prohibitArgs=['command'])
        steps.BuildStep.__init__(self, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog('logs')

        # Get a list of already built packages

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command=['ls', 'built_packages'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        prebuilt_packages = cmd.stdout.split()
        self.setProperty("existing_packages", prebuilt_packages, "Repository Scan")

        # Generate a list of packages to build

        cmd = yield self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
                command=['find', '-name', 'PKGBUILD', '-printf', '%h\\n'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        self.pkgs = [os.path.basename(path) for path in cmd.stdout.split()]

        # Get dependencies and provides for all the packages

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

        # Create package build steps for the sorted package list

        steps = []

        for name in sorted_package_names:
            info = pkg_info[job_names.index(name)]
            steps.append(ArchPackage(name,self.arch,
                    depends=info['depends'],provides=info['provides']))

        yield log.addStdout(u'Sorted packages: {}\n'.format(sorted_package_names))

        self.build.addStepsAfterCurrentStep(steps)
        self.setProperty("packages", sorted_package_names, "Repository Scan")

        # Warn if no packages found

        if len(self.pkgs) == 0:
            defer.returnValue(WARNINGS)  
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
        self.addStep(PushRepositoryChanges(arch))


class GitPoller(changes.GitPoller):
    def __init__(self, repourl, branches=None, branch=None,
                 workdir=None, pollInterval=10 * 60,
                 gitbin='git', usetimestamps=True,
                 category=None, project=None,
                 pollinterval=-2, fetch_refspec=None,
                 encoding='utf-8', name=None, pollAtLaunch=False,
                 ignored_authors=[]):
        changes.GitPoller.__init__(self,repourl,branches,branch,
                workdir, pollInterval, gitbin, usetimestamps,
                category, project, pollinterval, fetch_refspec,
                encoding, name, pollAtLaunch)
        self.ignored_authors = ignored_authors

    @defer.inlineCallbacks
    def _process_changes(self, newRev, branch):
        """
        Read changes since last change.
        - Read list of commit hashes.
        - Extract details from each commit.
        - Add changes to database.
        """

        # initial run, don't parse all history
        if not self.lastRev:
            return
        if newRev in self.lastRev.values():
            # TODO: no new changes on this branch
            # should we just use the lastRev again, but with a different branch?
            pass

        # get the change list
        revListArgs = ([r'--format=%H', r'%s' % newRev] +
                       [r'^%s' % rev for rev in self.lastRev.values()] +
                       [r'--'])
        self.changeCount = 0
        results = yield self._dovccmd('log', revListArgs, path=self.workdir)

        # process oldest change first
        revList = results.split()
        revList.reverse()
        self.changeCount = len(revList)
        self.lastRev[branch] = newRev

        if self.changeCount:
            log.msg('gitpoller: processing %d changes: %s from "%s" branch "%s"'
                    % (self.changeCount, revList, self.repourl, branch))

        for rev in revList:
            dl = defer.DeferredList([
                self._get_commit_timestamp(rev),
                self._get_commit_author(rev),
                self._get_commit_files(rev),
                self._get_commit_comments(rev),
            ], consumeErrors=True)

            results = yield dl

            # check for failures
            failures = [r[1] for r in results if not r[0]]
            if failures:
                # just fail on the first error; they're probably all related!
                raise failures[0]

            timestamp, author, files, comments = [r[1] for r in results]

            if author in self.ignored_authors:
                continue

            yield self.master.data.updates.addChange(
                author=author, revision=ascii2unicode(rev), files=files,
                comments=comments, when_timestamp=timestamp,
                branch=ascii2unicode(self._removeHeads(branch)),
                project=self.project, repository=ascii2unicode(self.repourl),
                category=self.category, src=u'git')

