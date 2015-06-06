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

class PushSourceChanges(ShellMixin, BuildStep):
    """
    Push sources changes back to version control.
    When a git ArchLinux package is built the pkgver field is updated,
    make sure those changes are committed and pushed back.
    """

    name = "git-push"
    description = "Push package updates back"

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=["command"])
        BuildStep.__init__(self, haltOnFailure=True, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        log = yield self.addLog("logs")

        # Add PKGBUILD
        cmd = yield self._makeCommand("git add ./*PKGBUILD")
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        # Commit
        author = "Buildbot <buildbot@papyros.io>"
        msg = "Build {} at {}".format(self.build.number, time.strftime("%c"))
        cmd = yield self._makeCommand(["git", "commit", "--allow-empty", 
                "-m", msg, "--author=" + author])
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        # Push
        cmd = yield self._makeCommand("git push")
        yield self.runCommand(cmd)
        if cmd.didFail():
            defer.returnValue(FAILURE)

        defer.returnValue(SUCCESS)

    def _makeCommand(self, args, **kwargs):
        return self.makeRemoteShellCommand(collectStdout=True, collectStderr=True,
            command=args, **kwargs)
