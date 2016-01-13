import builder.utils
import os
import os.path


def mkarchroot(workdir, packages=None):
    if not packages:
        packages = []
    parent_dir = os.path.dirname(workdir)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    utils.run(['mkarchroot', workdir] + packages, sudo=True,
            capture_stdout=False)

def arch_nspawn(workdir, cmd, bind_ro=None, bind_rw=None):
    if not bind_ro:
        bind_ro = []
    if not bind_rw:
        bind_rw = []
    bind_ro = ['--bind-ro=' + bind for bind in bind_ro]
    bind_rw = ['--bind=' + bind for bind in bind_rw]
    utils.run(['arch-nspawn', workdir] + bind_ro + bind_rw + cmd, capture_stdout=False)
