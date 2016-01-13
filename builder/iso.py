#! /usr/bin/env python3
import os.path, os
import sys
import shutil
import subprocess
from builder.utils import append_to_file, replace_in_file, load_yaml

class ArchISO(object):
    packages_i686 = []
    packages_x86_64 = []
    custom_repos = []
    customizations = []
    graphical_target = False
    version = None
    label = None

    def __init__(self, name, build_dir, packages):
        self.name = name
        self.build_dir = build_dir
        self.packages = packages

    def add_repo(self, name, url):
        self.custom_repos.append(('[{}]\n' +
                'SigLevel = Optional TrustAll\n' +
                'Server = {}').format(name, url))

    def add_customization(self, cmd):
        self.customizations.append(cmd)

    def set_display_manager(self, display_manager):
        self.graphical_target = True
        self.add_customization('systemctl enable {}.service'.format(display_manager))

    def path(self, filename):
        return os.path.join(self.build_dir, filename)

    def from_dict(dict, build_dir):
        iso = ArchISO(dict.get('name', 'archlinux'), build_dir, dict.get('packages', []))
        for repo, url in dict.get('repos', {}).items():
            iso.add_repo(repo, url)
        for customization in dict.get('customizations', []):
            iso.add_customization(customization)
        if 'display_manager' in dict:
            iso.set_display_manager(dict['display_manager'])
        iso.version = dict.get('version')
        iso.version = dict.get('label')
        return iso

    def build(self):
        print('>>>>> Removing the existing build directory...')
        shutil.rmtree(self.build_dir)

        print('>>>>> Setting up the build directory...')

        # Set up the iso build dir
        shutil.copytree('/usr/share/archiso/configs/releng', self.build_dir)

        # Add any additional repos
        replace_in_file(self.path('pacman.conf'), r'\#\[testing\]',
                '\n\n'.join(self.custom_repos) + '\n\n#[testing]')

        # Add the requested packages
        append_to_file(self.path('packages.both'), self.packages)
        append_to_file(self.path('packages.i686'), self.packages_i686)
        append_to_file(self.path('packages.x86_64'), self.packages_x86_64)

        # Add customizations
        append_to_file(self.path('airootfs/root/customize_airootfs.sh'), self.customizations)

        if self.graphical_target:
            replace_in_file(self.path('airootfs/root/customize_airootfs.sh'),
                    r'multi-user.target', 'graphical.target')

        print('>>>>> Building...')
        cmd = 'sudo ' + self.path('build.sh')
        args = ['v']

        if self.name:
            args += ['-N ' + self.name]
        if self.version:
            args += ['-V ' + self.version]
        if self.label:
            args += ['-L ' + self.label]

        cmd += ' ' + ' '.join(args)
        subprocess.call(cmd, shell=True, cwd=self.build_dir)


if __name__ == '__main__':
    yaml = load_yaml(sys.argv[1])
    iso = ArchISO.from_dict(yaml, sys.argv[2])
    iso.build()
