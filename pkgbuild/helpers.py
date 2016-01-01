from subprocess import call
from shutil import copy
import os
import os.path
import glob

import utils

def helper(name, args, workdir):
    return utils.helper('pkgbuild', name, args, workdir)

def pkgversion(pkgname, workdir, latest=False):
    args = []
    if latest:
        args += ['-l']
    args += ['PKGBUILD']
    latest_version = helper('pkgversion', args, workdir=workdir)
    if latest_version == "?":
        raise Exception('Unable to determine the version of {}'.format(pkgname))
    return latest_version

def pkgdepends(workdir):
    return helper('pkgdepends', [os.path.join(workdir, 'PKGBUILD')], workdir=workdir).split(' ')

def pkgprovides(workdir):
    return helper('pkgprovides', [os.path.join(workdir, 'PKGBUILD')], workdir=workdir).split(' ')

def find_files(pattern, workdir):
    os.chdir(workdir)
    return glob.glob(pattern)

def repoadd(database, package):
    db_dir = os.path.dirname(database)
    pkg_dir = os.path.dirname(package)

    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    if pkg_dir != db_dir:
        package = copy(package, db_dir)
    utils.run(['repo-add', database, package])

def ccm(action, arch, workdir):
    bits = "32" if arch == "i686" else "64"
    return utils.run(['sudo', 'ccm' + bits, action], workdir=workdir)
