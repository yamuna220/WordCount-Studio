# WordCount Studio

**Live Demo:** [https://wordcount-studio.onrender.com/](https://wordcount-studio.onrender.com/)

A dark Flask dashboard for submitting `.txt` files to a Hadoop 3.2.3 backend and displaying actual MapReduce word counts.
## Architecture
- Render runs the web dashboard (`app.py`) and forwards API requests to `WORDCOUNT_API_URL` using the bearer token in `WORDCOUNT_API_TOKEN`.
- `backend/app.py` runs on the Ubuntu host alongside Hadoop. It accepts only authenticated status and WordCount requests, limits uploads to 5 MB, invokes fixed Hadoop commands without a shell, and preserves the existing JAR.
- A Cloudflare Tunnel can expose the local API over HTTPS without opening Hadoop ports on the router. Keep the API bound to `127.0.0.1`.

## Render configuration
Build command: `pip install -r requirements.txt`
Start command: `gunicorn --bind 0.0.0.0:$PORT app:app`
Environment variables (set in Render dashboard, never commit secrets):
- `WORDCOUNT_API_URL`: HTTPS tunnel URL, without a trailing slash
- `WORDCOUNT_API_TOKEN`: same long random token configured on the Ubuntu backend

## Ubuntu backend
Install backend dependency with `python3 -m pip install --user -r backend/requirements.txt` (or use a virtual environment). Set `WORDCOUNT_API_TOKEN` to a randomly generated secret of at least 32 characters, then run `python3 backend/app.py`. The API listens only on `127.0.0.1:8000`.

Set `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`, `HADOOP_HOME=$HOME/hadoop-3.2.3`, and `WORDCOUNT_JAR=$HOME/WordCount/wordcount.jar` if your paths differ. Keep HDFS/YARN running. Do not expose ports 9000, 9870, or 8088 publicly.

## Security
- Never commit API tokens.
- Do not bind the backend to `0.0.0.0` or forward Hadoop ports.
- Keep the tunnel and backend running only while you need remote access. A Cloudflare Quick Tunnel URL changes when restarted; update Render's `WORDCOUNT_API_URL` after it changes. For a persistent URL, configure a named tunnel with a domain in Cloudflare.
- A public site can trigger real Hadoop jobs. Only share it with trusted users and rotate the token if exposed.
