/* ================================================================
   TONECHECK — popup.js
   ================================================================ */


const API_BASE = "http://127.0.0.1:5000";


// ----- element refs -----
const $ = (id) => document.getElementById(id);


const el = {
  input: $("input"),
  counter: $("counter"),
  analyzeBtn: $("analyze-btn"),
  clearBtn: $("clear-btn"),
  status: $("status"),
  statusLabel: $("status-label"),
  stateIdle: $("state-idle"),
  stateLoading: $("state-loading"),
  stateResult: $("state-result"),
  stateError: $("state-error"),
  errBody: $("err-body"),
  verdict: $("verdict"),
  verdictTag: $("verdict-tag"),
  verdictLabel: $("verdict-label"),
  confidenceNum: $("confidence-num"),
  gaugeFill: $("gauge-fill"),
  tabs: $("tabs"),
  tabUnderline: $("tab-underline"),
  explainText: $("explain-text"),
  rewriteText: $("rewrite-text"),
  safeNote: $("safe-note"),
  copyRewrite: $("copy-rewrite"),
  pingBtn: $("ping-btn"),
  panelExplain: $("panel-explain"),
  panelRewrite: $("panel-rewrite"),
  tabPanels: $("tab-panels"),
};


// ================================================================
// INIT
// ================================================================
document.addEventListener("DOMContentLoaded", () => {
  chrome.storage?.local.get(["lastDraft"], (data) => {
    if (data.lastDraft) {
      el.input.value = data.lastDraft;
      updateCounter();
    }
  });


  chrome.storage?.local.get(["pendingText"], (data) => {
    if (data.pendingText) {
      el.input.value = data.pendingText;
      chrome.storage.local.remove(["pendingText"]);
      updateCounter();
      setTimeout(runAnalysis, 250);
    }
  });


  pingServer();
  setupTabs();
});


// ================================================================
// INPUT HANDLERS
// ================================================================
el.input.addEventListener("input", () => {
  updateCounter();
  chrome.storage?.local.set({ lastDraft: el.input.value });
});


el.input.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    runAnalysis();
  }
});


el.analyzeBtn.addEventListener("click", runAnalysis);
el.clearBtn.addEventListener("click", () => {
  el.input.value = "";
  chrome.storage?.local.remove(["lastDraft"]);
  updateCounter();
  showState("idle");
});


el.pingBtn.addEventListener("click", (e) => {
  e.preventDefault();
  pingServer();
});


el.copyRewrite.addEventListener("click", () => {
  const txt = el.rewriteText.textContent.trim();
  if (!txt || txt === "—") return;
  navigator.clipboard.writeText(txt).then(() => {
    el.copyRewrite.textContent = "copied";
    el.copyRewrite.classList.add("copied");
    setTimeout(() => {
      el.copyRewrite.textContent = "copy";
      el.copyRewrite.classList.remove("copied");
    }, 1500);
  });
});


function updateCounter() {
  const n = el.input.value.length;
  el.counter.textContent = `${n} char${n === 1 ? "" : "s"}`;
}


// ================================================================
// SERVER HEALTH
// ================================================================
async function pingServer() {
  setStatus("connecting", "pending");
  try {
    const r = await fetch(`${API_BASE}/health`, { method: "GET" });
    if (!r.ok) throw new Error("bad response");
    const data = await r.json();
    setStatus(`online · acc ${(data.test_accuracy * 100).toFixed(0)}%`, "online");
  } catch (err) {
    setStatus("offline", "offline");
  }
}


function setStatus(label, state) {
  el.statusLabel.textContent = label;
  el.status.classList.remove("online", "offline");
  if (state === "online") el.status.classList.add("online");
  else if (state === "offline") el.status.classList.add("offline");
}


// ================================================================
// ANALYSIS
// ================================================================
async function runAnalysis() {
  const text = el.input.value.trim();
  if (!text) {
    el.input.focus();
    return;
  }


  showState("loading");
  animateLoaderSteps();


  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comment: text, top_k: 5 }),
    });


    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Server returned ${res.status}`);
    }


    const data = await res.json();
    renderResult(data);
  } catch (err) {
    el.errBody.textContent = err.message.includes("fetch")
      ? "Cannot reach the analysis server."
      : err.message;
    showState("error");
  }
}


let loaderInterval;
function animateLoaderSteps() {
  const steps = document.querySelectorAll(".step");
  let i = 0;
  clearInterval(loaderInterval);
  steps.forEach((s) => s.classList.remove("active"));
  steps[0].classList.add("active");
  loaderInterval = setInterval(() => {
    steps.forEach((s) => s.classList.remove("active"));
    i = (i + 1) % steps.length;
    steps[i].classList.add("active");
  }, 600);
}


// ================================================================
// RENDERING
// ================================================================
function renderResult(data) {
  clearInterval(loaderInterval);
  showState("result");


  const isToxic = data.prediction === "Toxic";
  const pct = Math.round((data.confidence || 0) * 100);


  el.verdict.classList.remove("toxic", "safe");
  el.verdict.classList.add(isToxic ? "toxic" : "safe");
  el.verdictTag.textContent = isToxic ? "Flagged" : "Clear";
  el.verdictLabel.textContent = isToxic ? "toxic · attention required" : "no markers detected";
  el.confidenceNum.textContent = pct;


  el.gaugeFill.style.width = "0%";
  requestAnimationFrame(() => {
    setTimeout(() => { el.gaugeFill.style.width = `${pct}%`; }, 40);
  });


  if (isToxic) {
    el.tabs.classList.remove("hidden");
    el.safeNote.classList.add("hidden");
    el.tabPanels.classList.remove("hidden");


    el.explainText.textContent = data.explanation || "(no explanation available)";
    el.rewriteText.textContent = data.rewrite || "(no rewrite available)";


    activateTab("explain");
  } else {
    el.tabs.classList.add("hidden");
    el.tabPanels.classList.add("hidden");
    el.safeNote.classList.remove("hidden");
  }
}


// ================================================================
// STATE SWITCHER
// ================================================================
function showState(state) {
  [el.stateIdle, el.stateLoading, el.stateResult, el.stateError].forEach((s) =>
    s.classList.add("hidden")
  );
  const map = {
    idle: el.stateIdle,
    loading: el.stateLoading,
    result: el.stateResult,
    error: el.stateError,
  };
  map[state]?.classList.remove("hidden");


  if (state === "loading") {
    el.analyzeBtn.disabled = true;
    el.analyzeBtn.querySelector(".btn-label").textContent = "Analyzing";
  } else {
    el.analyzeBtn.disabled = false;
    el.analyzeBtn.querySelector(".btn-label").textContent = "Run analysis";
  }
}


// ================================================================
// TABS
// ================================================================
function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((t) => {
    t.addEventListener("click", () => activateTab(t.dataset.tab));
  });
  requestAnimationFrame(() => positionUnderline(document.querySelector(".tab.active")));
}


function activateTab(name) {
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
  let activeTab;
  tabs.forEach((t) => {
    const isActive = t.dataset.tab === name;
    t.classList.toggle("active", isActive);
    if (isActive) activeTab = t;
  });
  panels.forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
  positionUnderline(activeTab);
}


function positionUnderline(tab) {
  if (!tab) return;
  const rect = tab.getBoundingClientRect();
  const parent = tab.parentElement.getBoundingClientRect();
  el.tabUnderline.style.left = `${rect.left - parent.left}px`;
  el.tabUnderline.style.width = `${rect.width}px`;
}

