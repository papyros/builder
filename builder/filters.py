from builder.model import Status

__author__ = 'Michael Spencer'


def init_app(app):
    app.template_filter('status_color')(status_color)
    app.template_filter('status_text')(status_text)
    app.template_filter('status_icon')(status_icon)


def status_color(status):
    if status == Status.not_built:
        return 'grey'
    elif status == Status.pending:
        return 'grey'
    elif status == Status.passed:
        return 'green'
    elif status == Status.failed:
        return 'red'
    elif status == Status.error:
        return 'red'
    elif status == Status.running:
        return 'yellow'
    else:
        return 'grey'


def status_text(status):
    if status == Status.not_built:
        return 'Not built'
    elif status == Status.pending:
        return 'Pending'
    elif status == Status.passed:
        return 'Passed'
    elif status == Status.failed:
        return 'Failed'
    elif status == Status.error:
        return 'Error'
    elif status == Status.running:
        return 'Running'
    else:
        return 'Unknown'


def status_icon(status):
    if status == Status.not_built:
        return 'minus circle'
    elif status == Status.pending:
        return 'wait'
    elif status == Status.passed:
        return 'checkmark'
    elif status == Status.failed:
        return 'warning sign'
    elif status == Status.error:
        return 'warning circle'
    elif status == Status.running:
        return 'spinner'
    else:
        return 'help circle'
