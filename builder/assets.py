from flask_assets import Bundle
from webassets.filter import get_filter
from .core import webassets, static_dir
import os.path

__author__ = 'Michael Spencer'


scss = get_filter('scss', as_output=True, load_paths=[os.path.join(static_dir, 'css')])


# Application styles
css = Bundle("css/main.scss",
             filters=scss, output="dist/builder.css",
             debug=False)

# Minified CSS
min_css = Bundle(css, filters="cssmin", output="dist/build.min.css")


def init_app(app):
    webassets.app = app
    webassets.init_app(app)
    webassets.register('css', min_css)
    webassets.manifest = 'cache' if not app.debug else False
    webassets.cache = not app.debug
    webassets.debug = app.debug
