import os
import os.path

from builder.core import Container, Object, workdir, gh, server_url
from builder.sources import GitSource
from builder.utils import load_yaml

from .tasks import build_iso


class ISOContainer(Container):

    def __init__(self, config):
        self.workdir = os.path.join(workdir, 'isos')
        self.config = config
        self.objects = [ArchISO(iso, self.workdir) for iso in config]

    def execute(self, name):
        iso = self.get(name)
        iso.build()


class ArchISO(Object):
    def __init__(self, config, parent_dir):
        self.name = config['name']
        self.workdir = os.path.join(parent_dir, config['name'])
        self.config_filename = config['config']
        self.set_source(self.workdir, config['git'])

    def set_source(self, workdir, url):
        branch = None
        if '#' in url:
            url, other = url.split('#', 1)

            if '=' in other:
                reftype, branch = other.split('=')

        self.source = GitSource(workdir, url)
        self.branch = branch

    def build(self):
        print('Starting build of ISO: ' + self.name)
        return build_iso.delay(self, self.branch)

    @property
    def config(self):
        filename = os.path.join(self.workdir, self.config_filename)
        if os.path.exists(filename):
            return ISOBuild(load_yaml(filename), os.path.join(self.workdir, 'build'))

class ISOBuild(object):
    custom_repos = []
    customizations = []

    def __init__(self, config, workdir):
        self.config = config
        self.workdir = workdir
        self.name = config.get('name', 'archlinux')
        self.packages = config.get('packages', [])
        self.packages_i686 = config.get('packages_i686', [])
        self.packages_x86_64 = config.get('packages_x86_64', [])

        for repo, url in config.get('repos', {}).items():
            self.add_repo(repo, url)
        for customization in config.get('customizations', []):
            self.add_customization(customization)
        if 'display_manager' in config:
            self.set_display_manager(config['display_manager'])
        self.version = config.get('version')
        self.label = config.get('label')

    def add_repo(self, name, url):
        self.custom_repos.append(('[{}]\n' + 'SigLevel = Optional TrustAll\n' +
                                  'Server = {}').format(name, url))

    def add_customization(self, cmd):
        self.customizations.append(cmd)

    def set_display_manager(self, display_manager):
        self.graphical_target = True
        self.add_customization('systemctl enable {}.service'.format(display_manager))

    def path(self, filename):
        return os.path.join(self.workdir, filename)
