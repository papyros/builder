#! /usr/bin/env python3

import os
import os.path
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader

from builder.core import base_dir
from builder.utils import load_yaml, run

env = Environment(loader=FileSystemLoader(os.path.join(base_dir, 'templates')),
                  trim_blocks=True, lstrip_blocks=True)

def create_pkgbuild(config, out_filename=None):
    if isinstance(config, str):
        config = load_yaml(config)

    template = env.get_template('PKGBUILD.{}.in'.format(config.get('type', 'base')))

    pkgbuild = template.render(**config)

    if out_filename is not None:
        with open('PKGBUILD', 'w') as f:
            f.write(pkgbuild)
    else:
        return pkgbuild


if __name__ == '__main__':
    create_pkgbuild('build.yml', out_filename='PKGBUILD')
    
    run([os.path.join(base_dir, 'helpers', 'pkgbuild', 'pkgversion'), '-l', 'PKGBUILD'])
    run(['ccm64', 's'], capture_stdout=False, sudo=True)
