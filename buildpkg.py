#! /usr/bin/env python3

import os
import os.path
import subprocess
import sys
from collections import OrderedDict

from jinja2 import Environment, FileSystemLoader

from builder.core import base_dir
from builder.pkgbuild.helpers import pkgrel, pkgversion
from builder.utils import load_yaml, run

env = Environment(loader=FileSystemLoader(os.path.join(base_dir, 'templates')),
                  trim_blocks=True, lstrip_blocks=True)

def create_pkgbuild(workdir):
    build_filename = os.path.join(workdir, 'build.yml')
    pkgbuild_filename = os.path.join(workdir, 'PKGBUILD')

    config = load_yaml(build_filename)
    config['optdepends'] = OrderedDict(sorted(config.get('optdepends', {}).items(),
                                       key=lambda t: t[0]))

    template = env.get_template('PKGBUILD.{}.in'.format(config.get('type', 'base')))

    version = '0'
    rel = 1

    if os.path.exists(pkgbuild_filename):
        try:
            version = pkgversion(config['name'], workdir=workdir, latest=False,
                                     include_rel=False)
        except Exception as ex:
            version = pkgversion(config['name'], workdir=workdir, latest=True,
                                 include_rel=False)
        rel = int(pkgrel(config['name'], workdir=workdir))

        with open(pkgbuild_filename) as f:
            old_pkgbuild = f.read()
        pkgbuild = template.render(**config, version=version, pkgrel=rel)

        if pkgbuild != old_pkgbuild:
            # from difflib import Differ
            # from pprint import pprint
            # d = Differ()
            # result = list(d.compare(old_pkgbuild.split('\n'), pkgbuild.split('\n')))
            # pprint(result)
            rel += 1

    pkgbuild = template.render(version=version, pkgrel=rel, **config)

    with open(pkgbuild_filename, 'w') as f:
        f.write(pkgbuild)
    if version == '0':
        pkgversion(config['name'], workdir=workdir, latest=True, include_rel=False)


if __name__ == '__main__':
    create_pkgbuild(workdir=os.getcwd())
