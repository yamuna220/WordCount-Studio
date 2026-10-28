import hmac
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, request

JAVA_HOME = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")
HADOOP_HOME = os.environ.get("HADOOP_HOME", str(Path.home() / "hadoop-3.2.3"))
WORDCOUNT_JAR = Path(os.environ.get("WORDCOUNT_JAR", str(Path.home() / "WordCount" / "wordcount.jar"))).resolve()
API_TOKEN = os.environ.get("WORDCOUNT_API_TOKEN", "")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ENV = os.environ.copy()
ENV.update({
    "JAVA_HOME": JAVA_HOME,
    "HADOOP_HOME": HADOOP_HOME,
    "HADOOP_CONF_DIR": os.environ.get("HADOOP_CONF_DIR", str(Path(HADOOP_HOME) / "etc" / "hadoop")),
    "PATH": f"{JAVA_HOME}/bin:{HADOOP_HOME}/bin:{HADOOP_HOME}/sbin:" + os.environ.get("PATH", ""),
})

def require_token(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("Authorization", "")
        expected = f"Bearer {API_TOKEN}" if API_TOKEN else ""
        if not API_TOKEN or not hmac.compare_digest(supplied, expected):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapped

def run_command(args, timeout=180):
    completed = subprocess.run([str(a) for a in args], env=ENV, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
    output = completed.stdout or ""
    if completed.returncode != 0:
        raise RuntimeError(output[-8000:] or f"Command failed with exit code {completed.returncode}")
    return output

def hdfs_path(path):
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", path):
        raise RuntimeError("Generated HDFS path failed validation")
    return path

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.get("/api/status")
@require_token
def status():
    data = {"jar_exists": WORDCOUNT_JAR.is_file(), "jar_path": str(WORDCOUNT_JAR), "hadoop_home": HADOOP_HOME, "java_home": JAVA_HOME}
    try:
        data["hadoop_version"] = run_command(["hadoop", "version"], timeout=20).splitlines()[0]
        run_command(["hdfs", "dfs", "-ls", "/"], timeout=20)
        data["hdfs"] = "connected"
    except Exception as exc:
        data["error"] = str(exc)[-1500:]
    return jsonify(data)

@app.post("/api/run")
@require_token
def run_wordcount():
    if "file" not in request.files:
        return jsonify({"error": "Choose a .txt file first."}), 400
    uploaded = request.files["file"]
    if not uploaded.filename or Path(uploaded.filename).suffix.lower() != ".txt":
        return jsonify({"error": "Only .txt files are supported."}), 400
    if not WORDCOUNT_JAR.is_file():
        return jsonify({"error": f"WordCount JAR not found: {WORDCOUNT_JAR}"}), 500
    run_id = uuid.uuid4().hex[:12]
    username = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("USER", "iot")) or "iot"
    base = hdfs_path(f"/user/{username}/wordcount_web/runs/{run_id}")
    input_dir, output_dir = f"{base}/input", f"{base}/output"
    try:
        with tempfile.TemporaryDirectory(prefix="wordcount-api-") as temp_dir:
            local_file = Path(temp_dir) / "input.txt"
            uploaded.save(local_file)
            if local_file.stat().st_size == 0:
                return jsonify({"error": "The uploaded file is empty."}), 400
            logs = [f"$ hdfs dfs -mkdir -p {input_dir}"]
            logs.append(run_command(["hdfs", "dfs", "-mkdir", "-p", input_dir], timeout=30))
            logs.append(f"$ hdfs dfs -put input.txt {input_dir}/input.txt")
            logs.append(run_command(["hdfs", "dfs", "-put", str(local_file), f"{input_dir}/input.txt"], timeout=30))
            logs.append(f"$ hadoop jar {WORDCOUNT_JAR} WordCount {input_dir} {output_dir}")
            logs.append(run_command(["hadoop", "jar", str(WORDCOUNT_JAR), "WordCount", input_dir, output_dir], timeout=240)[-14000:])
            output = run_command(["hdfs", "dfs", "-cat", f"{output_dir}/part-r-00000"], timeout=30)
            rows = []
            for line in output.splitlines():
                parts = line.rsplit(None, 1)
                if len(parts) == 2:
                    try: rows.append({"word": parts[0], "count": int(parts[1])})
                    except ValueError: pass
            rows.sort(key=lambda row: (-row["count"], row["word"].lower()))
            return jsonify({"success": True, "run_id": run_id, "hdfs_input": input_dir,
                "hdfs_output": output_dir, "rows": rows, "unique_words": len(rows),
                "total_words": sum(row["count"] for row in rows),
                "logs": "\n".join(x for x in logs if x.strip())[-18000:],
                "message": "MapReduce job completed successfully."})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "The Hadoop job timed out. Check YARN and Hadoop logs."}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)[-8000:], "hint": "Check HDFS/YARN health and the Hadoop logs."}), 500

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 5 MB."}), 413

if __name__ == "__main__":
    if not API_TOKEN or len(API_TOKEN) < 32:
        raise SystemExit("Set WORDCOUNT_API_TOKEN to a random secret of at least 32 characters before starting.")
    app.run(host="127.0.0.1", port=8000, debug=False)
