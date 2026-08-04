(() => {
  const $ = (id) => document.getElementById(id);

  const els = {
    apiBase: $("apiBase"),
    btnConnect: $("btnConnect"),
    connBadge: $("connBadge"),
    commandInput: $("commandInput"),
    btnSend: $("btnSend"),
    btnStatus: $("btnStatus"),
    btnVoice: $("btnVoice"),
    btnClear: $("btnClear"),
    activity: $("activity"),
    fleetBox: $("fleetBox"),
    resultBox: $("resultBox"),
    jarvisEnabled: $("jarvisEnabled"),
    jarvisUrl: $("jarvisUrl"),
    jarvisToken: $("jarvisToken"),
    btnSaveJarvis: $("btnSaveJarvis"),
    btnTestJarvis: $("btnTestJarvis"),
    jarvisMsg: $("jarvisMsg"),
  };

  const state = {
    pollTimer: null,
    runId: null,
    jarvis: loadLocal("gie.jarvis", {}),
  };

  function loadLocal(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
    } catch {
      return fallback;
    }
  }

  function saveLocal(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function defaultApiBase() {
    const saved = localStorage.getItem("gie.apiBase");
    if (saved) return saved;
    if (window.location.protocol.startsWith("http") && window.location.port) {
      return window.location.origin;
    }
    return "http://127.0.0.1:8091";
  }

  function apiBase() {
    return (els.apiBase.value || defaultApiBase()).replace(/\/$/, "");
  }

  function setConnected(ok, text) {
    els.connBadge.textContent = text;
    els.connBadge.classList.toggle("on", !!ok);
    els.connBadge.classList.toggle("off", !ok);
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function addActivity(title, detail = "", kind = "info") {
    const li = document.createElement("li");
    li.dataset.kind = kind;
    if (kind === "err") li.style.borderLeftColor = "var(--bad)";
    if (kind === "ok") li.style.borderLeftColor = "var(--ok)";
    if (kind === "cmd") li.style.borderLeftColor = "var(--accent-2)";
    li.innerHTML = `
      <time>${new Date().toLocaleTimeString()}</time>
      <strong>${escapeHtml(title)}</strong>
      ${detail ? `<div>${escapeHtml(detail)}</div>` : ""}
    `;
    els.activity.prepend(li);
  }

  function showResult(obj) {
    els.resultBox.textContent =
      typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  }

  async function api(path, options = {}) {
    const res = await fetch(`${apiBase()}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
    const text = await res.text();
    let body;
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = { raw: text };
    }
    if (!res.ok) {
      const msg = body.detail || body.error || text || res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return body;
  }

  async function connect() {
    setConnected(false, "Connecting…");
    localStorage.setItem("gie.apiBase", apiBase());
    try {
      const health = await api("/healthz");
      setConnected(true, `Connected · ${health.agent || "ok"}`);
      addActivity("Connected", apiBase(), "ok");
      await refreshFleet();
      await refreshJarvis();
    } catch (err) {
      setConnected(false, "Disconnected");
      addActivity("Connect failed", err.message, "err");
      els.fleetBox.textContent = "Could not reach orchestrator.";
    }
  }

  async function refreshFleet() {
    try {
      const data = await api("/v1/fleet");
      const agents = data.agents || [];
      if (!agents.length) {
        els.fleetBox.textContent = "No agents reported.";
        return;
      }
      els.fleetBox.innerHTML = "";
      els.fleetBox.className = "fleet";
      for (const a of agents) {
        const card = document.createElement("div");
        const ok = a.healthy !== false;
        card.className = `agent-card ${ok ? "ok" : "bad"}`;
        card.innerHTML = `
          <strong>${escapeHtml(a.display_name || a.agent_id || "agent")}</strong>
          <span>${escapeHtml(a.lane || "")} · ${ok ? "healthy" : "down"}</span>
        `;
        els.fleetBox.appendChild(card);
      }
      addActivity(
        "Fleet refreshed",
        `${data.healthy ?? agents.length}/${data.fleet_size ?? agents.length} healthy`,
        "info"
      );
    } catch (err) {
      els.fleetBox.textContent = `Fleet unavailable: ${err.message}`;
    }
  }

  function stopPoll() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function extractRunId(body) {
    return (
      body?.run?.run_id ||
      body?.run_id ||
      body?.id ||
      body?.result?.run_id ||
      null
    );
  }

  async function pollRun(runId) {
    stopPoll();
    state.runId = runId;
    const seenKey = `gie.seen.${runId}`;
    const seen = new Set(loadLocal(seenKey, []));

    const tick = async () => {
      try {
        const [run, trace] = await Promise.all([
          api(`/v1/runs/${runId}`).catch(() => null),
          api(`/v1/runs/${runId}/trace`).catch(() => null),
        ]);

        if (run) {
          showResult(run);
          const status = String(run.status || "running").toLowerCase();
          if (["completed", "failed", "cancelled", "blocked", "error"].includes(status)) {
            const kind = status.includes("fail") || status === "error" || status === "blocked" ? "err" : "ok";
            addActivity(`Run ${status}`, run.blocked_reason || run.command_text || "", kind);
            stopPoll();
            await notifyJarvis({
              type: "run.finished",
              run_id: runId,
              status,
              summary: run.evidence?.demo_summary || run.blocked_reason || status,
            });
          }
        }

        if (trace) {
          const spans = trace.spans || trace.events || [];
          for (const span of spans) {
            const key = `${span.event || ""}:${JSON.stringify(span.details || span)}`;
            if (seen.has(key)) continue;
            seen.add(key);
            const agent = span.details?.agent || span.agent || span.event || "step";
            const detail =
              typeof span.details === "object"
                ? JSON.stringify(span.details)
                : String(span.message || span.detail || "");
            addActivity(String(agent), detail.slice(0, 280), "info");
            await notifyJarvis({
              type: "run.event",
              run_id: runId,
              event: span.event || "step",
              details: span.details || span,
            });
          }
          saveLocal(seenKey, [...seen].slice(-300));
        }
      } catch (err) {
        addActivity("Poll error", err.message, "err");
      }
    };

    await tick();
    state.pollTimer = setInterval(tick, 1200);
  }

  async function sendCommand() {
    const text = els.commandInput.value.trim();
    if (!text) return;

    els.btnSend.disabled = true;
    addActivity("Command", text, "cmd");
    showResult({ sending: text });

    try {
      const body = await api("/v1/command", {
        method: "POST",
        body: JSON.stringify({ text, channel: "text" }),
      });
      showResult(body);
      addActivity(
        body.status || "accepted",
        body.message || body.transcript || "Orchestrator accepted command",
        body.status === "needs_clarification" ? "err" : "ok"
      );

      // Surface agent steps immediately when returned inline
      const steps = body.run?.steps || [];
      for (const step of steps) {
        addActivity(
          step.agent_id || "agent",
          step.summary || (step.ok ? "ok" : "failed"),
          step.ok === false ? "err" : "info"
        );
      }

      const runId = extractRunId(body);
      await notifyJarvis({
        type: "command.accepted",
        text,
        run_id: runId,
        status: body.status,
        response: body,
      });

      if (runId) await pollRun(runId);
      await refreshFleet();
    } catch (err) {
      addActivity("Command failed", err.message, "err");
      showResult({ error: err.message });
    } finally {
      els.btnSend.disabled = false;
    }
  }

  async function notifyJarvis(payload) {
    if (!els.jarvisEnabled.checked) return;
    const webhook = els.jarvisUrl.value.trim();
    if (!webhook && !state.jarvis.serverRelay) return;

    const event = {
      source: "gie-command-console",
      ts: new Date().toISOString(),
      ...payload,
    };

    try {
      await api("/v1/integrations/jarvis/forward", {
        method: "POST",
        body: JSON.stringify({ event }),
      });
      return;
    } catch {
      /* browser fallback */
    }

    if (!webhook) return;
    try {
      const headers = { "Content-Type": "application/json" };
      const token = els.jarvisToken.value.trim();
      if (token) headers.Authorization = `Bearer ${token}`;
      await fetch(webhook, {
        method: "POST",
        headers,
        body: JSON.stringify(event),
        mode: "cors",
      });
    } catch (err) {
      addActivity(
        "JARVIS forward failed",
        `${err.message} — enable server relay or allow CORS on JARVIS`,
        "err"
      );
    }
  }

  async function refreshJarvis() {
    els.jarvisEnabled.checked = !!state.jarvis.enabled;
    els.jarvisUrl.value = state.jarvis.webhook_url || "";
    els.jarvisToken.value = state.jarvis.token || "";
    try {
      const cfg = await api("/v1/integrations/jarvis");
      state.jarvis.serverRelay = true;
      els.jarvisEnabled.checked = !!cfg.enabled;
      if (cfg.webhook_url) els.jarvisUrl.value = cfg.webhook_url;
      els.jarvisMsg.textContent = cfg.enabled
        ? "JARVIS bridge enabled on orchestrator."
        : "JARVIS bridge ready (currently off).";
    } catch {
      state.jarvis.serverRelay = false;
      els.jarvisMsg.textContent =
        "Browser-only JARVIS mode (orchestrator bridge unavailable).";
    }
  }

  async function saveJarvis() {
    const cfg = {
      enabled: els.jarvisEnabled.checked,
      webhook_url: els.jarvisUrl.value.trim(),
      token: els.jarvisToken.value.trim(),
    };
    state.jarvis = { ...state.jarvis, ...cfg };
    saveLocal("gie.jarvis", state.jarvis);

    try {
      await api("/v1/integrations/jarvis", {
        method: "PUT",
        body: JSON.stringify(cfg),
      });
      els.jarvisMsg.textContent = "Saved on orchestrator + browser.";
      addActivity("JARVIS settings saved", "server + local", "ok");
    } catch {
      els.jarvisMsg.textContent = "Saved in browser only.";
      addActivity("JARVIS settings saved", "local only", "info");
    }
  }

  async function testJarvis() {
    addActivity("JARVIS ping", "Sending test event…", "info");
    await notifyJarvis({
      type: "ping",
      message: "Hello from GIE Command Console",
    });
    addActivity("JARVIS ping queued", els.jarvisUrl.value || "server relay", "ok");
  }

  function setupVoice() {
    if (!els.btnVoice) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      els.btnVoice.disabled = true;
      els.btnVoice.title = "Speech recognition not supported here";
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      els.commandInput.value = text;
      addActivity("Voice captured", text, "cmd");
    };
    rec.onerror = (e) => addActivity("Voice error", e.error || "unknown", "err");
    els.btnVoice.addEventListener("click", () => {
      try {
        rec.start();
        addActivity("Listening…", "", "info");
      } catch {
        /* already started */
      }
    });
  }

  // hydrate
  els.apiBase.value = defaultApiBase();
  els.jarvisEnabled.checked = !!state.jarvis.enabled;
  els.jarvisUrl.value = state.jarvis.webhook_url || "";
  els.jarvisToken.value = state.jarvis.token || "";
  els.activity.innerHTML = "";
  addActivity("Ready", "Connect, then send a command.", "info");

  els.btnConnect.addEventListener("click", connect);
  els.btnSend.addEventListener("click", sendCommand);
  els.btnStatus.addEventListener("click", refreshFleet);
  els.btnClear.addEventListener("click", () => {
    stopPoll();
    els.activity.innerHTML = "";
    addActivity("Cleared", "Activity feed reset.", "info");
    els.resultBox.textContent = "No command yet.";
  });
  els.btnSaveJarvis.addEventListener("click", saveJarvis);
  els.btnTestJarvis.addEventListener("click", testJarvis);
  els.commandInput.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") sendCommand();
  });

  setupVoice();
  connect();
})();
