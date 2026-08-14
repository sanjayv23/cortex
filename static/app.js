let currentReportMarkdown = "";

document.addEventListener("DOMContentLoaded", () => {
  fetchStatus();
  fetchDocsList();
});

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.status === "online") {
      document.getElementById("dbCountText").innerText = `Vector DB: ${data.vector_count} Chunks`;
    }
  } catch (err) {
    document.getElementById("dbCountText").innerText = "Vector DB: Offline";
  }
}

async function fetchDocsList() {
  const container = document.getElementById("docsListContainer");
  if (!container) return;
  try {
    const res = await fetch("/api/docs");
    const data = await res.json();
    if (data.docs && data.docs.length > 0) {
      container.innerHTML = data.docs.map(d => `📄 ${d}`).join("<br>");
    } else {
      container.innerHTML = `<span style="color: var(--text-muted);">No external documents uploaded yet.</span>`;
    }
  } catch (err) {
    container.innerHTML = `Failed to load documents list.`;
  }
}

async function uploadSelectedFile() {
  const fileInput = document.getElementById("fileInput");
  const statusText = document.getElementById("uploadStatusText");
  if (!fileInput.files || fileInput.files.length === 0) return;

  const file = fileInput.files[0];
  statusText.innerText = `Uploading and parsing '${file.name}'...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload_doc", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "File upload failed.");
    }

    const data = await res.json();
    statusText.innerText = `✅ Successfully uploaded '${file.name}'! Created ${data.chunks_added} vector chunks (ID: ${data.source_id}).`;
    fetchStatus();
    fetchDocsList();
    fileInput.value = "";
  } catch (err) {
    alert("Upload error: " + err.message);
    statusText.innerText = `⚠️ Upload failed: ${err.message}`;
  }
}


function setTopic(text) {
  document.getElementById("topicInput").value = text;
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  
  event.currentTarget.classList.add("active");
  document.getElementById(tabId).classList.add("active");
}

function toggleIngestDrawer() {
  const drawer = document.getElementById("ingestDrawer");
  drawer.classList.toggle("active");
}

async function runPipeline() {
  const topicInput = document.getElementById("topicInput");
  const topic = topicInput.value.trim();

  if (!topic) {
    alert("Please enter a research topic.");
    return;
  }

  const runBtn = document.getElementById("runBtn");
  const runBtnText = document.getElementById("runBtnText");
  runBtn.disabled = true;
  runBtnText.innerText = "Running Agents...";

  // Reset visual agent cards
  resetAgentCards();
  setAgentActive("Researcher", "Querying Vector DB & Synthesizing...");
  updatePipelineStatus("Step 1/3: Researcher agent decomposing topic & gathering evidence...");
  appendLog("text-info", `[PIPELINE START] Topic: "${topic}"`);

  try {
    const startRes = await fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic })
    });

    if (!startRes.ok) {
      const err = await startRes.json();
      throw new Error(err.detail || "Failed to start pipeline.");
    }

    const { job_id } = await startRes.json();
    const data = await pollResearchJob(job_id);

    currentReportMarkdown = data.final_report;

    if (data.revision_count > 0) {
      document.getElementById("revisionCountTag").innerText = `Revisions: ${data.revision_count}/2`;
      document.getElementById("badgeWriter").classList.add("revision");
      appendLog("text-warning", `[REVISION LOOP] Editor requested ${data.revision_count} revision pass(es). Feedback: ${data.editor_feedback}`);
    }

    setAgentDone("Editor", data.revision_count > 0 ? "Approved (Post-Revision)" : "Approved");
    updatePipelineStatus("✅ Research Pipeline Complete! Report ready.");
    appendLog("text-success", `[PIPELINE COMPLETE] Final report ready. Saved to ${data.saved_filename}`);

    // Render output markdown
    renderReport(data.final_report);
    renderNotes(data.research_notes);
    renderLogs(data.steps_log);
    renderDetailedSteps(data.detailed_steps);

    fetchStatus();
  } catch (err) {
    alert("Error running research pipeline: " + err.message);
    appendLog("text-warning", `[ERROR] ${err.message}`);
    updatePipelineStatus("⚠️ Execution error occurred.");
  } finally {
    runBtn.disabled = false;
    runBtnText.innerText = "Run Research Pipeline";
  }
}

// Polls a background research job until it completes or errors. Running the
// pipeline as one long synchronous request used to trip reverse-proxy gateway
// timeouts (several minutes across multiple LLM calls/revision passes), so the
// backend now runs it in a background thread and this polls for progress.
async function pollResearchJob(jobId) {
  let lastStepCount = 0;
  const POLL_INTERVAL_MS = 2000;

  while (true) {
    const res = await fetch(`/api/research/${jobId}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to fetch job status.");
    }
    const job = await res.json();

    if (job.detailed_steps && job.detailed_steps.length > lastStepCount) {
      renderDetailedSteps(job.detailed_steps);
      const newSteps = job.detailed_steps.slice(lastStepCount);
      lastStepCount = job.detailed_steps.length;

      newSteps.forEach(step => {
        if (step.agent === "Researcher") {
          setAgentDone("Researcher", `${job.research_notes.length} Grounded Notes`);
          appendLog("text-success", `[RESEARCHER DONE] Synthesized ${job.research_notes.length} grounded notes with source citations.`);
          setAgentActive("Writer", `Drafting v${job.draft_version}...`);
          updatePipelineStatus("Step 2/3: Writer agent composing technical draft report...");
        } else if (step.agent === "Writer") {
          setAgentDone("Writer", `Draft v${job.draft_version}`);
          appendLog("text-success", `[WRITER DONE] Draft v${job.draft_version} generated with inline citations.`);
          setAgentActive("Editor", "Auditing Factual Claims & Citations...");
          updatePipelineStatus("Step 3/3: Editor auditing grounding and clarity...");
        } else if (step.agent === "Editor" && job.status !== "done") {
          setAgentActive("Writer", `Revision pass ${job.revision_count}/2...`);
          updatePipelineStatus(`Editor requested revision ${job.revision_count}/2 — writer revising...`);
        }
      });
    }

    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "Pipeline execution failed.");

    await sleep(POLL_INTERVAL_MS);
  }
}

function renderDetailedSteps(steps) {
  const container = document.getElementById("stepsTimelineContainer");
  if (!steps || steps.length === 0) {
    container.innerHTML = `<div class="placeholder-box"><p>No detailed steps captured.</p></div>`;
    return;
  }

  let html = "";
  steps.forEach((s, i) => {
    const tagClass = `tag-${s.agent.toLowerCase()}`;
    html += `
      <div class="step-card">
        <div class="step-header">
          <div class="step-header-left">
            <span class="step-agent-tag ${tagClass}">${s.agent}</span>
            <span class="step-title">${s.title}</span>
          </div>
          <span class="step-time">[Step ${i+1}] ${s.timestamp}</span>
        </div>
        <div class="step-body">
          <p class="step-summary">${s.summary}</p>
    `;

    // Agent 1: Researcher details
    if (s.agent === "Researcher" && s.sub_questions) {
      html += `
        <div class="sub-questions-list">
          <h5>Decomposed Sub-Questions (${s.sub_questions.length})</h5>
      `;
      s.sub_questions.forEach(sq => {
        html += `<div class="sub-q-item">❓ ${sq}</div>`;
      });
      html += `</div>`;
    }

    // Agent 2: Writer details
    if (s.agent === "Writer") {
      if (s.editor_feedback_addressed) {
        html += `
          <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.84rem; color: #fef08a;">
            <strong>📌 Feedback Addressed in Surgical Revision:</strong> ${s.editor_feedback_addressed}
          </div>
        `;
      }
      html += `
        <div style="background: rgba(0,0,0,0.4); font-family: var(--font-mono); font-size: 0.8rem; padding: 10px 14px; border-radius: 8px; color: #d1d5db;">
          ${escapeHtml(s.draft_snippet)}
        </div>
      `;
    }

    // Agent 3: Editor details
    if (s.agent === "Editor" && s.audit_checks) {
      html += `
        <div class="audit-grid">
      `;
      s.audit_checks.forEach(c => {
        const isPassed = c.status.includes("Passed") || c.status.includes("Verified");
        const statusClass = isPassed ? "check-status-passed" : "check-status-flagged";
        html += `
          <div class="audit-check-card">
            <span>${c.check}</span>
            <span class="${statusClass}">${c.status}</span>
          </div>
        `;
      });
      html += `</div>`;
    }

    html += `
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}


function resetAgentCards() {
  ["Researcher", "Writer", "Editor"].forEach(agent => {
    const card = document.getElementById(`agentCard${agent}`);
    const badge = document.getElementById(`badge${agent}`);
    card.classList.remove("active");
    badge.className = "agent-badge";
    badge.innerText = "Idle";
  });
}

function setAgentActive(agent, text) {
  resetAgentCards();
  const card = document.getElementById(`agentCard${agent}`);
  const badge = document.getElementById(`badge${agent}`);
  card.classList.add("active");
  badge.classList.add("active");
  badge.innerText = text;
}

function setAgentDone(agent, metricText) {
  const card = document.getElementById(`agentCard${agent}`);
  const badge = document.getElementById(`badge${agent}`);
  const metric = document.getElementById(`metric${agent}`);
  card.classList.remove("active");
  badge.className = "agent-badge active";
  badge.innerText = "Completed";
  if (metricText) metric.innerText = metricText;
}

function updatePipelineStatus(msg) {
  document.getElementById("pipelineStatusText").innerText = msg;
}

function appendLog(className, message) {
  const container = document.getElementById("logContainer");
  const time = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.className = `log-line ${className}`;
  line.innerText = `[${time}] ${message}`;
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
}

function renderReport(markdownText) {
  const container = document.getElementById("reportContainer");
  if (window.marked) {
    container.innerHTML = marked.parse(markdownText);
  } else {
    container.innerText = markdownText;
  }
}

function renderNotes(notes) {
  const container = document.getElementById("notesContainer");
  if (!notes || notes.length === 0) {
    container.innerHTML = `<p class="placeholder-text">No notes found.</p>`;
    return;
  }

  let html = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px;">`;
  notes.forEach((note, i) => {
    html += `
      <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-size: 0.75rem; font-weight: 600; color: var(--accent-emerald);">Note #${i+1}</span>
          <span style="font-size: 0.75rem; color: var(--text-muted);">${note.source}</span>
        </div>
        <h5 style="font-size: 0.9rem; margin-bottom: 6px; color: #fff;">${note.sub_question}</h5>
        <p style="font-size: 0.82rem; color: #d1d5db; line-height: 1.4; margin-bottom: 8px;">${note.finding}</p>
        <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${note.url}</div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function renderLogs(steps) {
  steps.forEach(s => {
    appendLog("text-info", `[NODE ${s.node.toUpperCase()}] Status: ${s.status} | Feedback: ${s.editor_feedback || 'None'}`);
  });
}

async function submitIngest() {
  const title = document.getElementById("ingestTitle").value.trim();
  const url = document.getElementById("ingestUrl").value.trim();
  const content = document.getElementById("ingestContent").value.trim();

  if (!title || !content) {
    alert("Title and document content are required.");
    return;
  }

  try {
    const res = await fetch("/api/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, url, content })
    });

    const data = await res.json();
    if (data.success) {
      alert(`Success! Ingested ${data.chunks_added} vector chunks for source ${data.source_id}. Total vector DB count: ${data.total_vector_count}`);
      document.getElementById("ingestTitle").value = "";
      document.getElementById("ingestUrl").value = "";
      document.getElementById("ingestContent").value = "";
      toggleIngestDrawer();
      fetchStatus();
    } else {
      alert("Failed to ingest document.");
    }
  } catch (err) {
    alert("Ingest error: " + err.message);
  }
}

function copyReport() {
  if (!currentReportMarkdown) {
    alert("No report available to copy.");
    return;
  }
  navigator.clipboard.writeText(currentReportMarkdown);
  alert("Markdown report copied to clipboard!");
}

function downloadReport() {
  if (!currentReportMarkdown) {
    alert("No report available to download.");
    return;
  }
  const blob = new Blob([currentReportMarkdown], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `research_report_${Date.now()}.md`;
  a.click();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
