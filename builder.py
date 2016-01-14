#! /usr/bin/env python3

from builder import Builder
from builder.core import base_dir
import os.path
import sys


if __name__ == '__main__':
    builder = Builder(os.path.join(base_dir, 'config.yml'))

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'ci':
        builder.continuous.execute(*args)
    elif cmd == 'iso':
        builder.isos.execute(*args)
    elif cmd == 'reload':
        builder.continuous.create_webhooks()
    else:
        print('Command not found: ' + cmd)
