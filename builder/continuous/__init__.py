from builder.core import Container, Object, workdir, chroots_dir, celery, logger
from builder.utils import load_yaml, run
from builder.sources import GitSource
from .tasks import build_continuous
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

    def process_pull_request(self, pull_request):
        print('Processing pull request')
        repo_name = pull_request['base']['repo']['full_name']
        repo = next((repo for repo in self.repos if repo.name == repo_name), None)
        if not repo:
            raise Exception("Repository not registered: " + repo_name)
        patch_url = pull_request['patch_url']
        branch = pull_request['base']['ref']
        repo.build(branch=branch, patch_url=patch_url)

    @property
    def objects(self):
        return self.repos


class Repository(Object):
    def __init__(self, name, workdir):
        super().__init__()
        self.name = name
        self.workdir = workdir
        self.source = GitSource(workdir, name)

    def build(self, branch=None, patch_url=None):
        print('Starting CI build of ' + self.name)
        return build_continuous.delay(self, branch=branch, patch_url=patch_url)

    @property
    def config(self):
        return load_yaml(os.path.join(self.workdir, '.builder.yml'))
