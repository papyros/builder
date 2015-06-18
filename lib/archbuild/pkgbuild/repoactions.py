#
# Archbuild - Buildbot configuration for Papyros
#
# Copyright (C) 2015 Michael Spencer <sonrisesoftware@gmail.com>
# Copyright (C) 2015 Pier Luigi Fiorini <pierluigi.fiorini@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os.path
import yaml

import networkx as nx

from buildbot.process.buildstep import ShellMixin, BuildStep
from buildbot.status.results import *

from twisted.internet import defer

from archbuild.common import utils

from pkgactions import BinaryPackageBuild

class RepositoryScan(ShellMixin, BuildStep):
    """
    Scans a repository to find packages and build them.
    """

    name = "repo-scan"
    description = "Scan a repository and build packages not yet built"
    packages = []

    def __init__(self, arch, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        # Find out which packages are meant for this channel
        config = utils.loadYaml("tmp/channels.yml")

        self.packages = []
        channels = config.get('channels', {})

        for channel in channels:
            packages = config.get('channels', {}).get(channel, {}).get('packages', [])
            if len(self.packages) == 0:
                self.packages = packages
            else:
                self.packages = utils.union(self.packages, packages)

        # Make a list of packages that have been built already
        cmd = yield self._makeCommand(["/usr/bin/find", "../repository", 
                "-type", "f", "-name", "*.pkg.tar.xz", "-printf", "%f "])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        existing_packages = cmd.stdout.split()
        self.setProperty("existing_packages", existing_packages, "RepositoryScan")

        cmd = yield self._makeCommand(['find', 'packages', '-name', 'PKGBUILD', '-printf', '%h '])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        self.available_packages = [os.path.basename(path) for path in cmd.stdout.split()]

        if len(self.available_packages) == 0:
            yield log.addStdout("No available packages to build.\n")
            defer.returnValue(SKIPPED)
            
        # Get the dependencies and provides for the packages
        pkg_info = []
        for pkgname in self.available_packages:
            # Dependencies
            cmd = yield self._makeCommand("../helpers/pkgdepends packages/{}/PKGBUILD".format(pkgname))
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)
            depends = cmd.stdout.strip().split(" ")

            # Get the package names this package provides
            cmd = yield self._makeCommand("../helpers/pkgprovides packages/{}/PKGBUILD".format(pkgname))
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)
            provides = cmd.stdout.strip().split(" ")

            # Append package information
            pkg_info.append({
                "name": pkgname,
                "depends": depends,
                "provides": provides,
                "required": False
            })

        # Update the list of dependencies removing dependencies provided by the system
        for pkg in pkg_info:
            deps = []
            for dep in pkg["depends"]:
                providers = [npkg for npkg in pkg_info if dep in npkg["provides"] or npkg["name"] == dep]
                if len(providers) > 0:
                    deps.append(providers[0]["name"])
            pkg["depends"] = deps

        names = [pkg["name"] for pkg in pkg_info]
        
        for name in self.packages:
            if name in names:
                self._markRequired(pkg_info, names, name)

        # Sort packages based on their dependencies
        graph = nx.DiGraph()
        for pkg in pkg_info:
            if len(pkg["depends"]) == 0:
                graph.add_node(pkg["name"])
            else:
                for dep in pkg["depends"]:
                    if dep != pkg["name"]:
                        graph.add_edge(dep, pkg["name"])
        sorted_names = nx.topological_sort(graph)
        
        yield log.addStdout(u"Available packages to build:\n\t{}\n".format("\n\t".join(sorted_names)))

        required_packages = [name for name in sorted_names if pkg_info[names.index(name)]['required']]

        if len(required_packages) == 0:
            yield log.addStdout("No packages will be build.\n")
            defer.returnValue(SKIPPED)
        else:
            yield log.addStdout(u"Building packages:\n\t{}\n".format("\n\t".join(required_packages)))

        # Create build steps for the sorted packages list
        steps = []
        for name in required_packages:
            info = pkg_info[names.index(name)]
            steps.append(BinaryPackageBuild(name=name, arch=self.arch,
                            depends=info["depends"], provides=info["provides"]))

        self.build.addStepsAfterCurrentStep(steps)
        self.setProperty("packages", required_packages, "RepositoryScan")

        defer.returnValue(SUCCESS)

    def getCurrentSummary(self):
        return {"step": u"scanning repository"}

    def getResultSummary(self):
        return {"step": u"{} packages".format(len(self.packages))}

    def _makeCommand(self, args, **kwargs):
        import types
        if type(args) == types.StringType:
            command = args.split(" ")
        else:
            command = args
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=command, **kwargs)

    def _markRequired(self, pkg_info, names, name):
        pkg = pkg_info[names.index(name)]

        if pkg['required']:
            return
        else:
            pkg['required'] = True
            for dep in pkg['depends']:
                self._markRequired(pkg_info, names, dep)

class Changelog(ShellMixin, BuildStep):
    """
    """

    name = "changelog"
    description = "Create a changelog for the packages"
    packages = []

    def __init__(self, arch, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        changelog = ''

        # Find out which packages are meant for this channel
        buildinfo = utils.loadYaml("tmp/buildinfo.yml")

        if buildinfo.get('packages') is None:
            buildinfo['packages'] = {}

        versions = buildinfo.get('packages')

        packages = self.getProperty('packages')

        yield log.addStdout(u"Generating changelogs for packages:\n\t{}\n".
                format("\n\t".join(packages)))

        for package in packages:
            # Package directory
            workdir = os.path.join(self.workdir, 'packages', package)

            prev_ver = versions.get(package, '')

            changes = ''

            if prev_ver != '':
                yield log.addStdout(u"Previous version for {} is {}\n".format(package, prev_ver))
            
                cmd = yield self._makeCommand(['../../../helpers/changelog', '-l', 
                        'PKGBUILD', prev_ver], workdir=workdir)
                yield self.runCommand(cmd)
                if cmd.didFail():
                    defer.returnValue(FAILURE)
                changes = cmd.stdout
            else:
                changes = ' * New package added to the channel!'

            if len(changes) > 0:
                changelog += package + '\n' + changes + '\n'
                yield log.addStdout(u"{}:\n{}\n".format(package, changes))
            else:
                yield log.addStdout(u"{}:\n * No changes\n\n".format(package))

            cmd = yield self._makeCommand("../../../helpers/gitrev -l PKGBUILD"
                    .format(package), workdir=workdir)
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)
            versions[package] = cmd.stdout.strip()

            yield log.addStdout(u"New version for {} is {}\n".format(package, versions[package]))

        changelog = changelog.strip()

        if len(changelog) == 0:
            changelog = 'No changes'

        yield log.addStdout(u'Build info is:{}'.format(yaml.dump(buildinfo, default_flow_style=False)))

        utils.saveYaml("tmp/buildinfo.yml", buildinfo)
        self.setProperty('changelog', changelog, 'Changelog')

        defer.returnValue(SUCCESS)

    def getCurrentSummary(self):
        return {"step": u"generating changelog"}

    def getResultSummary(self):
        return {"step": u"changelog built"}

    def _makeCommand(self, args, **kwargs):
        import types
        if type(args) == types.StringType:
            command = args.split(" ")
        else:
            command = args
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=command, **kwargs)

