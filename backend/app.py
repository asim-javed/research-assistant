from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app)


@app.route("/api/hello")
def hello():
    return jsonify(message="Hello from Flask!")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
