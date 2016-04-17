from builder import create_app

import sample_config

app = create_app('builder.config.FlaskConfig')


if __name__ == "__main__":
    app.run()
