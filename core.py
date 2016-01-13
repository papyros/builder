import os.path
from celery import Celery, Task
from celery.utils.log import get_task_logger

class Container(object):
    @property
    def triggers(self):
        return []

    @property
    def objects(self):
        return []

class JobTask(Task):
    status = 'Not yet started'

class Object(object):
    status = 'Not yet built'

class Trigger(object):
    def run(self):
        pass

base_dir = os.path.abspath(os.path.dirname(__file__))
workdir = os.path.join(base_dir, 'checkout')
chroots_dir = os.path.join(base_dir, 'chroots')

celery = Celery('builder')
celery.config_from_object('config')
celery.Task = JobTask

logger = get_task_logger('builder')
