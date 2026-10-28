# WordCount Studio — Hadoop MapReduce UI

A local-only dark dashboard that uploads a `.txt` file to HDFS, runs your existing Java `WordCount` JAR, and displays the resulting frequencies.

## Preserves your current project

Expected existing paths:
- Hadoop: `~/hadoop-3.2.3`
- Java: `/usr/lib/jvm/java-17-openjdk-amd64`
- Existing JAR: `~/WordCount/wordcount.jar`

This project does not edit `WordCount.java`, rebuild your JAR, reformat HDFS, or delete your existing HDFS files. Each UI run uses a unique path under `/user/$USER/wordcount_web/runs/`.

## Run it (Ubuntu)

1. Extract `WordCountWeb.zip` into your home folder so you have `~/WordCountWeb/setup.sh`.
2. Open a terminal and run:

   ```bash
   cd ~/WordCountWeb
   bash setup.sh
   ```

3. Open Firefox or Chrome on the same Ubuntu machine and visit:

   `http://127.0.0.1:5000`

4. Upload a `.txt` file and click **Run MapReduce job**.
5. Leave the terminal running while using the UI. Press `Ctrl+C` in that terminal to stop the web server.

The setup script creates a Python virtual environment and installs Flask. It does not install or modify Hadoop.

## Hadoop prerequisites

For the UI to complete a real cluster job:
- HDFS must be running.
- ResourceManager and NodeManager must be running.
- `mapreduce.framework.name` must be `yarn` in `mapred-site.xml`.
- The existing JAR must accept the standard arguments `WordCount <input-path> <output-path>`.
- Java module-opening options needed by your Hadoop 3.2.3 + Java 17 setup should remain in the Hadoop configuration you already adjusted.

If the job fails, read the **Execution logs** section in the UI. The full backend error is also printed in the terminal running `setup.sh`.

## Security

The Flask server binds only to `127.0.0.1`, not to your network. Do not change it to `0.0.0.0` or expose it publicly: the backend can launch Hadoop commands. File uploads are limited to 5 MB and only `.txt` files are accepted.

## Notes

- The dashboard reports total tokens as the sum of emitted word counts and unique words as the number of output rows.
- Runtime is the browser-observed duration for the request.
- CSV export downloads the displayed word/count data.
- Job output directories are intentionally retained in HDFS for inspection and are not automatically deleted.
