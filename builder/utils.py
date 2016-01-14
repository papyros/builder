import os.path
import re
import subprocess

import yaml

from builder.core import base_dir, redis_client


def run(cmd, workdir=None, capture_stdout=True, sudo=False):
    if sudo:
        cmd = ['sudo'] + cmd
    print(' '.join(cmd))
    if capture_stdout:
        completion = subprocess.run(cmd, cwd=workdir, check=True, universal_newlines=True,
                                    stdout=subprocess.PIPE)
        return completion.stdout.strip()
    else:
        return subprocess.run(cmd, cwd=workdir, check=True)


def helper(type, name, args, workdir, sudo=False):
    return run([os.path.join(base_dir, 'helpers', type, name)] + args, workdir=workdir, sudo=sudo)


def load_yaml(fileName):
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    stream = open(fileName, "r")
    return load(stream, Loader=Loader)


def save_yaml(fileName, data):
    with open(fileName, 'w') as file:
        file.write(yaml.dump(data, default_flow_style=False))


def flatten(outer_list):
    return [item for inner_list in outer_list for item in inner_list]


def append_to_file(filename, text):
    if isinstance(text, list):
        text = '\n'.join(text)
    with open(filename, 'a') as file:
        file.write(text)


def replace_in_file(filename, regex, replacement):
    regex = re.compile(regex)

    lines = []
    with open(filename) as infile:
        for line in infile:
            line = regex.sub(replacement, line)
            lines.append(line)
    with open(filename, 'w') as outfile:
        for line in lines:
            outfile.write(line)


def locked(function=None, key="", timeout=None):
    """Enforce only one celery task at a time."""

    def _dec(run_func):
        """Decorator."""

        def _caller(self, *args, **kwargs):
            """Caller."""
            ret_value = None
            have_lock = False
            lock = redis_client.lock(key, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = run_func(self, *args, **kwargs)
                else:
                    self.retry()
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        _caller.__name__ == run_func.__name__

        return _caller

    return _dec(function) if function is not None else _dec
