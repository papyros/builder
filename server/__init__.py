from flask import Flask, request
from builder import Builder
import sys

app = Flask(__name__)

@app.route("/github/event_handler")
def handle_github_event():
    type = request.headers.get('HTTP_X_GITHUB_EVENT', None)
    json = request.json()

    if type == 'pull_request':
        builder.continuous.process_pull_request(json['pull_request'])

if __name__ == "__main__":
    builder = Builder(sys.argv[1])
    app.run()
