import re
import yaml
import os.path
from core import base_dir

import subprocess


def run(cmd, workdir=None, capture_stdout=True):
    if capture_stdout:
        completion = subprocess.run(cmd, cwd=workdir, check=True, universal_newlines=True,
                                    stdout=subprocess.PIPE)
        return completion.stdout.strip()
    else:
        return subprocess.run(cmd, cwd=workdir, check=True)

def helper(type, name, args, workdir):
    return run([os.path.join(base_dir, 'helpers', type, name)] + args, workdir=workdir)


def load_yaml(fileName):
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    stream = open(fileName, "r")
    return load(stream, Loader=Loader)


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
