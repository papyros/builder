from .repo import Repository
from .package import Package
from ..core import Container, Object, workdir
from .tasks import build_repository
from ..utils import load_yaml

import os.path

class RepositoryContainer(Container):
    def __init__(self, config):
        self.workdir = os.path.join(workdir, 'pkgbuild')
        self.config = config
        self.objects = [RepositoryInfo(repo, arch, self.workdir)
                        for repo in config for arch in ['i686', 'x86_64']]

    def execute(self, name):
        repo = self.get(name)
        repo.build()


class RepositoryInfo(Object):
    def __init__(self, config, arch, parent_dir):
        self.name = config['name'] + '/' + arch
        self.arch = arch
        self.workdir = os.path.join(parent_dir, config['name'], arch)
        self.set_source(self.workdir, config['git'])

    def build(self):
        print('Starting build of Arch repo: ' + self.name)
        return build_repository.delay(self, self.branch)

    @property
    def config(self):
        filename = os.path.join(self.workdir, 'channels.yml')

        if os.path.exists(filename):
            return Repository(self.name, self.arch, load_yaml(filename), self.workdir)
