#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
HADOOP_HOME="${HADOOP_HOME:-$HOME/hadoop-3.2.3}"
WORDCOUNT_JAR="${WORDCOUNT_JAR:-$HOME/WordCount/wordcount.jar}"

if [[ ! -x "$JAVA_HOME/bin/java" ]]; then
  echo "ERROR: Java not found at $JAVA_HOME"
  echo "Set JAVA_HOME to your installed Java directory and retry."
  exit 1
fi
if [[ ! -x "$HADOOP_HOME/bin/hadoop" ]]; then
  echo "ERROR: Hadoop not found at $HADOOP_HOME"
  echo "Expected your existing Hadoop installation at ~/hadoop-3.2.3."
  exit 1
fi
if [[ ! -f "$WORDCOUNT_JAR" ]]; then
  echo "ERROR: WordCount JAR not found at $WORDCOUNT_JAR"
  echo "The existing Java project must be at ~/WordCount/wordcount.jar."
  exit 1
fi

export JAVA_HOME HADOOP_HOME WORDCOUNT_JAR
export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-$HADOOP_HOME/etc/hadoop}"
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH"

if [[ ! -d "$APP_DIR/venv" ]]; then
  python3 -m venv "$APP_DIR/venv" || {
    echo
    echo "Could not create a Python virtual environment."
    echo "On Ubuntu, install the venv package with your system package manager, then run setup.sh again."
    exit 1
  }
fi

"$APP_DIR/venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/venv/bin/python" -m pip install flask

echo
echo "Checking Hadoop and JAR..."
"$HADOOP_HOME/bin/hadoop" version | head -n 1
echo "JAR: $WORDCOUNT_JAR"
echo
echo "Starting WordCount Studio at http://127.0.0.1:5000"
echo "Keep this terminal open while using the dashboard. Press Ctrl+C to stop."
cd "$APP_DIR"
exec "$APP_DIR/venv/bin/python" app.py
