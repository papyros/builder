import os
import os.path

from git import Repo

from builder.helpers import hub


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

    # TODO: Implement progress
    def pull(self, branch=None):
        if self.exists:
            try:
                self.repo.git.rebase('--abort')
            except:
                pass
            try:
                self.repo.git.am('--abort')
            except:
                pass
            self.repo.git.reset(
                '--hard', 'origin/{}'.format(branch or 'master'))
            self.repo.git.clean('-xfd')
            info = self.repo.remotes.origin.pull()[0]

            updated = info.flags & (
                info.FORCED_UPDATE | info.FAST_FORWARD | info.NEW_HEAD)
            return updated
        else:
            self.repo = Repo.clone_from(self.url, self.workdir)
            return True

    def patch(self, patch_url):
        hub(['am', '-3', patch_url], workdir=self.workdir)

    def poll_trigger(self, action):
        pass

    @property
    def exists(self):
        return os.path.exists(os.path.join(self.workdir, '.git'))
