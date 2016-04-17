import os.path

from celery import Celery
from flask_mongoengine import MongoEngine
from flask_assets import Environment

from .config import FlaskConfig

base_dir = os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, 'static')

db = MongoEngine()

celery = Celery('builder')
celery.config_from_object(FlaskConfig)

webassets = Environment()
