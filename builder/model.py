from builder.util import StrEnum

__author__ = 'Michael Spencer'


class Status(StrEnum):
    pending = 'pending'
    not_built = 'not_built'
    running = 'running'
    passed = 'passed'
    error = 'error'
    failed = 'failed'


class BuildInfo(object):
    status = Status.error
