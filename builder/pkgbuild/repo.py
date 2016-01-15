import os.path

import networkx as nx

from ..utils import flatten, load_yaml

from .package import Package


class Repository:
    def __init__(self, name, arch, config, workdir, export_dir):
        self.name = name
        self.arch = arch
        self.workdir = workdir
        self.export_dir = export_dir
        self.repo_dir = os.path.join(workdir, 'built_packages')
        self.database = os.path.join(self.repo_dir, name + '.db.tar.gz')

        self.package_names = flatten([config['channels'][name]['packages']
                                     for name in config['channels']])

    def load(self):
        self.buildinfo = load_yaml(os.path.join(self.workdir, "buildinfo.yml"))
        self.build_number = self.buildinfo.get('build_number', 0) + 1

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

    @property
    def changelog(self):
        changes = ['{}:\n{}'.format(pkg.name, pkg.changes) for pkg in self.packages
                   if pkg.changes is not None]
        if len(changes) > 0:
            return '\n\n'.join(changes)
        else:
            return 'No changes'
