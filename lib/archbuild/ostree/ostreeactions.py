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

import time

from buildbot.process.buildstep import ShellMixin, BuildStep
from buildbot.status.results import *

from twisted.internet import defer

from archbuild.common import utils

class CreateInitImage(ShellMixin, BuildStep):
    """
    """

    name = "ostreeinit"
    description = "Create the OSTree init files"

    def __init__(self, arch, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch

    @defer.inlineCallbacks
    def run(self):
        # Create the pacstrap instance
        cmd = yield self._makeCommand(['sudo', '../helpers/ostreeinit', 
            '32' if self.arch == 'i686' else '64', '../pacstrap-' + self.arch])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)

class FilesystemSetup(ShellMixin, BuildStep):
    """
    """

    name = "setup"
    description = "Set up directories"

    def __init__(self, arch, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch

    @defer.inlineCallbacks
    def run(self):
        # Create the pacstrap instance
        cmd = yield self._makeCommand(['sudo', '../helpers/ostreesetup', '../pacstrap-' + self.arch])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)


class CommitTree(ShellMixin, BuildStep):
    """
    """

    name = "commit"
    description = "Commit tree to OSTree"

    def __init__(self, arch, channel, ostree_dir, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch
        self.channel = channel
        self.ostree_dir = ostree_dir

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self._makeCommand("test -d " + self.ostree_dir)
        yield self.runCommand(cmd)
        if cmd.didFail():
            # Create the pacstrap instance
            cmd = yield self._makeCommand(['ostree', '--repo=' + self.ostree_dir, 'init',
                    '--mode', 'archive-z2'])
            yield self.runCommand(cmd)
            if cmd.didFail():
                defer.returnValue(FAILURE)

        cmd = yield self._makeCommand(['sudo', 'ostree', '--repo=' + self.ostree_dir, 'commit',
                    '--tree=dir=../pacstrap-' + self.arch, '--branch=' + self.channel,
                    '--subject', 'Build {} at {}'.format(self.build.number, time.strftime("%c"))])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        cmd = yield self._makeCommand(['sudo', '../helpers/post-commit', self.ostree_dir])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)
