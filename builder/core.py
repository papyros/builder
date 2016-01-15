import os
import os.path

import redis
from celery import Celery, Task
from celery.utils.log import get_task_logger
from github3 import login

from .sources import GitSource


class Container(object):
    objects = []

    def get(self, name):
        return next((obj for obj in self.objects if obj.name == name), None)


class JobTask(Task):
    status = 'Not yet started'


class Object(object):
    name = None
    status = 'Not yet built'

    def set_source(self, workdir, url):
        branch = None
        if '#' in url:
            url, other = url.split('#', 1)

            if '=' in other:
                reftype, branch = other.split('=')

        self.source = GitSource(workdir, url)
        self.branch = branch


base_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
workdir = os.path.join(base_dir, 'working')
chroots_dir = os.path.join(base_dir, 'chroots')

celery = Celery('builder')
celery.config_from_object('config')
celery.Task = JobTask

server_url = celery.conf['SERVER_ROOT']

if celery.conf['CELERY_ALWAYS_EAGER']:
    import logging as logger
    logger.basicConfig(level=logger.DEBUG)
else:
    logger = get_task_logger('builder')

redis_client = redis.Redis()


token = id = ''
with open(os.path.join(base_dir, '.github_auth'), 'r') as fd:
    token = fd.readline().strip()  # Can't hurt to be paranoid
    id = fd.readline().strip()

gh = login(token=token)

if not gh:
    raise Exception('Unable to sign into GitHub!')
