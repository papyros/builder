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
from pacstrapactions import *
from ostreeactions import *

class ScanChannels(ShellMixin, BuildStep):
    """
    """

    name = "scan-channels"
    description = "Build all available channels"

    def __init__(self, arch, ostree_lock, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.arch = arch
        self.ostree_lock = ostree_lock

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        # Find out which packages are meant for this channel
        config = utils.loadYaml("tmp/channels.yml")

        self.packages = []
        channels = config.get('channels', {})

        yield log.addStdout(u"Channels:\n\t{}\n".format("\n\t".join(channels)))

        steps = []

        for channel in channels:
            steps.append(PacstrapCreate(self.arch, channel))
            steps.append(CreateInitImage(self.arch, channel))
            steps.append(FilesystemSetup(self.arch, channel))
            steps.append(PostInstall(self.arch, channel))
            # TODO: Support stable channels as well
            steps.append(CommitTree(self.arch, 'testing', channel, 
                    '/srv/http/ostree', locks=[self.ostree_lock.access('exclusive')])) 

        self.build.addStepsAfterCurrentStep(steps)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)
