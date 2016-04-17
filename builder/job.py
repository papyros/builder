from celery import Task

from builder.model import Status

__author__ = 'Michael Spencer'


class BuildFailure(BaseException):
    pass


class Build(Task):
    job = None
    workdir = None
    status = Status.pending

    def run(self, job, workdir, *args, **kwargs):
        self.job = job
        self.workdir = workdir
        self.status = Status.running

        try:
            self.build(*args, **kwargs)
            self.status = Status.passed
        except BuildFailure as failure:
            self.status = Status.failed
        except Exception as ex:
            self.status = Status.error

    def build(self, *args, **kwargs):
        raise Exception('Not yet implemented!')


class Job(object):
    Build = Build
    title = ''

    def __init__(self, title, build):
        self.title = title
        self.Build = build

    def build(self, *args, **kwargs):
        build = self.Build()

        build.delay(*args, **kwargs)

    @property
    def builds(self):
        return []

    @property
    def latest_build(self):
        return next(iter(self.builds), None)

    @property
    def status(self):
        build = self.latest_build

        return build.status if build else Status.not_built
