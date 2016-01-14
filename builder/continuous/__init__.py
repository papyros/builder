import os
import os.path

from builder.core import Container, Object, workdir, gh, server_url
from builder.sources import GitSource
from builder.utils import load_yaml

from .tasks import build_continuous, update_commit_status


class ContinuousIntegration(Container):

    def __init__(self, config):
        self.workdir = os.path.join(workdir, 'continuous')
        self.config = config
        self.repos = [Repository(name, os.path.join(
            self.workdir, name)) for name in config]

    def execute(self, repo_name):
        repo = next(repo for repo in self.repos if repo.name == repo_name)
        repo.build()

    def process_pull_request(self, pull_request):
        repo_name = pull_request['base']['repo']['full_name']
        repo = next((repo for repo in self.repos if repo.name == repo_name), None)
        if not repo:
            raise Exception("Repository not registered: " + repo_name)
        repo.build_pull_request(pull_request=pull_request)

    def process_push(self, info):
        repo_name = info['repository']['full_name']
        repo = next((repo for repo in self.repos if repo.name == repo_name), None)
        if not repo:
            raise Exception("Repository not registered: " + repo_name)
        repo.build_specific_commit(info['after'])

    @property
    def objects(self):
        return self.repos

    def create_webhooks(self):
        for repo in self.repos:
            try:
                gh_repo = gh.repository(*repo.name.split('/'))
                name = 'web'
                config = {
                    'url': server_url + '/github/event_handler',
                    'content_type': 'json'
                }

                gh_repo.create_hook(name, config, events=['push', 'pull_request'])
            except Exception as ex:
                print('Failed to create webhook for: ' + repo.name)
                print(ex.errors)


class Repository(Object):

    def __init__(self, name, workdir):
        super().__init__()
        self.name = name
        self.workdir = workdir
        self.source = GitSource(workdir, name)

    def build(self, branch=None, patch_url=None):
        print('Starting CI build of ' + self.name)
        return build_continuous.delay(self, branch=branch, patch_url=patch_url)

    def build_specific_commit(self, sha):
        context = 'continuous-integration/builder/push'

        print('Starting CI build of {} ({})'.format(self.name, sha))
        success_callback = update_commit_status.si(self.name, sha, 'success',
                                                   'Build succeeded!', context)
        error_callback = update_commit_status.si(self.name, sha, 'failure',
                                                 'Build failed!', context)
        build_task = build_continuous.subtask(kwargs={'repo': self, 'sha': sha},
                                              immutable=True, link=success_callback,
                                              link_error=error_callback)
        start_task = update_commit_status.subtask((self.name, sha, 'pending',
                                                   'Running CI build', context), link=build_task)
        return start_task.delay()

    def build_pull_request(self, pull_request):
        context = 'continuous-integration/builder/pr'

        patch_url = pull_request['patch_url']
        branch = pull_request['base']['ref']

        source_repo = pull_request['head']['repo']['full_name']
        source_sha = pull_request['head']['sha']

        print('Starting CI build of pull request for ' + self.name)
        success_callback = update_commit_status.si(source_repo, source_sha, 'success',
                                                   'Build succeeded!', context)
        error_callback = update_commit_status.si(source_repo, source_sha, 'failure',
                                                 'Build failed!', context)
        build_task = build_continuous.subtask(kwargs={'repo': self, 'branch': branch,
                                                      'patch_url': patch_url},
                                              immutable=True, link=success_callback,
                                              link_error=error_callback)
        start_task = update_commit_status.subtask((source_repo, source_sha, 'pending',
                                                   'Running CI build', context), link=build_task)
        return start_task.delay()

    @property
    def config(self):
        filename = os.path.join(self.workdir, '.builder.yml')
        if os.path.exists(filename):
            return load_yaml(filename)
