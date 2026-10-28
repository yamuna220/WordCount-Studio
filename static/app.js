const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const fileMeta = document.getElementById("file-meta");
const fileLabel = document.getElementById("file-label");
const pickedName = document.getElementById("picked-name");
const pickedSize = document.getElementById("picked-size");
const runButton = document.getElementById("run-button");
const buttonLabel = document.getElementById("button-label");
const resultsBody = document.getElementById("results-body");
const searchInput = document.getElementById("search-input");
const exportButton = document.getElementById("export-button");
const logConsole = document.getElementById("log-console");
const toast = document.getElementById("toast");
let allRows = [];
let lastRunAt = null;
let timerId = null;
const navItems = [...document.querySelectorAll(".nav-item[data-target]")];
const navNames = { overview: "Overview", "run-job": "MapReduce Jobs", results: "Input & Results", logs: "Execution Logs" };


function navigateTo(targetId) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  navItems.forEach(item => {
    const active = item.dataset.target === targetId;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  const breadcrumb = document.getElementById("breadcrumb-current");
  if (breadcrumb) breadcrumb.textContent = navNames[targetId] || "Workspace";
  document.getElementById("sidebar")?.classList.remove("mobile-open");
  const menu = document.getElementById("mobile-menu");
  if (menu) menu.setAttribute("aria-expanded", "false");
}
navItems.forEach(item => item.addEventListener("click", () => navigateTo(item.dataset.target)));
document.getElementById("mobile-menu")?.addEventListener("click", () => {
  const sidebar = document.getElementById("sidebar");
  const opened = sidebar.classList.toggle("mobile-open");
  document.getElementById("mobile-menu").setAttribute("aria-expanded", String(opened));
});

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(timerId);
  timerId = setTimeout(() => toast.classList.remove("show"), 3500);
}
function formatSize(bytes) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}
function setStatus(message, type = "ready") {
  const el = document.getElementById("job-status");
  el.innerHTML = `<span class="status-dot" style="${type === "error" ? "background:#ff7777;box-shadow:0 0 12px #ff777755" : type === "running" ? "background:#ffbd70;box-shadow:0 0 12px #ffbd7055" : ""}"></span>${message}`;
}
function setPipeline(state) {
  const ids = ["pipe-input", "pipe-map", "pipe-reduce", "pipe-output"];
  const labels = state === "done" ? ["Uploaded", "Complete", "Complete", "Available"] :
    state === "running" ? ["Queued", "Running", "Pending", "Pending"] :
    ["Waiting", "Waiting", "Waiting", "Waiting"];
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    el.textContent = labels[i];
    el.classList.toggle("done", state === "done");
  });
}
function appendLogs(text, type = "") {
  if (!text) return;
  const lines = String(text).split("\n");
  lines.forEach(line => {
    const div = document.createElement("div");
    div.className = `log-line ${type}`;
    div.textContent = line;
    logConsole.appendChild(div);
  });
  logConsole.scrollTop = logConsole.scrollHeight;
}
function renderRows() {
  const q = searchInput.value.trim().toLowerCase();
  const rows = allRows.filter(r => r.word.toLowerCase().includes(q));
  document.getElementById("row-count").textContent = `${rows.length} row${rows.length === 1 ? "" : "s"}`;
  if (!rows.length) {
    resultsBody.innerHTML = `<tr class="empty-row"><td colspan="4"><div class="empty-state"><div class="empty-icon">⌕</div><strong>No matching words</strong><span>Try another search term.</span></div></td></tr>`;
    return;
  }
  const max = Math.max(...allRows.map(r => r.count), 1);
  resultsBody.innerHTML = rows.map((r, i) => `
    <tr><td>${String(i + 1).padStart(2, "0")}</td><td class="word-cell">${escapeHtml(r.word)}</td><td class="count-cell">${r.count.toLocaleString()}</td>
    <td class="bar-cell"><div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, r.count / max * 100)}%"></div></div></td></tr>
  `).join("");
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function clearPickedFile() {
  fileInput.value = "";
  fileMeta.hidden = true;
  dropZone.hidden = false;
}
function useFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".txt")) {
    showToast("Please choose a .txt file.");
    fileInput.value = "";
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showToast("File must be 5 MB or smaller.");
    fileInput.value = "";
    return;
  }
  fileMeta.hidden = false;
  dropZone.hidden = true;
  pickedName.textContent = file.name;
  pickedSize.textContent = formatSize(file.size);
}
fileInput.addEventListener("change", () => useFile(fileInput.files[0]));
document.getElementById("remove-file").addEventListener("click", clearPickedFile);
["dragenter", "dragover"].forEach(ev => dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add("dragover"); }));
["dragleave", "drop"].forEach(ev => dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.remove("dragover"); }));
dropZone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  useFile(file);
});
searchInput.addEventListener("input", renderRows);
document.getElementById("clear-logs").addEventListener("click", () => {
  logConsole.replaceChildren();
  appendLogs("Log view cleared.", "dim");
});
exportButton.addEventListener("click", () => {
  if (!allRows.length) return;
  const csv = "word,count\n" + allRows.map(r => `"${r.word.replace(/"/g, '""')}",${r.count}`).join("\n");
  const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
  const a = document.createElement("a");
  a.href = url; a.download = "wordcount-results.csv"; a.click();
  URL.revokeObjectURL(url);
});
form.addEventListener("submit", async e => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) { showToast("Choose a .txt file first."); return; }
  runButton.disabled = true;
  buttonLabel.textContent = "Running Hadoop job…";
  setStatus("Job running", "running");
  setPipeline("running");
  appendLogs(`\n[${new Date().toLocaleTimeString()}] Submitting ${file.name} to Hadoop…`);
  lastRunAt = performance.now();
  const data = new FormData();
  data.append("file", file);
  try {
    const response = await fetch("/api/run", {method: "POST", body: data});
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      setStatus("Job failed", "error");
      setPipeline("idle");
      appendLogs(payload.error || "Job failed without an error message.", "error");
      if (payload.hint) appendLogs(payload.hint, "dim");
      showToast("The Hadoop job failed. Check execution logs below.");
      return;
    }
    allRows = payload.rows || [];
    renderRows();
    document.getElementById("total-words").textContent = (payload.total_words || 0).toLocaleString();
    document.getElementById("unique-words").textContent = (payload.unique_words || 0).toLocaleString();
    document.getElementById("runtime").textContent = `${((performance.now() - lastRunAt) / 1000).toFixed(1)}s`;
    document.getElementById("hdfs-path").textContent = `HDFS output: ${payload.hdfs_output}`;
    document.getElementById("result-summary").textContent = `Run ${payload.run_id} · Completed`;
    exportButton.disabled = !allRows.length;
    setStatus("Completed successfully");
    setPipeline("done");
    appendLogs(payload.logs, "success");
    appendLogs(`SUCCESS: ${payload.total_words} total tokens · ${payload.unique_words} unique words.`, "success");
    showToast("MapReduce job completed successfully.");
  } catch (err) {
    setStatus("Connection error", "error");
    setPipeline("idle");
    appendLogs(`Request failed: ${err.message}`, "error");
    showToast("Cannot reach the local Flask backend.");
  } finally {
    runButton.disabled = false;
    buttonLabel.textContent = "Run MapReduce job";
  }
});
async function checkStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    const state = document.getElementById("cluster-state");
    const pulse = document.getElementById("cluster-pulse");
    if (data.jar_exists && data.hadoop_version && data.hdfs === "connected") {
      state.textContent = `${data.hadoop_version} · HDFS connected · JAR found`;
      pulse?.classList.remove("offline");
    } else {
      const problems = [];
      if (!data.hadoop_version) problems.push("Hadoop unavailable");
      if (data.hdfs !== "connected") problems.push("HDFS unavailable");
      if (!data.jar_exists) problems.push("JAR not found");
      state.textContent = problems.join(" · ") || "Check Hadoop configuration";
      pulse?.classList.add("offline");
    }
    if (!data.jar_exists) appendLogs(`Configured WordCount JAR not found: ${data.jar_path}`, "error");
    if (data.error) appendLogs(data.error, "error");
  } catch (_) {
    document.getElementById("cluster-state").textContent = "Backend unavailable";
  }
}
checkStatus();
