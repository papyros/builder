from core import Container, Object, workdir, chroots_dir, celery, logger
from utils import load_yaml, run
from sources import GitSource
from .helpers import mkarchroot, arch_nspawn
import os, os.path
import shutil


class ContinuousIntegration(Container):
    def __init__(self, config):
        self.workdir = os.path.join(workdir, 'continuous')
        self.config = config
        self.repos = [Repository(name, os.path.join(self.workdir, name)) for name in config]

    def execute(self, repo_name):
        repo = next(repo for repo in self.repos if repo.name == repo_name)
        repo.build()

    @property
    def objects(self):
        return self.repos


class Repository(Object):
    def __init__(self, name, workdir):
        super().__init__()
        self.name = name
        self.workdir = workdir
        self.source = GitSource(workdir, name)

    def build(self):
        print('Starting CI build of ' + self.name)
        return build_continuous.delay(self)

    @property
    def config(self):
        return load_yaml(os.path.join(self.workdir, '.builder.yml'))

class Chroot:

    def __init__(self, name):
        self.base_dir = os.path.join(chroots_dir, 'base')
        self.workdir = os.path.join(chroots_dir, 'active_job')
        self.bind_ro = []
        self.bind_rw = []

    def create(self):
        self.create_base()
        run(['rsync', '-a', '--delete', '-q', '-W', '-x',  self.base_dir + '/', self.workdir],
                capture_stdout=False, sudo=True)

    def create_base(self):
        if not os.path.exists(self.base_dir):
            mkarchroot(self.base_dir, ['base-devel'])
        arch_nspawn(self.base_dir, ['pacman', '--noconfirm', '-Syu'])

    def install(self, pkgs):
        if not isinstance(pkgs, list):
            pkgs = [pkgs]

        arch_nspawn(self.workdir, ['pacman', '--noconfirm', '-S'] + pkgs)

    def run(self, cmd, workdir=None):
        arch_nspawn(self.workdir, cmd, bind_ro=self.bind_ro, bind_rw=self.bind_rw)

@celery.task
def build_continuous(repo):
    chroot = Chroot(repo.name)
    chroot.bind_ro = [repo.workdir + ':/source']

    config = repo.config

    logger.info('Building repo: ' + repo.name)
    logger.info('Fetching sources...')
    repo.source.pull()

    logger.info('Creating chroot...')
    chroot.create()

    logger.info('Installing dependencies...')
    chroot.run(['mkdir', '/build'])
    chroot.install(config.get('dependencies', []))

    logger.info('Running build steps...')
    for cmd in config.get('build', []):
        logger.info('--> ' + cmd)
        cmd = 'cd /build &&' + cmd.format(srcdir='/source')
        chroot.run(['bash', '-c', cmd])

    logger.info('Repository passed continuous integration: ' + repo.name)
