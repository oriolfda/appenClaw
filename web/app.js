const $ = (id) => document.getElementById(id);

const els = {
  settingsPanel: $("settingsPanel"),
  toggleSettings: $("toggleSettings"),
  endpoint: $("endpoint"),
  token: $("token"),
  sessionId: $("sessionId"),
  language: $("language"),
  showTranscription: $("showTranscription"),
  saveSettings: $("saveSettings"),
  checkStatus: $("checkStatus"),
  statusLine: $("statusLine"),
  messages: $("messages"),
  messageInput: $("messageInput"),
  sendBtn: $("sendBtn"),
  fileInput: $("fileInput"),
  attachmentHint: $("attachmentHint"),
  player: $("player"),
};

const defaultCfg = {
  endpoint: "http://192.168.0.210:8091",
  token: "",
  sessionId: "appenclaw-app-chat",
  language: "auto",
  showTranscription: true,
};

let attachment = null;

function loadCfg() {
  const raw = localStorage.getItem("appenclaw-web-config");
  const cfg = raw ? { ...defaultCfg, ...JSON.parse(raw) } : defaultCfg;
  els.endpoint.value = cfg.endpoint;
  els.token.value = cfg.token;
  els.sessionId.value = cfg.sessionId;
  els.language.value = cfg.language;
  els.showTranscription.checked = !!cfg.showTranscription;
}

function saveCfg() {
  const cfg = {
    endpoint: els.endpoint.value.trim().replace(/\/$/, ""),
    token: els.token.value.trim(),
    sessionId: els.sessionId.value.trim() || "appenclaw-app-chat",
    language: els.language.value,
    showTranscription: els.showTranscription.checked,
  };
  localStorage.setItem("appenclaw-web-config", JSON.stringify(cfg));
  setStatus("Configuració desada");
  return cfg;
}

function setStatus(txt) {
  els.statusLine.textContent = txt;
}

function appendMessage(text, role = "bot", meta = "") {
  const div = document.createElement("article");
  div.className = `msg ${role}`;
  div.textContent = text;
  if (meta) {
    const small = document.createElement("small");
    small.textContent = meta;
    div.appendChild(small);
  }
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}

function authHeaders(cfg) {
  const h = { "Content-Type": "application/json" };
  if (cfg.token) h.Authorization = `Bearer ${cfg.token}`;
  return h;
}

async function checkStatus() {
  const cfg = saveCfg();
  try {
    const res = await fetch(`${cfg.endpoint}/status`, { headers: authHeaders(cfg) });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
    const c = data.context || {};
    const used = c.usedPercent == null ? "?" : `${c.usedPercent}%`;
    setStatus(`OK · sessió ${c.sessionId || cfg.sessionId} · context ${used}`);
  } catch (err) {
    setStatus(`Error estat: ${err.message}`);
  }
}

function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onerror = reject;
    fr.onload = () => {
      const out = String(fr.result || "");
      const b64 = out.includes(",") ? out.split(",")[1] : out;
      resolve(b64);
    };
    fr.readAsDataURL(file);
  });
}

els.fileInput.addEventListener("change", async () => {
  const file = els.fileInput.files?.[0];
  if (!file) {
    attachment = null;
    els.attachmentHint.textContent = "";
    return;
  }
  const b64 = await fileToB64(file);
  attachment = { name: file.name, mime: file.type || "application/octet-stream", dataBase64: b64 };
  els.attachmentHint.textContent = `Adjunt: ${file.name} (${Math.round(file.size / 1024)} KB)`;
});

async function sendMessage() {
  const cfg = saveCfg();
  const message = els.messageInput.value.trim();
  if (!message && !attachment) return;

  appendMessage(message || "[adjunt]", "user");
  els.messageInput.value = "";
  els.sendBtn.disabled = true;
  setStatus("Enviant...");

  const payload = {
    sessionId: cfg.sessionId,
    message,
    prefs: {
      language: cfg.language,
      showTranscription: cfg.showTranscription,
    },
  };
  if (attachment) payload.attachment = attachment;

  try {
    const res = await fetch(`${cfg.endpoint}/chat`, {
      method: "POST",
      headers: authHeaders(cfg),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);

    appendMessage(data.reply || "(sense text)", "bot", data.sessionId || "");
    if (data.mediaUrl) {
      els.player.src = data.mediaUrl;
      els.player.classList.remove("hidden");
      try { await els.player.play(); } catch (_) {}
    }

    attachment = null;
    els.fileInput.value = "";
    els.attachmentHint.textContent = "";
    setStatus("Resposta rebuda");
  } catch (err) {
    appendMessage(`Error: ${err.message}`, "bot");
    setStatus("Error d'enviament");
  } finally {
    els.sendBtn.disabled = false;
  }
}

els.toggleSettings.addEventListener("click", () => {
  els.settingsPanel.classList.toggle("hidden");
});
els.saveSettings.addEventListener("click", saveCfg);
els.checkStatus.addEventListener("click", checkStatus);
els.sendBtn.addEventListener("click", sendMessage);
els.messageInput.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && !ev.shiftKey) {
    ev.preventDefault();
    sendMessage();
  }
});

loadCfg();
checkStatus();
