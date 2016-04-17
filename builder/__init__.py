import logging
from flask import Flask

from builder import assets, filters
from .core import db, celery
from .frontend import blueprint


# application factory, see: http://flask.pocoo.org/docs/patterns/appfactories/
def create_app(config_path, config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config_path)

    if config_overrides is not None:
        app.config.update(config_overrides)

    db.init_app(app)
    assets.init_app(app)
    filters.init_app(app)

    logging.basicConfig()

    app.register_blueprint(blueprint)

    return app
