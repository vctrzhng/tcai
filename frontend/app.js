/* ============================================================
   TCAI frontend — plain JS, no build step.
   Talks to the FastAPI backend. Same origin when served by
   FastAPI; override API_BASE if you open the file directly.
   ============================================================ */
const API_BASE = (location.protocol === "file:") ? "http://127.0.0.1:8000" : "";

// Fields shown in the compare table; direction tells which way is buyer-favorable
const COMPARE_LABELS = {
  vendor_name: "Vendor", pricing_model: "Pricing", payment_terms_days: "Payment (days)",
  discount_pct: "Discount %", minimum_spend: "Min spend", minimum_spend_period: "Period",
  term_length_months: "Term (mo)", auto_renewal: "Auto-renew",
  termination_for_convenience: "Term. convenience", liability_cap: "Liability cap",
  governing_law: "Gov. law",
};

/* ---------- helpers ---------- */
function $(id) { return document.getElementById(id); }

async function api(path, opts) {
  const r = await fetch(API_BASE + path, opts);
  if (!r.ok) {
    let msg = r.status + " " + r.statusText;
    try { const j = await r.json(); if (j.detail) msg = j.detail; } catch (_) {}
    throw new Error(msg);
  }
  return r.json();
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("show"), 3200);
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") return v.toLocaleString();
  return String(v);
}
function cell(v) {
  const f = fmt(v);
  return f === null ? '<span class="cell-null">—</span>' : escapeHtml(f);
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- tab routing ---------- */
function go(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  $("view-" + view).classList.add("active");
  document.querySelector(`.tab[data-view="${view}"]`)?.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (view === "library") loadLibrary();
}

/* ============================================================
   UPLOAD
   ============================================================ */
const drop = $("drop"), fileInput = $("file-input");
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("dragover"); });
drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
drop.addEventListener("drop", e => {
  e.preventDefault(); drop.classList.remove("dragover");
  if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles(fileInput.files);
});

async function uploadFiles(files) {
  const names = [...files].map(f => f.name).join(", ");
  $("upload-status").innerHTML =
    `<p class="muted-note"><span class="spinner"></span>Extracting ${files.length} contract(s): ${escapeHtml(names)}… this can take a few seconds each.</p>`;
  $("upload-results").innerHTML = "";

  const fd = new FormData();
  [...files].forEach(f => fd.append("files", f));

  try {
    const data = await api("/contracts/upload", { method: "POST", body: fd });
    $("upload-status").innerHTML = "";
    renderUploadResults(data.uploaded);
    const ok = data.uploaded.filter(u => !u.error).length;
    toast(`${ok} contract(s) added to your library.`);
  } catch (err) {
    $("upload-status").innerHTML =
      `<div class="warnings">Upload failed: ${escapeHtml(err.message)}. Is the backend running?</div>`;
  }
  fileInput.value = "";
}

function renderUploadResults(rows) {
  const el = $("upload-results");
  el.innerHTML = rows.map(u => {
    if (u.error) {
      return `<div class="card"><div class="card-head">
        <h3 class="card-title">${escapeHtml(u.filename)}</h3>
        <span class="pill pill-risk">failed</span></div>
        <p class="muted-note">${escapeHtml(u.error)}</p></div>`;
    }
    const pill = u.needs_review
      ? '<span class="pill pill-warn">needs review</span>'
      : '<span class="pill pill-ok">clean</span>';
    const flagged = new Set(
      (u.review_reasons || []).map(r => r.split(":")[0]));
    const fields = Object.entries(u.fields).map(([k, v]) => {
      const isFlag = flagged.has(k);
      return `<div class="field ${isFlag ? "flagged" : ""}">
        <span class="field-label">${escapeHtml(COMPARE_LABELS[k] || k)}</span>
        <span class="field-val">${cell(v)}</span></div>`;
    }).join("");
    const reasons = (u.review_reasons && u.review_reasons.length)
      ? `<p class="muted-note">Flagged: ${u.review_reasons.map(escapeHtml).join("; ")}</p>` : "";
    return `<div class="card">
      <div class="card-head"><h3 class="card-title">${escapeHtml(u.filename)}</h3>${pill}</div>
      <div class="fields-grid">${fields}</div>${reasons}</div>`;
  }).join("");
}

/* ============================================================
   LIBRARY
   ============================================================ */
async function loadLibrary() {
  const body = $("library-body");
  body.innerHTML = `<p class="muted-note"><span class="spinner"></span>Loading…</p>`;
  try {
    const { contracts } = await api("/contracts");
    $("library-count").textContent = `${contracts.length} contract(s)`;
    if (!contracts.length) {
      body.innerHTML = emptyState("No contracts yet",
        "Head to Upload to add your first contracts.");
      return;
    }
    const cols = ["vendor_name", "pricing_model", "payment_terms_days",
      "discount_pct", "minimum_spend", "term_length_months", "liability_cap"];
    const head = `<tr><th>Status</th>${cols.map(c =>
      `<th>${escapeHtml(COMPARE_LABELS[c] || c)}</th>`).join("")}<th></th></tr>`;
    const rows = contracts.map(c => {
      const pill = c.needs_review
        ? '<span class="pill pill-warn">review</span>'
        : '<span class="pill pill-ok">clean</span>';
      const tds = cols.map(col =>
        `<td class="${col === "vendor_name" ? "vendor" : "num"}">${cell(c[col])}</td>`).join("");
      return `<tr><td>${pill}</td>${tds}
        <td><button class="btn" style="padding:4px 10px;font-size:12px"
            onclick="del('${c.contract_id}')">Remove</button></td></tr>`;
    }).join("");
    body.innerHTML = `<div class="table-scroll"><table class="data">
      <thead>${head}</thead><tbody>${rows}</tbody></table></div>`;
  } catch (err) {
    body.innerHTML = `<div class="warnings">${escapeHtml(err.message)}</div>`;
  }
}

async function del(id) {
  try { await api("/contracts/" + id, { method: "DELETE" }); toast("Contract removed."); loadLibrary(); }
  catch (err) { toast("Could not remove: " + err.message); }
}

/* ============================================================
   COMPARE
   ============================================================ */
async function loadCompare() {
  const body = $("compare-body");
  body.innerHTML = `<p class="muted-note"><span class="spinner"></span>Building…</p>`;
  try {
    const data = await api("/analysis/compare", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!data.rows.length) {
      body.innerHTML = emptyState("Nothing to compare yet",
        "Upload at least two contracts to see them side by side.");
      return;
    }
    const cols = data.columns;
    const hl = data.highlights || {};
    // build best/worst lookup: field -> {best:id, worst:id}
    const head = cols.map(c => `<th>${escapeHtml(COMPARE_LABELS[c] || c)}</th>`).join("");
    const rows = data.rows.map(r => {
      const tds = cols.map(col => {
        let cls = col === "vendor_name" ? "vendor" : "num";
        if (hl[col]) {
          if (hl[col].best === r.contract_id) cls += " cell-best";
          else if (hl[col].worst === r.contract_id) cls += " cell-worst";
        }
        return `<td class="${cls}">${cell(r[col])}</td>`;
      }).join("");
      return `<tr>${tds}</tr>`;
    }).join("");
    body.innerHTML = `<div class="table-scroll"><table class="data">
      <thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>
      <p class="muted-note">Terracotta = most buyer-favorable in that column; clay = least.</p>`;
  } catch (err) {
    body.innerHTML = `<div class="warnings">${escapeHtml(err.message)}</div>`;
  }
}

/* ============================================================
   INSIGHTS
   ============================================================ */
async function loadInsights() {
  const kind = $("insight-kind").value;
  const voice = $("insight-voice").value;
  const body = $("insights-body");
  body.innerHTML = `<p class="muted-note"><span class="spinner"></span>Reading the dataset and writing insights…</p>`;
  try {
    const data = await api("/analysis/insights", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, voice }),
    });
    if (data.note && (!data.insights || !data.insights.length)) {
      body.innerHTML = emptyState("Not enough data yet", data.note);
      return;
    }
    const insights = (data.insights || []).map((ins, i) =>
      `<div class="insight"><div class="insight-mark">${i + 1}</div>
        <p class="insight-text">${escapeHtml(ins.text)}</p></div>`).join("");
    const rec = data.recommendation
      ? `<div class="recommendation"><p class="eyebrow">Recommendation</p>
          <p>${escapeHtml(data.recommendation)}</p></div>` : "";
    const warn = (data.grounding_warnings && data.grounding_warnings.length)
      ? `<div class="warnings">Grounding check flagged ${data.grounding_warnings.length}
          figure(s) not found in the source table — treat with caution:
          ${data.grounding_warnings.map(escapeHtml).join(" / ")}</div>` : "";
    body.innerHTML = `<div class="card">
      <div class="card-head"><h3 class="card-title">${labelFor(kind)}</h3>
        <span class="card-meta">${voice === "neutral" ? "Neutral analyst" : "Buyer's advocate"}</span></div>
      ${insights}${rec}${warn}</div>`;
  } catch (err) {
    body.innerHTML = `<div class="warnings">${escapeHtml(err.message)}</div>`;
  }
}

function labelFor(kind) {
  return { best_pricing: "Best pricing", unfavorable: "Unfavorable terms",
    compare: "Cross-contract comparison", benchmark: "Dataset benchmark" }[kind] || kind;
}

/* ---------- shared ---------- */
function emptyState(title, msg) {
  return `<div class="empty"><p class="empty-title">${escapeHtml(title)}</p>
    <p>${escapeHtml(msg)}</p></div>`;
}
