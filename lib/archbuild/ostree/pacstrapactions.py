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

class PacstrapCreate(ShellMixin, BuildStep):
    """
    """

    name = "pacstrap"
    description = "Create a basic Arch installation"

    def __init__(self, arch, channel, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch
        self.channel = channel

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        # Find out which packages are meant for this channel
        config = utils.loadYaml("tmp/channels.yml")
        self.packages = config.get('channels', {}).get(self.channel, {}).get('packages', [])

        yield log.addStdout(u"Creating pacstrap with the following packages:\n\t{}\n"
                .format("\n\t".join(self.packages)))

        # Create the pacstrap instance
        cmd = yield self._makeCommand(['sudo', '../helpers/pacstrap-create', 
                '32' if self.arch == 'i686' else '64',
                'pacman.conf', '../pacstrap-' + self.arch + '-' + self.channel] + self.packages)
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)

class PostInstall(ShellMixin, BuildStep):
    """
    """

    name = "post-install"
    description = "Post installation setup"

    def __init__(self, arch, channel, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch
        self.channel = channel

    @defer.inlineCallbacks
    def run(self):
        # Create the pacstrap instance
        cmd = yield self._makeCommand(['sudo', '../helpers/post-install', 
                '32' if self.arch == 'i686' else '64', '.', 
                '../pacstrap-' + self.arch + '-' + self.channel])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)
