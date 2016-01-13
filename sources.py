from git import Repo
import os
import os.path

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
    def pull(self):
        if self.exists:
            info = self.repo.remotes.origin.pull()[0]
            
            updated = info.flags & (info.FORCED_UPDATE|info.FAST_FORWARD|info.NEW_HEAD)
            return updated
        else:
            self.repo = Repo.clone_from(self.url, self.workdir)
            return True

    def poll_trigger(self, action):
        pass

    @property
    def exists(self):
        return os.path.exists(os.path.join(self.workdir, '.git'))
