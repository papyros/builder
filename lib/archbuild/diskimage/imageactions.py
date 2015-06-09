#
# Archbuild - Buildbot configuration for Papyros
#
# Copyright (C) 2015 Michael Spencer <sonrisesoftware@gmail.com>
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

class CreateDiskImage(ShellMixin, BuildStep):
    """
    """

    name = "diskimage"
    description = "Create a disk image from the OSTree repository"

    def __init__(self, arch, branch, channel, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch
        self.branch = branch
        self.channel = channel

    @defer.inlineCallbacks
    def run(self):
        # Create the image directory if needed
        cmd = yield self._makeCommand(['mkdir', '-p', 
            '/srv/http/images/{branch}/{arch}/{date}'
                    .format(branch=self.branch,arch=self.arch,date=time.strftime("%Y%m%d"))])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        # Build the disk image
        cmd = yield self._makeCommand(['sudo', '../helpers/ostree-pack', 
            'papyros', 'http://dash.papyros.io/ostree', 
            '/srv/http/ostree',
            'papyros/{branch}/{arch}/{channel}'
                    .format(branch=self.branch,arch=self.arch,channel=self.channel),
            '/srv/http/images/{branch}/{arch}/{date}/papyros-{channel}.img'
                    .format(branch=self.branch,arch=self.arch,channel=self.channel,
                            date=time.strftime("%Y%m%d")), 
            '10GB'], timeout=2400) # 40 minutes
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)
        
        # Make sure the permissions are right
        cmd = yield self._makeCommand(['chmod', '-R', 'a+rX', '/srv/http/images'])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)
