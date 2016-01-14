from flask import Flask, request, jsonify
from builder import Builder
import sys

app = Flask(__name__)

@app.route("/github/event_handler", methods=['POST'])
def handle_github_event():
    type = request.headers.get('X_GITHUB_EVENT', None)

    if type == 'pull_request':
        action = request.json['action']
        if action == 'opened' or action == 'synchronize':
            builder.continuous.process_pull_request(request.json['pull_request'])
            return jsonify(status='success')
    elif type == 'push':
        builder.continuous.process_push(request.json)
        return jsonify(status='success')
    return jsonify(status='ignored')

if __name__ == "__main__":
    builder = Builder(sys.argv[1])
    app.run(debug=True)
