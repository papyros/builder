import os
import os.path

from builder.core import chroots_dir
from builder.helpers import arch_nspawn, mkarchroot
from builder.utils import run


class Chroot:

    def __init__(self, name):
        self.base_dir = os.path.join(chroots_dir, 'base')
        self.workdir = os.path.join(chroots_dir, 'active_job')
        self.bind_ro = []
        self.bind_rw = []

    def create(self):
        self.create_base()
        rsync(self.base_dir, self.workdir, sudo=True)

    def create_base(self):
        if not os.path.exists(self.base_dir):
            mkarchroot(self.base_dir, ['base-devel', 'vim'])
        else:
            arch_nspawn(self.base_dir, ['pacman', '--noconfirm', '-Syu'])

    def install(self, pkgs):
        if not isinstance(pkgs, list):
            pkgs = [pkgs]

        if len(pkgs) > 0:
            arch_nspawn(self.workdir, ['pacman', '--noconfirm', '-S'] + pkgs)

    def run(self, cmd, workdir=None):
        if workdir:
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            cmd = 'cd {} && {}'.format(workdir, cmd)
            cmd = (['bash', '-cil', cmd])
        arch_nspawn(self.workdir, cmd, bind_ro=self.bind_ro,
                    bind_rw=self.bind_rw)
