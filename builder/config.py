__author__ = 'Michael Spencer'

jobs = []


class FlaskConfig:
    BROKER_URL = 'redis://'
    CELERY_RESULT_BACKEND = 'redis://'

    CELERY_TIMEZONE = 'America/Chicago'
    CELERY_ENABLE_UTC = True
    # CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    SERVER_ROOT = 'http://build.papyros.io'

    DEBUG = True
