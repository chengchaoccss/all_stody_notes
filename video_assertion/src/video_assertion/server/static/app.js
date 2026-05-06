const $ = (id) => document.getElementById(id);

const submitForm = $("submitForm");
const submitBtn = $("submitBtn");
const statusCard = $("statusCard");
const statusLine = $("statusLine");
const resultsTable = $("resultsTable");
const reportCard = $("reportCard");
const reportFrame = $("reportFrame");
const reportLink = $("reportLink");

submitForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const file = $("videoFile").files[0];
  if (!file) return;

  let assertionsText = $("assertions").value.trim();
  try {
    JSON.parse(assertionsText);
  } catch (err) {
    setStatus("failed", "断言不是合法 JSON: " + err.message);
    return;
  }

  const fd = new FormData();
  fd.append("file", file);
  fd.append("assertions", assertionsText);

  submitBtn.disabled = true;
  submitBtn.textContent = "提交中…";
  resultsTable.innerHTML = "";
  reportCard.hidden = true;
  statusCard.hidden = false;
  setStatus("queued", "上传视频中…");

  let jobId;
  try {
    const r = await fetch("/api/v1/jobs", { method: "POST", body: fd });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    const body = await r.json();
    jobId = body.job_id;
    setStatus("queued", `已提交 (job ${jobId})，等待执行…`);
  } catch (err) {
    setStatus("failed", "提交失败: " + err.message);
    submitBtn.disabled = false;
    submitBtn.textContent = "提交";
    return;
  }

  await pollJob(jobId);

  submitBtn.disabled = false;
  submitBtn.textContent = "提交";
});

async function pollJob(jobId) {
  while (true) {
    let job;
    try {
      const r = await fetch(`/api/v1/jobs/${jobId}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      job = await r.json();
    } catch (err) {
      setStatus("failed", "轮询失败: " + err.message);
      return;
    }

    setStatus(
      job.status,
      `Job ${jobId} · 状态 ${job.status}` +
        (job.started_at ? ` · 开始于 ${job.started_at}` : "")
    );

    if (job.status === "completed") {
      renderResults(job.report);
      reportCard.hidden = false;
      reportFrame.src = `/api/v1/jobs/${jobId}/report.html`;
      reportLink.href = `/api/v1/jobs/${jobId}/report.html`;
      return;
    }
    if (job.status === "failed") {
      setStatus("failed", `失败: ${job.error || "(no detail)"}`);
      return;
    }
    await sleep(1500);
  }
}

function renderResults(report) {
  if (!report || !report.results) return;
  const rows = report.results
    .map(
      (r) => `
      <tr>
        <td>${escapeHtml(r.text)}</td>
        <td><span class="kind">${r.kind}</span></td>
        <td class="${r.passed ? "pass" : "fail"}">
          ${r.passed ? "PASS" : "FAIL"} (${r.confidence.toFixed(2)})
        </td>
        <td>${escapeHtml(r.evidence)}</td>
      </tr>`
    )
    .join("");
  const passed = report.results.filter((r) => r.passed).length;
  resultsTable.innerHTML = `
    <p>共 ${report.results.length} 条断言，通过 ${passed} 条。</p>
    <table>
      <thead><tr><th>断言</th><th>类型</th><th>结果</th><th>证据</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function setStatus(klass, text) {
  statusLine.className = "status " + klass;
  statusLine.textContent = text;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
