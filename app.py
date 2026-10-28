import os
from pathlib import Path
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
API_URL = os.environ.get("WORDCOUNT_API_URL", "").rstrip("/")
API_TOKEN = os.environ.get("WORDCOUNT_API_TOKEN", "")

@app.get("/")
def index():
    return render_template("index.html")

def backend_request(method, path, **kwargs):
    if not API_URL or not API_TOKEN:
        return None, (jsonify({"error": "Hadoop backend is not configured. Set WORDCOUNT_API_URL and WORDCOUNT_API_TOKEN in Render environment variables."}), 503)
    if not API_URL.startswith("https://"):
        return None, (jsonify({"error": "WORDCOUNT_API_URL must use HTTPS."}), 500)
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_TOKEN}"
    try:
        response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=(10, 270), **kwargs)
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": f"Hadoop backend returned a non-JSON response (HTTP {response.status_code})."}
        return (payload, response.status_code), None
    except requests.RequestException:
        return None, (jsonify({"error": "Could not reach the Hadoop backend. Check that Ubuntu, the API, and Cloudflare Tunnel are running."}), 502)

@app.get("/api/status")
def status():
    result, error = backend_request("GET", "/api/status")
    if error:
        return error
    payload, code = result
    return jsonify(payload), code

@app.post("/api/run")
def run_wordcount():
    if "file" not in request.files:
        return jsonify({"error": "Choose a .txt file first."}), 400
    uploaded = request.files["file"]
    if not uploaded.filename or Path(uploaded.filename).suffix.lower() != ".txt":
        return jsonify({"error": "Only .txt files are supported."}), 400
    result, error = backend_request("POST", "/api/run", files={"file": ("upload.txt", uploaded.stream, "text/plain")})
    if error:
        return error
    payload, code = result
    return jsonify(payload), code

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 5 MB."}), 413

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
