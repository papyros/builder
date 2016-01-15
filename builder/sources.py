import os
import os.path

from git import Repo


def git_url(repo_name):
    return 'git@github.com:{}.git'.format(repo_name)


class Source:
    workdir = None

    def pull(self):
        pass


class GitSource(Source):

    def __init__(self, workdir, url):
        if '://' not in url:
            url = git_url(url)

        self.workdir = workdir
        self.url = url

        if not os.path.exists(self.workdir):
            os.makedirs(workdir)

        if self.exists:
            self.repo = Repo(workdir)
        else:
            print("WARNING: repo doesn't exist: " + workdir)

    def pull(self, branch=None):
        if self.exists:
            self.repo.remotes.origin.pull()
        else:
            self.repo = Repo.clone_from(self.url, self.workdir)
            self.repo.head.reference = self.repo.refs[branch]
            self.repo.head.reset(index=True, working_tree=True)

    # TODO: Implement progress
    def checkout(self, sha=None, branch=None, patch_url=None):
        if self.exists:
            print("Fetching repo...")
            try:
                self.repo.git.rebase('--abort')
            except:
                pass
            try:
                self.repo.git.am('--abort')
            except:
                pass
            self.repo.remotes.origin.fetch()
        else:
            self.repo = Repo.clone_from(self.url, self.workdir)

        if sha is not None:
            print('Checking out commit: ' + sha)
            self.repo.head.reference = self.repo.commit(sha)
            self.repo.head.reset(index=True, working_tree=True)
        else:
            if branch is None:
                branch = 'master'
            self.repo.head.reference = self.repo.refs[branch]
            self.repo.head.reset(index=True, working_tree=True)
            self.repo.git.reset('--hard', 'origin/{}'.format(branch))
            self.repo.git.clean('-xfd')

        if patch_url is not None:
            print('Applying patch: ' + patch_url)
            self.patch(patch_url=patch_url)

    def patch(self, patch_url):
        from builder.helpers import hub
        hub(['am', '-3', patch_url], workdir=self.workdir)

    def poll_trigger(self, action):
        pass

    @property
    def exists(self):
        return os.path.exists(os.path.join(self.workdir, '.git'))
