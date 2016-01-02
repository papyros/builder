from .helpers import pkgversion, pkgdepends, pkgprovides, pkgsources, gitrev, changelog
from .helpers import find_files, repoadd, ccm, ccm_repoadd
import tarfile
import os.path
import re
import downloader

class Package:
    required = False

    def __init__(self, repo, name):
        self.repo = repo
        self.name = name
        self.workdir = os.path.join(self.repo.workdir, 'packages', name)

    def load(self):
        self.dependencies = pkgdepends(self.workdir)
        self.provides = pkgprovides(self.workdir)
        self.sources = {}
        for source in pkgsources(self.workdir):
            split = source.split('::', 1)
            if len(split) == 2:
                self.sources[split[0]] = split[1]
            else:
                self.sources[split[0]] = split[0]

    def download(self):
        print(' -> ' + self.name)
        for name, source in self.sources.items():
            if source.startswith('git'):
                if source.startswith('git+'):
                    source = source[4:]
                downloader.git_clone(source, os.path.join(self.workdir, name), bare=True)
            elif source.startswith('http') or source.startswith('https'):
                print('HTTP!')
            elif '://' in source:
                raise Exception('Unkown protocol for source: ' + source)

    def refresh(self):
        print(' -> ' + self.name)
        built_packages = self.built_packages(latest_only=False)
        built_versions = [self.pkg_regex.match(filename).group(1)
                          for filename in built_packages]
        self.built_version = max(built_versions) if len(built_versions) > 0 else None
        self.latest_version = pkgversion(self.name, workdir=self.workdir, latest=True)
        self.gitrev = gitrev(workdir=self.workdir)
        self.prev_ver = self.repo.buildinfo.get('packages').get(self.name, None)
        self.needs_build = self.latest_version != self.built_version

    def build(self):
        print(' -> {} ({} -> {})'.format(self.name, self.built_version, self.latest_version))
        if self.needs_build:
            ccm('s', arch=self.repo.arch, workdir=self.workdir)

        self.artifacts = self.built_packages(latest_only=True)

        if len(self.artifacts) is 0:
            raise Exception("No packages were built!")

        # Copy the artifacts
        for artifact in self.artifacts:
            repoadd(self.repo.database, os.path.join(self.workdir, artifact))
            ccm_repoadd(os.path.join(self.workdir, artifact), arch=self.repo.arch)

    def built_packages(self, latest_only=False):
        regex = self.latest_pkg_regex if latest_only else self.pkg_regex
        packages = find_files('*.pkg.tar.xz'.format(self.name, self.repo.arch),
                              workdir=self.workdir)
        return list(filter(regex.match, packages))

    @property
    def changes(self):

        if not self.prev_ver:
            return ' * New package added to the channel!'

        changes = changelog(self.prev_ver, workdir=self.workdir)

        if len(changes) == 0:
            changes = ' * No changes'

        return changes

    @property
    def pkg_regex(self):
        return re.compile(r'{}.*?\-(r?\d.*)\-({}|any)\.pkg\.tar\.xz'.format(self.name, self.repo.arch))

    @property
    def latest_pkg_regex(self):
        return re.compile(r'.*\-{}\-({}|any)\.pkg\.tar\.xz'.format(self.latest_version,
                self.repo.arch))
