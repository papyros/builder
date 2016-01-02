import os.path
import networkx as nx

from .package import Package
from utils import load_yaml, flatten, save_yaml
from git import Actor, Repo
from datetime import datetime

class Repository:
    build_number = 1  # TODO: Load the build number from the buildinfo

    def __init__(self, name, arch, packages, workdir):
        self.name = name
        self.arch = arch
        self.workdir = workdir
        self.repo_dir = os.path.join(workdir, 'built_packages')
        self.database = os.path.join(self.repo_dir, name + '.db.tar.gz')
        self.package_names = packages

    def load(self):
        self.buildinfo = load_yaml(os.path.join(self.workdir, "buildinfo.yml"))

        all_package_names = self.find_packages()
        self.all_packages = [Package(self, name) for name in all_package_names]

        print('Loading packages...')
        for package in self.all_packages:
            package.load()

        # Update the list of dependencies removing dependencies provided by the system
        for package in self.all_packages:
            package.dependencies = [self.get_package(dependency).name
                                    for dependency in package.dependencies
                                    if self.get_package(dependency) is not None]

        # Recursively mark requested packages and all their dependencies as required
        for name in self.package_names:
            self._markRequired(name)

        # Sort packages based on their dependencies
        graph = nx.DiGraph()
        for pkg in self.all_packages:
            if len(pkg.dependencies) == 0:
                graph.add_node(pkg.name)
            else:
                for dep in pkg.dependencies:
                    if dep != pkg.name:
                        graph.add_edge(dep, pkg.name)
        sorted_names = nx.topological_sort(graph)

        self.packages = [self.get_package(name) for name in sorted_names
                         if self.get_package(name).required]

        print('Packages to build:')
        for package in self.packages:
            print(' -> ' + package.name)

        if len(self.packages) == 0:
            raise Exception('No packages to build!')

    def download(self):
        print('Downloading package sources...')
        for package in self.packages:
            package.download()

    def refresh(self):
        print('Refreshing package statuses...')
        for package in self.packages:
            package.refresh()

    def build(self):
        print('Building packages')
        for package in self.packages:
            package.build()

    def from_channel_config(config, arch, workdir):
        if isinstance(config, str):
            config = load_yaml(config)
        packages = flatten([config['channels'][name]['packages'] for name in config['channels']])
        return Repository(config['name'].lower(), arch, packages, workdir)

    def find_packages(self):
        packages = []
        pkg_dir = os.path.join(self.workdir, 'packages')
        for file in os.listdir(pkg_dir):
            if (os.path.isdir(os.path.join(pkg_dir, file)) and
                os.path.exists(os.path.join(pkg_dir, file, 'PKGBUILD'))):
                packages.append(file)
        return packages

    def publish(self):
        for package in self.packages:
            self.buildinfo.get('packages')[package.name] = package.gitrev
        save_yaml(os.path.join(self.workdir, 'buildinfo.yml'), self.buildinfo)
        repo = Repo(self.workdir)
        repo.index.add(['buildinfo.yml'] +
                       ['packages/{}/PKGBUILD'.format(pkg.name) for pkg in self.packages])
        repo.index.commit('Build {} at {:%c}\n\n{}'.format(self.build_number, datetime.now(),
                                                           self.changelog),
                          author=Actor("Builder", "builder@papyros.io"))
        repo.remotes.origin.push()

    @property
    def changelog(self):
        changes = ['{}:\n{}'.format(pkg.name, pkg.changes) for pkg in self.packages
                   if pkg.changes is not None]
        if len(changes) > 0:
            return '\n\n'.join(changes)
        else:
            return 'No changes'

    @property
    def needs_build(self):
        for package in self.packages:
            if package.needs_build:
                return True
        return False

    def print_status(self):
        for package in self.packages:
            print('{} {} {}'.format(package.name, package.built_version, package.latest_version))

    def _markRequired(self, pkg):
        if isinstance(pkg, str):
            pkg = self.get_package(pkg)

        if pkg is None:
            return
        elif pkg.required:
            return
        else:
            pkg.required = True
            for dep in pkg.dependencies:
                self._markRequired(dep)

    def get_package(self, name):
        for pkg in self.all_packages:
            possible_names = [pkg.name] + pkg.provides

            if name in possible_names:
                return pkg
