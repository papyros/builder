from flask.blueprints import Blueprint
from flask.templating import render_template

from builder import config

__author__ = 'Michael Spencer'


blueprint = Blueprint('frontend', import_name=__name__)


@blueprint.route('/')
def index():
    return render_template('jobs.html', jobs=config.jobs)
