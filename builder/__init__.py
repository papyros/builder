from builder.continuous import ContinuousIntegration
from builder.iso import ISOContainer
from builder.pkgbuild import RepositoryContainer
from builder.utils import load_yaml


class Builder(object):
    def __init__(self, filename):
        self.config = load_yaml(filename)
        self.continuous = ContinuousIntegration(self.config.get('continuous', []))
        self.isos = ISOContainer(self.config.get('isos', []))
        self.repositories = RepositoryContainer(self.config.get('repositories', []))
