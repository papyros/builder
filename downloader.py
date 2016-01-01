from git.util import RemoteProgress
from git import Repo
import os.path
import progressbar

def git_clone(url, path, bare=False):
    url, other = url.split('#', 1)

    reftype, branch = other.split('=')

    progress = ProgressBar()
    if os.path.exists(path):
        repo = Repo(path)
        repo.pull(progress=progress)
        # TODO: Does this work with tags?
        repo.head = repo.heads[branch]
        # reset the index and working tree to match the pointed-to commit
        repo.head.reset(index=True, working_tree=True)
        return repo
    else:
        kwargs = {}
        if branch is not None:
            kwargs['branch'] = branch
        return Repo.clone_from(url, path, progress=progress, bare=True, **kwargs)


class ProgressBar(RemoteProgress):
    bar = None

    def __init__(self):
        super().__init__()

    def update(self, op_code, cur_count, max_count=None, message=''):
        if self.bar is None or self.bar.op_code != op_code:
            self.bar = progressbar.ProgressBar(max_value=(max_count or 100.0))
            self.bar.op_code = op_code
        if cur_count > 0 and cur_count < self.bar.max_value:
            self.bar.update(cur_count)
