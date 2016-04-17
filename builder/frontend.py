from flask import url_for, redirect, request
from flask.blueprints import Blueprint
from flask.templating import render_template

from builder import config

__author__ = 'Michael Spencer'


blueprint = Blueprint('frontend', import_name=__name__)


@blueprint.route('/')
def index():
    return redirect(url_for('frontend.jobs'))


@blueprint.route('/jobs')
def jobs():
    selected = request.args.get('selected', None)

    selected_job = config.jobs[int(selected)] if selected else config.jobs[0]
    print(selected, selected_job)
    return render_template('jobs.html', jobs=config.jobs, selected_job=selected_job)
