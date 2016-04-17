from builder import config
from builder.job import Build, Job

__author__ = 'Michael Spencer'


class SampleBuild(Build):
    def build(self, *args, **kwargs):
        pass


config.jobs = [Job('Test job', SampleBuild)]
