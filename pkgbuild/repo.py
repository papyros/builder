import os.path
import networkx as nx

from .package import Package
from utils import load_yaml

class Repository:
    def __init__(self, name, arch, packages, workdir):
        self.name = name
        self.arch = arch
        self.workdir = workdir
        self.repo_dir = os.path.join(workdir, 'built_packages')
        self.database = os.path.join(self.repo_dir, name + '.db.tar.gz')
        self.package_names = packages

    def refresh(self):
        all_package_names = self.find_packages()
        self.all_packages = [Package(self, name) for name in all_package_names]

        print('Refreshing package statuses...')
        for package in self.all_packages:
            package.refresh()

        # Update the list of dependencies removing dependencies provided by the system
        for package in self.all_packages:
            package.dependencies = [dependency for dependency in package.dependencies
                                    if self.get_package(dependency) is not None]

        # Recursively mark requested packages and all their dependencies as required
        for name in self.package_names:
            self._markRequired(name)

        # Sort packages based on their dependencies
        graph = nx.DiGraph()
        for pkg in pkg_info:
            if len(pkg.dependencies) == 0:
                graph.add_node(pkg.name)
            else:
                for dep in pkg.dependencies:
                    if dep != pkg.name:
                        graph.add_edge(dep, pkg.name)
        sorted_names = nx.topological_sort(graph)

        self.packages = [self.get_package(name) for name in sorted_names
                         if self.get_package(name).required]

        if len(self.packages) == 0:
            raise Exception('No packages to build!')

    def build(self):
        print('Building packages')
        for package in self.packages:
            package.build()

    def from_channel_config(config, arch, workdir):
        if isinstance(config, basestr):
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
        if isinstance(pkg, basestring):
            pkg = self.get_package(pkg)

        if pkg is None:
            return
        elif pkg.required:
            return
        else:
            pkg.required = True
            for dep in pkg['depends']:
                self._markRequired(dep)

    def get_package(self, name):
        for pkg in self.all_packages.values():
            possible_names = [pkg['name']] + pkg['provides']

            if name in possible_names:
                return pkg
