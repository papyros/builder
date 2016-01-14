import glob
import os
import os.path
from shutil import copy

import utils


def helper(name, args, workdir, sudo=False):
    return utils.helper('pkgbuild', name, args, workdir=workdir, sudo=sudo)


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
    return helper('pkgdepends', [os.path.join(workdir, 'PKGBUILD')], workdir=workdir).split()


def pkgprovides(workdir):
    return helper('pkgprovides', [os.path.join(workdir, 'PKGBUILD')], workdir=workdir).split()


def pkgsources(workdir):
    return helper('pkgsources', [os.path.join(workdir, 'PKGBUILD')], workdir=workdir).split()


def gitrev(workdir):
    return helper('gitrev', ['-l', os.path.join(workdir, 'PKGBUILD')], workdir=workdir)


def changelog(prev_ver, workdir):
    return helper('changelog', ['-l', os.path.join(workdir, 'PKGBUILD'), prev_ver],
                  workdir=workdir)


def find_files(pattern, workdir):
    os.chdir(workdir)
    return glob.glob(pattern)


def repoadd(database, package, sudo=False):
    db_dir = os.path.dirname(database)
    pkg_dir = os.path.dirname(package)

    if os.path.exists(os.path.join(db_dir, os.path.basename(package))):
        return

    if sudo:
        utils.run(['mkdir', '-p', db_dir], workdir=db_dir, sudo=True)
        if pkg_dir != db_dir:
            utils.run(['cp', package, db_dir], workdir=db_dir, sudo=True)
    else:
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        if pkg_dir != db_dir:
            package = copy(package, db_dir)
    utils.run(['repo-add', database, package], sudo=sudo)


def ccm(action, arch, workdir):
    bits = "32" if arch == "i686" else "64"
    return utils.run(['ccm' + bits, action], workdir=workdir, capture_stdout=False, sudo=True)


def ccm_repoadd(package, arch):
    bits = "32" if arch == "i686" else "64"
    # TODO: Replace the db path with a path loaded from the ccm config
    repoadd('/scratch/chroot{}/root/repo/chroot_local.db.tar.gz'.format(bits), package, sudo=True)
