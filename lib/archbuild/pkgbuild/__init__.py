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

from buildbot.process.factory import BuildFactory
from buildbot.steps.shell import ShellCommand
from buildbot.steps.source.git import Git
from buildbot.plugins import steps

from chrootactions import *
from repoactions import *
from sourceactions import *

class RepositoryFactory(BuildFactory):
    """
    Factory to build a repository of packages for a certain architecture.
    """

    def __init__(self, sources, arch):
        BuildFactory.__init__(self, sources)

        # Download the helpers
        for helper in ("pkgdepends", "pkgprovides", "pkgversion", "ccm-setup"):
            self.addStep(steps.FileDownload(name="helper " + helper,
                                            mastersrc="helpers/pkgbuild/" + helper,
                                            slavedest="../helpers/" + helper,
                                            mode=0755))
        # Create a directory to hold the packages that have been built
        self.addStep(steps.MakeDirectory(name="mkdir-repository", dir="repository"))
        # Create or update the chroot
        self.addStep(PrepareCcm(arch=arch))
        # Copy the channel configuration from slave to master
        self.addStep(steps.FileUpload("channel.yml", "tmp/channel.yml", name="config-upload"))
        # Scan repository and find packages to build
        self.addStep(RepositoryScan(arch=arch))
        # Push back changes to version control (only push for x86_64 so we don't have duplicates)
        if arch == "x86_64":
            self.addStep(PushSourceChanges())
