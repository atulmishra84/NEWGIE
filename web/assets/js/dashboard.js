(() => {
  const HISTORY_KEY = "gie.dashboard.history.v1";
  const API_KEY = "gie.dashboard.apiBase";

  const $ = (id) => document.getElementById(id);

  const apiBaseInput = $("apiBase");
  const toastEl = $("toast");
  const resultBox = $("resultBox");
  const resultMeta = $("resultMeta");
  const stepsEl = $("stepsStrip");
  const plainReport = $("plainReport");
  const reportPanel = $("reportPanel");
  const rawJsonWrap = $("rawJsonWrap");
  const statusGrid = $("statusGrid");
  const historyBody = $("historyBody");
  const docsLink = $("docsLink");
  const apiHint = $("apiHint");
  const analyzePanel = $("analyze");

  function isLocalHost(hostname) {
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
  }

  function defaultApiBase() {
    const params = new URLSearchParams(location.search);
    const fromQuery = params.get("api");
    if (fromQuery) return fromQuery.replace(/\/$/, "");
    if (typeof window.GIE_API_BASE === "string" && window.GIE_API_BASE) {
      return window.GIE_API_BASE.replace(/\/$/, "");
    }
    if (isLocalHost(location.hostname)) return "http://127.0.0.1:8091";
    return "/api";
  }

  function resolveInitialApiBase() {
    const saved = localStorage.getItem(API_KEY);
    if (!saved) return defaultApiBase();
    if (!isLocalHost(location.hostname) && /127\.0\.0\.1|localhost/.test(saved)) {
      localStorage.removeItem(API_KEY);
      return defaultApiBase();
    }
    return saved.replace(/\/$/, "");
  }

  apiBaseInput.value = resolveInitialApiBase();
  if (apiHint) {
    apiHint.textContent = isLocalHost(location.hostname)
      ? "Local default: Orchestrator on :8091"
      : "Using same-origin /api proxy to Orchestrator";
  }

  function base() {
    return apiBaseInput.value.replace(/\/$/, "");
  }

  function syncDocsLink() {
    docsLink.href = `${base()}/docs`;
  }

  function toast(msg, isError = false) {
    toastEl.textContent = msg;
    toastEl.classList.toggle("error", isError);
    toastEl.classList.add("show");
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(() => toastEl.classList.remove("show"), 4200);
  }

  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveHistory(rows) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(rows.slice(0, 25)));
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function unwrap(body) {
    if (body && typeof body === "object" && "data" in body) return body.data;
    return body;
  }

  function executionIdOf(data) {
    if (!data || typeof data !== "object") return null;
    return data.execution_id || data.executionId || data.id || null;
  }

  function resultOf(data, key) {
    return data?.result?.[key] || data?.steps?.find((s) => s.step_id === key)?.output || null;
  }

  /** Normalize risk score to 0–100 (accepts 0–1 fractions from live peers). */
  function score100(score) {
    if (score == null || score === "") return null;
    const n = Number(score);
    if (!Number.isFinite(n)) return null;
    if (n >= 0 && n <= 1) return Math.round(n * 100);
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function riskTone(score) {
    const s = score100(score);
    if (s == null) return "neutral";
    if (s >= 70) return "high";
    if (s >= 40) return "medium";
    return "low";
  }

  function decisionFrom(data, risk, policy) {
    const fails = (policy?.violations || []).filter((v) => String(v.status).toLowerCase() === "fail");
    const score = score100(risk?.score);
    if ((score != null && score >= 70) || fails.length) {
      return {
        key: "hold",
        title: "Hold for remediation",
        blurb: "Do not treat this as cleared for production until top risks and failed policy checks are addressed.",
      };
    }
    if ((score != null && score >= 40) || (policy?.violations || []).some((v) => String(v.status).toLowerCase() === "warn")) {
      return {
        key: "conditional",
        title: "Ship with conditions",
        blurb: "Proceed only if the priority actions and drafted guardrails below are scheduled before or with release.",
      };
    }
    return {
      key: "clear",
      title: "Cleared to proceed",
      blurb: "No elevated blockers were found in this run. Keep the audit ID with your release evidence.",
    };
  }

  function sevClass(sev) {
    const s = String(sev || "").toLowerCase();
    if (s === "high" || s === "fail" || s === "gap") return "sev-high";
    if (s === "medium" || s === "warn" || s === "partial" || s === "warning") return "sev-med";
    if (s === "low" || s === "pass" || s === "ok") return "sev-low";
    return "sev-neutral";
  }

  function meterSvg(score) {
    const s = score100(score) ?? 0;
    const r = 54;
    const c = 2 * Math.PI * r;
    const offset = c - (s / 100) * c;
    const tone = riskTone(s);
    return `<div class="score-meter tone-${tone}" aria-label="Risk score ${s} of 100">
      <svg viewBox="0 0 140 140" width="120" height="120" role="img">
        <circle class="track" cx="70" cy="70" r="${r}" />
        <circle class="fill" cx="70" cy="70" r="${r}"
          stroke-dasharray="${c.toFixed(2)}"
          stroke-dashoffset="${offset.toFixed(2)}" />
      </svg>
      <div class="score-center">
        <strong>${escapeHtml(String(s))}</strong>
        <span>/100</span>
      </div>
    </div>`;
  }

  function rowsTable(headers, rowsHtml) {
    if (!rowsHtml) return "";
    return `<div class="brief-table-wrap"><table class="brief-table">
      <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
      <tbody>${rowsHtml}</tbody>
    </table></div>`;
  }

  function renderPlainReport(data) {
    if (!plainReport) return;
    if (!data || typeof data !== "object" || data.error) {
      clearPlainReport();
      return;
    }

    const ctx = resultOf(data, "context");
    const risk = resultOf(data, "risk");
    const policy = resultOf(data, "policy");
    const compliance = resultOf(data, "compliance");
    const knowledge = resultOf(data, "knowledge");
    const recommendation = resultOf(data, "recommendation");
    const generator = resultOf(data, "generator");
    const validation = resultOf(data, "validation");
    const explain = resultOf(data, "explainability");
    const executionId = executionIdOf(data);
    const conf = data.confidence?.score;
    const riskScore = score100(risk?.score);
    const tone = riskTone(riskScore);
    const decision = decisionFrom(data, risk, policy);
    const when = data.finished_at || data.created_at || new Date().toISOString();
    const sourcePath = ctx?.source_path || data.metadata?.path || "—";
    const tenant = data.tenant_id || "—";
    const liveSteps = (data.steps || []).filter((s) => s?.output?.live === true).length;
    const liveMode = liveSteps > 0 || risk?.live === true;

    const assetRows = (ctx?.assets || [])
      .map(
        (a) => `<tr>
        <td>${escapeHtml(a.name || a.id || "—")}</td>
        <td>${escapeHtml(a.type || "—")}</td>
        <td>${escapeHtml(a.provider || a.runtime || "—")}</td>
      </tr>`
      )
      .join("");

    const flowRows = (ctx?.data_flows || [])
      .map(
        (f) => `<tr>
        <td>${escapeHtml(f.from || "—")}</td>
        <td class="flow-arrow">→</td>
        <td>${escapeHtml(f.to || "—")}</td>
        <td>${escapeHtml(f.data || "—")}</td>
      </tr>`
      )
      .join("");

    const findingRows = (risk?.findings || [])
      .map(
        (f) => `<tr>
        <td><span class="sev ${sevClass(f.severity)}">${escapeHtml(f.severity || "n/a")}</span></td>
        <td>${escapeHtml(f.title || "—")}</td>
        <td>${f.likelihood != null ? escapeHtml(String(Math.round(f.likelihood * 100)) + "%") : "—"}</td>
      </tr>`
      )
      .join("");

    const policyRows = (policy?.violations || [])
      .map(
        (v) => `<tr>
        <td><span class="sev ${sevClass(v.status)}">${escapeHtml(v.status || "—")}</span></td>
        <td class="mono">${escapeHtml(v.policy || "—")}</td>
      </tr>`
      )
      .join("");

    const gapRows = (compliance?.gaps || [])
      .map(
        (g) => `<tr>
        <td><span class="sev ${sevClass(g.status)}">${escapeHtml(g.status || "—")}</span></td>
        <td class="mono">${escapeHtml(g.control || "—")}</td>
        <td>${escapeHtml(g.note || "—")}</td>
      </tr>`
      )
      .join("");

    const actionRows = (recommendation?.actions || [])
      .map(
        (a, idx) => `<tr>
        <td><span class="prio">P${escapeHtml(String(a.priority ?? idx + 1))}</span></td>
        <td>${escapeHtml(a.title || "—")}</td>
      </tr>`
      )
      .join("");

    const guardrailItems = generator?.artifacts?.items || generator?.artifacts || [];
    const guardrailRows = (Array.isArray(guardrailItems) ? guardrailItems : [])
      .map((g) => {
        if (typeof g === "string") {
          return `<tr><td>artifact</td><td class="mono">${escapeHtml(g)}</td></tr>`;
        }
        return `<tr>
          <td>${escapeHtml(g.type || "artifact")}</td>
          <td class="mono">${escapeHtml(g.name || g.id || "—")}</td>
        </tr>`;
      })
      .join("");

    const validationRows = (validation?.results || [])
      .map(
        (r) => `<tr>
        <td><span class="sev ${sevClass(r.status)}">${escapeHtml(r.status || "—")}</span></td>
        <td class="mono">${escapeHtml(r.artifact || "—")}</td>
        <td>${escapeHtml(r.note || "—")}</td>
      </tr>`
      )
      .join("");

    const driverBars = (explain?.drivers || [])
      .map((d) => {
        const pct = Math.round((d.weight || 0) * 100);
        return `<div class="driver">
          <div class="driver-top">
            <span>${escapeHtml(String(d.factor || "").replace(/_/g, " "))}</span>
            <strong>${pct}%</strong>
          </div>
          <div class="driver-track"><i style="width:${pct}%"></i></div>
        </div>`;
      })
      .join("");

    const frameworks = (knowledge?.frameworks || [])
      .map((f) => `<span class="chip">${escapeHtml(f)}</span>`)
      .join("");

    plainReport.hidden = false;
    if (reportPanel) reportPanel.hidden = false;
    plainReport.innerHTML = `
      <div class="brief" data-tone="${tone}">
        <header class="brief-masthead">
          <div>
            <p class="brief-brand">GIE · Governance brief</p>
            <h2>${escapeHtml(decision.title)}</h2>
            <p class="brief-lede">${escapeHtml(decision.blurb)}</p>
          </div>
          <div class="brief-actions no-print">
            <button type="button" class="btn btn-light" id="btnCopyBrief">Copy summary</button>
            <button type="button" class="btn btn-ghost" id="btnPrintBrief">Print / PDF</button>
          </div>
        </header>

        <div class="brief-decision decision-${decision.key}">
          <div class="decision-copy">
            <span class="decision-label">Release posture</span>
            <strong>${escapeHtml(decision.title)}</strong>
            <p>${escapeHtml(
              explain?.narrative ||
                explain?.summary ||
                risk?.summary ||
                "Analysis completed for this AI system."
            )}</p>
          </div>
          ${riskScore != null ? meterSvg(riskScore) : ""}
        </div>

        <div class="brief-meta">
          <div><span>Tenant</span><strong>${escapeHtml(tenant)}</strong></div>
          <div><span>Source</span><strong class="mono">${escapeHtml(sourcePath)}</strong></div>
          <div><span>Mode</span><strong>${liveMode ? `Live peers (${liveSteps || "—"} steps)` : "Demo / simulated"}</strong></div>
          <div><span>Confidence</span><strong>${conf != null ? escapeHtml(String(conf)) : "—"}</strong></div>
          <div><span>Completed</span><strong>${escapeHtml(String(when).replace("T", " ").replace(/Z$/, " UTC"))}</strong></div>
          <div class="meta-wide"><span>Audit ID</span>
            <strong class="mono" id="auditIdText">${escapeHtml(executionId || "—")}</strong>
            <button type="button" class="linkish no-print" id="btnCopyAudit">Copy</button>
          </div>
        </div>

        <section class="brief-section" style="--i:1">
          <div class="section-head">
            <span class="num">01</span>
            <div>
              <h3>System inventory</h3>
              <p>What is actually in this AI system?</p>
            </div>
          </div>
          <p class="section-body">${escapeHtml(ctx?.summary || "No inventory details were returned.")}</p>
          ${rowsTable(["Component", "Type", "Runtime / provider"], assetRows)}
          ${
            flowRows
              ? `<p class="subhead">Data movement</p>${rowsTable(["From", "", "To", "Data"], flowRows)}`
              : ""
          }
        </section>

        <section class="brief-section" style="--i:2">
          <div class="section-head">
            <span class="num">02</span>
            <div>
              <h3>Risk posture</h3>
              <p>What could go wrong, and how severe is it?</p>
            </div>
          </div>
          <p class="section-body">${escapeHtml(risk?.summary || "No risk summary was returned.")}</p>
          ${rowsTable(["Severity", "Finding", "Likelihood"], findingRows)}
          ${driverBars ? `<p class="subhead">Score drivers</p><div class="drivers">${driverBars}</div>` : ""}
        </section>

        <section class="brief-section" style="--i:3">
          <div class="section-head">
            <span class="num">03</span>
            <div>
              <h3>Policy &amp; regulatory alignment</h3>
              <p>Are we aligned with the rules we claim to follow?</p>
            </div>
          </div>
          <p class="section-body">${escapeHtml(policy?.summary || "No policy summary was returned.")}</p>
          ${frameworks ? `<div class="chip-row">${frameworks}</div>` : ""}
          ${rowsTable(["Status", "Policy"], policyRows)}
          <p class="section-body">${escapeHtml(compliance?.summary || "")}</p>
          ${rowsTable(["Status", "Control", "Note"], gapRows)}
        </section>

        <section class="brief-section" style="--i:4">
          <div class="section-head">
            <span class="num">04</span>
            <div>
              <h3>Evidence of review</h3>
              <p>Can we prove this was checked before shipping?</p>
            </div>
          </div>
          <p class="section-body">Yes. Keep this brief and audit ID with the release package as evidence that governance ran.</p>
          <ul class="evidence-list">
            <li>Pipeline steps completed: <strong>${escapeHtml(String(data.steps?.length || 0))}</strong></li>
            <li>Validation outcome: ${escapeHtml(validation?.summary || "not available")}</li>
            <li>Run status: <strong>${escapeHtml(data.status || "—")}</strong></li>
          </ul>
          ${rowsTable(["Result", "Artifact", "Note"], validationRows)}
        </section>

        <section class="brief-section accent" style="--i:5">
          <div class="section-head">
            <span class="num">05</span>
            <div>
              <h3>Recommended guardrails</h3>
              <p>What should we apply next?</p>
            </div>
          </div>
          <p class="section-body">${escapeHtml(recommendation?.summary || "No recommendations were returned.")}</p>
          <p class="subhead">Priority actions</p>
          ${rowsTable(["Priority", "Action"], actionRows) || "<p class='muted'>No prioritized actions.</p>"}
          <p class="subhead">Draft policies &amp; monitors</p>
          ${
            rowsTable(["Type", "Artifact"], guardrailRows) ||
            `<p class="muted">${escapeHtml(generator?.summary || "No drafted guardrails in this run.")}</p>`
          }
        </section>

        <footer class="brief-footer">
          Generated by Guardrails Intelligence Engine · Not a legal opinion · Retain audit ID with release evidence
        </footer>
      </div>
    `;

    const summaryText = [
      `GIE Governance Brief — ${decision.title}`,
      `Tenant: ${tenant}`,
      `Source: ${sourcePath}`,
      `Risk: ${riskScore != null ? riskScore + "/100" : "n/a"}`,
      `Mode: ${liveMode ? "live peers" : "demo/simulated"}`,
      `Confidence: ${conf ?? "n/a"}`,
      `Audit ID: ${executionId || "n/a"}`,
      "",
      explain?.narrative || risk?.summary || "",
      "",
      "Priority actions:",
      ...(recommendation?.actions || []).map((a) => `- P${a.priority ?? "?"}: ${a.title}`),
      "",
      "Guardrails:",
      ...(Array.isArray(guardrailItems) ? guardrailItems : []).map((g) =>
        typeof g === "string" ? `- ${g}` : `- ${g.type || "artifact"}: ${g.name || g.id}`
      ),
    ].join("\n");

    plainReport._summaryText = summaryText;

    $("btnCopyBrief")?.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(plainReport._summaryText || "");
        toast("Brief summary copied");
      } catch {
        toast("Could not copy summary", true);
      }
    });
    $("btnPrintBrief")?.addEventListener("click", () => window.print());
    $("btnCopyAudit")?.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(String(executionId || ""));
        toast("Audit ID copied");
      } catch {
        toast("Could not copy audit ID", true);
      }
    });

    reportPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearPlainReport() {
    if (!plainReport) return;
    plainReport.hidden = true;
    plainReport.innerHTML = "";
    if (reportPanel) reportPanel.hidden = true;
  }

  function renderHistory() {
    const rows = loadHistory();
    if (!rows.length) {
      historyBody.innerHTML = `<tr><td colspan="6">No runs yet.</td></tr>`;
      return;
    }
    historyBody.innerHTML = rows
      .map((r) => {
        const id = r.executionId || "—";
        return `<tr>
          <td>${escapeHtml(r.when)}</td>
          <td>${escapeHtml(r.tenant)}</td>
          <td class="mono">${escapeHtml(r.source)}</td>
          <td><span class="badge badge-teal">${escapeHtml(r.mode)}</span></td>
          <td class="mono">${escapeHtml(id)}</td>
          <td>${
            id !== "—"
              ? `<button type="button" class="btn btn-ghost" data-exec="${escapeAttr(
                  id
                )}" style="min-height:2rem;padding:0.3rem 0.6rem;font-size:0.8rem">Open brief</button>`
              : ""
          }</td>
        </tr>`;
      })
      .join("");
  }

  function renderSteps(data) {
    if (!stepsEl) return;
    const steps = Array.isArray(data?.steps) ? data.steps : [];
    if (!steps.length) {
      stepsEl.hidden = true;
      stepsEl.innerHTML = "";
      return;
    }
    stepsEl.hidden = false;
    stepsEl.innerHTML = steps
      .map((s) => {
        const ok = s.status === "succeeded" || s.status === "cached";
        const cls = ok ? "ok" : s.status === "failed" ? "fail" : "";
        return `<div class="step-chip ${cls}">
          <strong>${escapeHtml(s.step_id || s.agent_id || "step")}</strong>
          <span>${escapeHtml(s.status || "")}${s.duration_ms != null ? ` · ${s.duration_ms}ms` : ""}</span>
        </div>`;
      })
      .join("");
  }

  function showResult(data, metaBadges = [], { isError = false } = {}) {
    resultMeta.hidden = false;
    resultMeta.innerHTML = metaBadges
      .map((b) => `<span class="badge ${b.cls || ""}">${escapeHtml(b.text)}</span>`)
      .join("");
    if (rawJsonWrap) rawJsonWrap.hidden = false;
    resultBox.hidden = false;
    resultBox.textContent =
      typeof data === "string" ? data : JSON.stringify(data, null, 2);
    if (isError) clearPlainReport();
  }

  async function fetchJson(path, options = {}) {
    const url = `${base()}${path}`;
    const headers = {
      Accept: "application/json",
      "x-tenant-id": options.tenantId || "default",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    };
    let res;
    try {
      res = await fetch(url, { ...options, headers });
    } catch {
      const hint =
        /127\.0\.0\.1|localhost/.test(base()) && !isLocalHost(location.hostname)
          ? " API base still points at localhost — set it to /api and Ping again."
          : " Check API base and that Orchestrator is reachable.";
      const err = new Error(`Network error:${hint}`);
      err.status = 0;
      throw err;
    }
    const text = await res.text();
    let body;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }
    if (!res.ok) {
      const detail =
        typeof body === "object" && body?.detail
          ? typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail)
          : typeof body === "object" && body?.error?.message
            ? body.error.message
            : `HTTP ${res.status}`;
      const err = new Error(detail);
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return body;
  }

  function renderStatus(items) {
    statusGrid.innerHTML = items
      .map(
        (i) => `<div class="status-item">
        <div class="label">${escapeHtml(i.label)}</div>
        <div class="value ${i.down ? "down" : ""}">${escapeHtml(i.value)}</div>
      </div>`
      )
      .join("");
  }

  async function refreshStatus() {
    const items = [];
    try {
      const root = await fetchJson("/");
      items.push({ label: "Orchestrator", value: root?.agent || root?.service || "up" });
      if (root?.version) items.push({ label: "Version", value: String(root.version) });
      if (root?.schema) items.push({ label: "Schema", value: String(root.schema) });
    } catch (e) {
      items.push({ label: "Orchestrator", value: "unreachable", down: true });
      toast(`Status failed: ${e.message}`, true);
      renderStatus(items);
      return;
    }

    try {
      const st = unwrap(await fetchJson("/status"));
      if (st && typeof st === "object") {
        items.push({
          label: "Healthy",
          value: String(st.healthy ?? "—"),
          down: st.healthy === false,
        });
        items.push({ label: "Active", value: String(st.active_executions ?? 0) });
        if (Array.isArray(st.agents)) {
          for (const agent of st.agents) {
            const down = agent.healthy === false;
            items.push({
              label: agent.agent_id || "agent",
              value: down ? "down" : "ok",
              down,
            });
          }
        }
      }
    } catch (e) {
      items.push({ label: "/status", value: e.message || "error", down: true });
      toast(`Agent status failed: ${e.message}`, true);
    }

    renderStatus(items.length ? items : [{ label: "Status", value: "ok" }]);
    toast("Status refreshed");
  }

  function applyDemoSample() {
    const demo = window.GIE_DEMO || { tenant: "acme", path: "/demo/acme-ai-assistant" };
    const form = $("analyzeForm");
    form.tenant_id.value = demo.tenant || "acme";
    form.source_path.value = demo.path || "/demo/acme-ai-assistant";
    form.source_type.value = "folder";
    form.mode.value = "sync";
    form.cache.checked = false;
    form.require_human_approval.checked = false;
    form.options.value = `{
  "parallel": true,
  "audience": "engineering",
  "demo": true
}`;
  }

  function presentAnalysis(envelope, extraBadges = []) {
    const data = unwrap(envelope);
    const executionId = executionIdOf(data);
    const status = data?.status || "ok";
    renderSteps(data);
    renderPlainReport(data);
    showResult(envelope, [
      ...extraBadges,
      { text: String(status), cls: status === "failed" ? "badge-danger" : "badge-ok" },
      ...(data?.confidence?.score != null
        ? [{ text: `conf ${data.confidence.score}`, cls: "badge" }]
        : []),
      ...(executionId ? [{ text: `exec ${executionId}`, cls: "badge" }] : []),
    ]);
    analyzePanel?.classList.add("has-brief");
  }

  $("btnPing").addEventListener("click", () => {
    localStorage.setItem(API_KEY, base());
    syncDocsLink();
    refreshStatus();
  });

  apiBaseInput.addEventListener("change", () => {
    localStorage.setItem(API_KEY, base());
    syncDocsLink();
  });

  $("btnRefreshStatus").addEventListener("click", refreshStatus);

  $("btnSample").addEventListener("click", () => {
    applyDemoSample();
    toast("Loaded ACME AI Assistant demo");
  });

  $("analyzeForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const form = ev.target;
    let options;
    try {
      options = JSON.parse(form.options.value);
    } catch {
      toast("Options must be valid JSON", true);
      return;
    }

    const payload = {
      tenant_id: form.tenant_id.value.trim(),
      source: {
        type: form.source_type.value,
        path: form.source_path.value.trim(),
      },
      mode: form.mode.value,
      cache: form.cache.checked,
      require_human_approval: form.require_human_approval.checked,
      options,
      metadata: { demo: Boolean(options.demo) },
    };

    try {
      const envelope = await fetchJson("/analyze", {
        method: "POST",
        body: JSON.stringify(payload),
        tenantId: payload.tenant_id,
      });
      const data = unwrap(envelope);
      presentAnalysis(envelope, [{ text: payload.mode, cls: "badge-teal" }]);
      const rows = loadHistory();
      rows.unshift({
        when: new Date().toLocaleString(),
        tenant: payload.tenant_id,
        source: payload.source.path,
        mode: payload.mode,
        executionId: executionIdOf(data),
      });
      saveHistory(rows);
      renderHistory();
      toast("Governance brief ready");
    } catch (e) {
      if (stepsEl) {
        stepsEl.hidden = true;
        stepsEl.innerHTML = "";
      }
      clearPlainReport();
      showResult(
        e.body || e.message,
        [
          { text: "error", cls: "badge-danger" },
          { text: String(e.status || "fail"), cls: "badge" },
        ],
        { isError: true }
      );
      toast(`Analyze failed: ${e.message}`, true);
    }
  });

  historyBody.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-exec]");
    if (!btn) return;
    const id = btn.getAttribute("data-exec");
    try {
      const envelope = await fetchJson(`/execution/${encodeURIComponent(id)}`);
      presentAnalysis(envelope, [{ text: "execution", cls: "badge-teal" }]);
      toast("Opened governance brief");
    } catch (e) {
      toast(`Fetch failed: ${e.message}`, true);
    }
  });

  $("btnClearHistory").addEventListener("click", () => {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
    toast("History cleared");
  });

  applyDemoSample();
  syncDocsLink();
  renderHistory();
  refreshStatus().catch(() => {});
})();
