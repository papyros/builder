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

from buildbot.process.factory import BuildFactory
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source.git import Git
from buildbot.plugins import steps

from channelactions import *

class DiskImageFactory(BuildFactory):
    """
    Factory to build disk images using the OSTree repository.
    """

    def __init__(self, sources, arch):
        BuildFactory.__init__(self, sources)

        # Download the helpers
        for helper in ('ostree-install', 'ostree-pack'):
            self.addStep(steps.FileDownload(name="helper " + helper,
                                            mastersrc="helpers/diskimage/" + helper,
                                            slavedest="../helpers/" + helper,
                                            mode=0755))
        
        # Copy the channel configuration from slave to master
        self.addStep(steps.FileUpload("channels.yml", "tmp/channels.yml", name="config-upload"))

        self.addStep(ScanChannels(arch))

