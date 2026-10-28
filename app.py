import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

APP_DIR = Path(__file__).resolve().parent
JAVA_HOME = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")
HADOOP_HOME = os.environ.get("HADOOP_HOME", str(Path.home() / "hadoop-3.2.3"))
WORDCOUNT_JAR = Path(os.environ.get("WORDCOUNT_JAR", str(Path.home() / "WordCount" / "wordcount.jar")))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

ENV = os.environ.copy()
ENV["JAVA_HOME"] = JAVA_HOME
ENV["HADOOP_HOME"] = HADOOP_HOME
ENV["HADOOP_CONF_DIR"] = os.environ.get("HADOOP_CONF_DIR", str(Path(HADOOP_HOME) / "etc" / "hadoop"))
ENV["PATH"] = f"{JAVA_HOME}/bin:{HADOOP_HOME}/bin:{HADOOP_HOME}/sbin:" + ENV.get("PATH", "")

def run_command(args, timeout=180):
    """Run a fixed command safely (no shell) and return combined output."""
    completed = subprocess.run(
        [str(a) for a in args],
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout or ""
    if completed.returncode != 0:
        raise RuntimeError(output[-12000:] or f"Command failed with exit code {completed.returncode}")
    return output

def safe_hdfs_path(path):
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", path):
        raise RuntimeError("Generated HDFS path did not pass validation.")
    return path

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def status():
    checks = {}
    try:
        checks["hadoop_version"] = run_command(["hadoop", "version"], timeout=20).splitlines()[0]
        run_command(["hdfs", "dfs", "-ls", "/"], timeout=20)
        checks["hdfs"] = "connected"
    except Exception as exc:
        checks["error"] = str(exc)[-1800:]
    checks["jar_exists"] = WORDCOUNT_JAR.is_file()
    checks["jar_path"] = str(WORDCOUNT_JAR)
    checks["hadoop_home"] = HADOOP_HOME
    checks["java_home"] = JAVA_HOME
    return jsonify(checks)

@app.post("/api/run")
def run_wordcount():
    if "file" not in request.files:
        return jsonify({"error": "Choose a .txt file first."}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "Choose a file first."}), 400
    if Path(uploaded.filename).suffix.lower() != ".txt":
        return jsonify({"error": "Only .txt files are supported."}), 400
    if not WORDCOUNT_JAR.is_file():
        return jsonify({"error": f"WordCount JAR not found: {WORDCOUNT_JAR}"}), 500

    run_id = uuid.uuid4().hex[:12]
    hdfs_base = safe_hdfs_path(f"/user/{os.environ.get('USER', 'iot')}/wordcount_web/runs/{run_id}")
    hdfs_input_dir = f"{hdfs_base}/input"
    hdfs_input_file = f"{hdfs_input_dir}/input.txt"
    hdfs_output_dir = f"{hdfs_base}/output"

    try:
        with tempfile.TemporaryDirectory(prefix="wordcount-web-") as temp_dir:
            local_file = Path(temp_dir) / "input.txt"
            uploaded.save(local_file)
            if local_file.stat().st_size == 0:
                return jsonify({"error": "The uploaded file is empty."}), 400

            logs = []
            logs.append(f"$ hdfs dfs -mkdir -p {hdfs_input_dir}")
            logs.append(run_command(["hdfs", "dfs", "-mkdir", "-p", hdfs_input_dir], timeout=30))
            logs.append(f"$ hdfs dfs -put input.txt {hdfs_input_file}")
            logs.append(run_command(["hdfs", "dfs", "-put", str(local_file), hdfs_input_file], timeout=30))
            logs.append(f"$ hadoop jar {WORDCOUNT_JAR} WordCount {hdfs_input_dir} {hdfs_output_dir}")
            job_output = run_command(
                ["hadoop", "jar", str(WORDCOUNT_JAR), "WordCount", hdfs_input_dir, hdfs_output_dir],
                timeout=240,
            )
            logs.append(job_output[-18000:])

            result = run_command(["hdfs", "dfs", "-cat", f"{hdfs_output_dir}/part-r-00000"], timeout=30)
            rows = []
            for line in result.splitlines():
                parts = line.rsplit(None, 1)
                if len(parts) == 2:
                    try:
                        rows.append({"word": parts[0], "count": int(parts[1])})
                    except ValueError:
                        continue
            rows.sort(key=lambda row: (-row["count"], row["word"].lower()))
            total = sum(row["count"] for row in rows)
            return jsonify({
                "success": True,
                "run_id": run_id,
                "hdfs_input": hdfs_input_dir,
                "hdfs_output": hdfs_output_dir,
                "rows": rows,
                "unique_words": len(rows),
                "total_words": total,
                "logs": "\n".join(part for part in logs if part.strip())[-22000:],
                "message": "MapReduce job completed successfully.",
            })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "The Hadoop job timed out. Check YARN and the Hadoop logs, then retry."}), 504
    except Exception as exc:
        return jsonify({
            "error": str(exc)[-12000:],
            "hint": "Confirm HDFS and YARN are running, and that mapreduce.framework.name is set to yarn.",
        }), 500

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 5 MB."}), 413

if __name__ == "__main__":
    # Local-only by default; do not expose this command-executing UI to a public network.
    app.run(host="127.0.0.1", port=5000, debug=False)
