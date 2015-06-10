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

import os, re

from buildbot.plugins import steps
from buildbot.process.buildstep import ShellMixin
from buildbot.process.buildstep import BuildStep
from buildbot.status.results import *

from twisted.internet import defer

from chrootactions import CcmAction

class BinaryPackageBuild(CcmAction):
    """
    Build a package in a clean chroot.
    See https://wiki.archlinux.org/index.php/DeveloperWiki:Building_in_a_Clean_Chroot
    """

    description = "Build a package in a clean chroot"
    artifacts = []
    ccm = True

    def __init__(self, name, arch, depends, provides, **kwargs):
        CcmAction.__init__(self, arch=arch, action="s", **kwargs)
        self.name = "pkg {} {}".format(name, arch)
        self.pkgname = name
        self.arch = arch
        self.depends = depends
        self.provides = provides

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        yield log.addStdout(u"Depends: {}\n".format(self.depends))
        yield log.addStdout(u"Provides: {}\n".format(self.provides))

        # Package directory
        workdir = os.path.join(self.workdir, 'packages', self.pkgname)

        # Find the artifacts
        cmd = yield self._makeCommand(["/usr/bin/find", ".", "-type", "f", 
                "-name", "*.pkg.tar.xz", "-printf", "%f "], workdir=workdir)
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        existing_packages = cmd.stdout.strip().split(" ")
            
        # Check whether we already built the latest version
        cmd = yield self._makeCommand("../../../helpers/pkgversion -l PKGBUILD", workdir=workdir)
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        self.latest_version = cmd.stdout.strip()
        if self.latest_version == "?":
            yield log.addStderr(u"Unable to determine the {} version".format(self.pkgname))
            defer.returnValue(FAILURE)
        yield log.addStdout(u"Latest Version: {}\n".format(self.latest_version))

        # Determine the package file name
        self.pkgfilename = "{}-{}-{}.pkg.tar.xz".format(self.pkgname, self.latest_version, self.arch)
        yield log.addStdout(u"Expected package file name: {}\n".format(self.pkgfilename))

        # Already built packages
        r = re.compile(r'{}.*\-.*\-{}\.pkg\.tar\.xz'.format(self.pkgname, self.arch))
        already_built_packages = filter(r.match, existing_packages)
        yield log.addStdout(u"Existing packages: {}\n".format(already_built_packages))

        # Did we have this package already built?
        r = re.compile(r'{}.*\-{}\-{}\.pkg\.tar\.xz'.format(self.pkgname, re.escape(self.latest_version), self.arch))
        already_built_same_version = filter(r.match, existing_packages)

        already_built = len(already_built_same_version) > 0

        if already_built:
            self.current = True
            yield log.addStdout(u"Package already built, skipping!\n")
        else:
            if self.ccm is True:
                # Build the package with ccm
                cmd = yield self._makeCcmCommand("s", workdir=workdir)
                yield self.runCommand(cmd)
                if cmd.didFail():
                    defer.returnValue(FAILURE)
            else:
                # Retrieve the chroot path
                chrootdir = self.getProperty("chroot_basedir")
                yield log.addStdout(u"Building from chroot: {}\n".format(chrootdir))

                # Actually build the package
                repodir = os.path.join(self.workdir, "..", "..", "repository")
                cmd = yield self._makeCommand("sudo makechrootpkg -cu -D {}:/var/tmp/repository -r {}".format(repodir, chrootdir), workdir=workdir)
                yield self.runCommand(cmd)
                if cmd.didFail():
                    defer.returnValue(FAILURE)

        # Find the artifacts
        cmd = yield self._makeCommand(["/usr/bin/find", ".", "-type", "f", 
                "-name", "*.pkg.tar.xz", "-printf", "%f "], workdir=workdir)
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        self.all_artifacts = cmd.stdout.strip().split(" ")
        yield log.addStdout(u"All packages: {}\n".format(self.all_artifacts))
        
        # Add artifact to the list
        r = re.compile(r'.*\-{}\-{}\.pkg\.tar\.xz'.format(re.escape(self.latest_version), self.arch))
        self.artifacts = filter(r.match, self.all_artifacts)
        yield log.addStdout(u"Built packages: {}\n".format(self.artifacts))

        # Bail out if we don't have artifacts
        if len(self.artifacts) == 0:
            yield log.addStderr(u"No artifacts have been built!\n")
            defer.returnValue(FAILURE)

        # Copy the artifacts
        for artifact in self.artifacts:
            cmd = yield self._makeCommand("/usr/bin/cp -f packages/{}/{} ../repository".format(self.pkgname, artifact))
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

            cmd = yield self._makeCommand("repo-add ../repository/papyros.db.tar.gz " +
                                          "../repository/{}".format(artifact))
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        import types
        if type(args) == types.StringType:
            command = args.split(" ")
        else:
            command = args
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=command, **kwargs)

    @defer.inlineCallbacks
    def _runCommand(self, command, **kwargs):
        cmd = yield self._makeCommand(command, **kwargs)
        yield self.runCommand(cmd)
        defer.returnValue(not cmd.didFail())
