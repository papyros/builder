from builder.helpers import mkarchroot, arch_nspawn
from builder.core import chroots_dir
import os
import os.path


class Chroot:
    def __init__(self, name):
        self.base_dir = os.path.join(chroots_dir, 'base')
        self.workdir = os.path.join(chroots_dir, 'active_job')
        self.bind_ro = []
        self.bind_rw = []

    def create(self):
        self.create_base()
        run(['rsync', '-a', '--delete', '-q', '-W', '-x',  self.base_dir + '/', self.workdir],
                capture_stdout=False, sudo=True)

    def create_base(self):
        if not os.path.exists(self.base_dir):
            mkarchroot(self.base_dir, ['base-devel'])
        arch_nspawn(self.base_dir, ['pacman', '--noconfirm', '-Syu'])

    def install(self, pkgs):
        if not isinstance(pkgs, list):
            pkgs = [pkgs]

        arch_nspawn(self.workdir, ['pacman', '--noconfirm', '-S'] + pkgs)

    def run(self, cmd, workdir=None):
        arch_nspawn(self.workdir, cmd, bind_ro=self.bind_ro, bind_rw=self.bind_rw)
