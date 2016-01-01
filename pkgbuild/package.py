from .helpers import pkgversion, pkgdepends, pkgprovides, find_files, repoadd, ccm
import tarfile
import os.path
import re

class Package:
    required = False

    def __init__(self, repo, name):
        self.repo = repo
        self.name = name
        self.workdir = os.path.join(self.repo.workdir, 'packages', name)

    def refresh(self):
        print(' -> ' + self.name)
        built_packages = self.built_packages(latest_only=False)
        built_versions = [self.pkg_regex.match(filename).group(1)
                          for filename in built_packages]
        self.built_version = max(built_versions) if len(built_versions) > 0 else None
        self.latest_version = pkgversion(self.name, workdir=self.workdir, latest=True)
        self.dependencies = pkgdepends(self.workdir)
        self.provides = pkgprovides(self.workdir)
        self.needs_build = self.latest_version != self.built_version

    def build(self):
        print(' -> ' + self.name)
        if self.needs_build:
            ccm('s', arch=self.repo.arch, workdir=self.workdir)

        self.artifacts = self.built_packages(latest_only=True)

        if len(self.artifacts) is 0:
            raise Exception("No packages were built!")

        # Copy the artifacts
        for artifact in self.artifacts:
            repoadd(self.repo.database, os.path.join(self.workdir, artifact))

    def built_packages(self, latest_only=False):
        regex = self.latest_pkg_regex if latest_only else self.pkg_regex
        packages = find_files('*.pkg.tar.xz'.format(self.name, self.repo.arch),
                              workdir=self.workdir)
        return list(filter(regex.match, packages))

    @property
    def pkg_regex(self):
        return re.compile(r'{}.*?\-(\d.*)\-({}|any)\.pkg\.tar\.xz'.format(self.name, self.repo.arch))

    @property
    def latest_pkg_regex(self):
        return re.compile(r'.*\-{}\-({}|any)\.pkg\.tar\.xz'.format(self.latest_version,
                self.repo.arch))
