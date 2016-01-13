#! /usr/bin/env python3

from continuous import ContinuousIntegration
from utils import load_yaml
from core import base_dir
import sys
import os.path


if __name__ == '__main__':
    config = load_yaml(os.path.join(base_dir, 'config.yml'))

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'ci':
        container = ContinuousIntegration(config.get('continuous', []))
        container.execute(*args)
    else:
        print('Command not found: ' + cmd)
