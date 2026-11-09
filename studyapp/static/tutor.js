const URLS = window.TUTOR_URLS;
const $ = (id) => document.getElementById(id);

// The server keeps nothing between requests: the extracted notes and the chat
// live here and are sent along with every question / quiz request.
// sessionStorage keeps them across a page reload in this tab.
const STORE_KEY = "sapience-tutor";
let session = { files: [], material: "", history: [] };

function saveSession() {
  try { sessionStorage.setItem(STORE_KEY, JSON.stringify(session)); } catch (_) { /* storage off/full */ }
}
function loadSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(STORE_KEY) || "null");
    if (s && typeof s.material === "string" && Array.isArray(s.files) && Array.isArray(s.history)) return s;
  } catch (_) { /* ignore */ }
  return null;
}
function clearSession() {
  session = { files: [], material: "", history: [] };
  try { sessionStorage.removeItem(STORE_KEY); } catch (_) { /* ignore */ }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

function setStatus(el, msg, { error = false, busy = false } = {}) {
  el.className = "sp-status" + (error ? " is-error" : "");
  el.innerHTML = (busy ? '<span class="sp-spinner"></span>' : "") + escapeHtml(msg);
}

// Errors from Render/gunicorn (timeouts, restarts) come back as HTML pages, not JSON.
async function postJson(url, body) {
  const res = await fetch(url, body instanceof FormData
    ? { method: "POST", body }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  let data = null;
  try { data = await res.json(); } catch (_) { /* not JSON */ }
  if (!data) {
    if (res.redirected || res.status === 401) throw new Error("You've been logged out. Please log in again.");
    if ([502, 503, 504].includes(res.status) || res.status === 0) {
      throw new Error("The server took too long (the AI may be busy). Please try again.");
    }
    throw new Error(`Server error (${res.status}). Please try again.`);
  }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// ---- Upload slot ----
const drop = $("materialsDrop");
const dropText = drop.querySelector(".sp-drop-text");

function refreshSlot() {
  const files = $("materials").files;
  drop.classList.toggle("has-file", files.length > 0);
  $("materialsRemove").classList.toggle("sp-hidden", !files.length);
  dropText.textContent = files.length
    ? Array.from(files).map((f) => f.name).join(", ")
    : dropText.dataset.empty;
}

$("materials").addEventListener("change", refreshSlot);
$("materialsRemove").addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  $("materials").value = "";
  refreshSlot();
});
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.add("is-over")));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("is-over")));

function showLoaded(files, skipped, truncated) {
  let html = files.map((f) => `<span class="sp-file-chip">📄 ${escapeHtml(f)}</span>`).join("");
  if (truncated) {
    html += `<p class="sp-hint" style="width:100%">Your notes are long, so the tutor only uses roughly the first 40,000 characters.</p>`;
  }
  if (skipped && skipped.length) {
    html += `<p class="sp-hint" style="width:100%">Skipped (unsupported or empty): ${skipped.map(escapeHtml).join(", ")}</p>`;
  }
  $("materialFiles").innerHTML = html;
  $("uploadPanel").classList.add("sp-hidden");
  ["materialPanel", "chatPanel", "quizPanel"].forEach((id) => $(id).classList.remove("sp-hidden"));
}

function showUpload() {
  $("uploadPanel").classList.remove("sp-hidden");
  ["materialPanel", "chatPanel", "quizPanel"].forEach((id) => $(id).classList.add("sp-hidden"));
}

$("analyzeBtn").addEventListener("click", async () => {
  const files = $("materials").files;
  const status = $("uploadStatus");

  if (!files.length) {
    setStatus(status, "Pick at least one file.", { error: true });
    return;
  }

  const fd = new FormData();
  for (const f of files) fd.append("materials", f);

  setStatus(status, "Reading your notes…", { busy: true });
  $("analyzeBtn").disabled = true;

  try {
    const data = await postJson(URLS.upload, fd);
    session = { files: data.files, material: data.material, history: [], truncated: !!data.truncated };
    saveSession();
    resetChat();
    resetQuiz();
    setStatus(status, "");
    showLoaded(data.files, data.skipped, data.truncated);
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    $("analyzeBtn").disabled = false;
  }
});

$("changeMaterialBtn").addEventListener("click", () => {
  clearSession();
  $("materials").value = "";
  refreshSlot();
  setStatus($("uploadStatus"), "");
  resetChat();
  resetQuiz();
  showUpload();
});

// ---- Chat ----
function resetChat() {
  $("chatLog").innerHTML = "";
  setStatus($("chatStatus"), "");
}

function addBubble(role, text) {
  const log = $("chatLog");
  const el = document.createElement("div");
  el.className = "sp-bubble " + (role === "user" ? "user" : "model");
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

async function sendChat() {
  const input = $("chatInput");
  const message = input.value.trim();
  if (!message) return;
  const status = $("chatStatus");

  const userBubble = addBubble("user", message);
  input.value = "";
  input.disabled = true;
  $("chatSendBtn").disabled = true;
  const thinking = addBubble("model", "thinking…");
  setStatus(status, "");

  try {
    const data = await postJson(URLS.chat, {
      message,
      material: session.material,
      history: session.history.slice(-20),
    });
    thinking.textContent = data.answer;
    session.history.push({ role: "user", text: message }, { role: "model", text: data.answer });
    saveSession();
  } catch (e) {
    thinking.remove();
    userBubble.remove();
    input.value = message; // let them resend without retyping
    setStatus(status, e.message, { error: true });
  } finally {
    input.disabled = false;
    $("chatSendBtn").disabled = false;
    input.focus();
  }
}

$("chatSendBtn").addEventListener("click", sendChat);
$("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

// ---- Quiz ----
let quizTotal = 0;
let quizAnswered = 0;
let quizRight = 0;

function resetQuiz() {
  $("quizContainer").innerHTML = "";
  $("quizScore").classList.add("sp-hidden");
  setStatus($("quizStatus"), "");
  quizTotal = quizAnswered = quizRight = 0;
}

$("quizCount").addEventListener("input", (e) => ($("quizCountLabel").textContent = e.target.value));

$("quizBtn").addEventListener("click", async () => {
  const status = $("quizStatus");
  resetQuiz();
  setStatus(status, "Writing your quiz…", { busy: true });
  $("quizBtn").disabled = true;

  try {
    const data = await postJson(URLS.quiz, {
      num_questions: parseInt($("quizCount").value, 10),
      material: session.material,
    });
    renderQuiz(data.questions || []);
    setStatus(status, "");
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    $("quizBtn").disabled = false;
  }
});

function updateScore() {
  const el = $("quizScore");
  el.classList.remove("sp-hidden");
  el.textContent = quizAnswered < quizTotal
    ? `${quizRight} / ${quizAnswered} so far`
    : `You got ${quizRight} / ${quizTotal} ${quizRight === quizTotal ? "★ perfect!" : quizRight / quizTotal >= 0.6 ? "— nice!" : "— review those notes and try again"}`;
}

function renderQuiz(questions) {
  const c = $("quizContainer");
  quizTotal = questions.length;

  questions.forEach((q, qi) => {
    const card = document.createElement("div");
    card.className = "sp-quiz-card";
    card.innerHTML = `<div class="sp-quiz-q">${qi + 1}. ${escapeHtml(q.question)}</div>
      <div class="sp-quiz-opts"></div>
      <div class="sp-quiz-explain sp-hidden"></div>`;

    const opts = card.querySelector(".sp-quiz-opts");
    (q.options || []).forEach((opt, oi) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sp-quiz-opt";
      btn.textContent = `${"ABCD"[oi] || oi + 1}. ${opt}`;
      btn.addEventListener("click", () => {
        if (card.dataset.answered) return;
        card.dataset.answered = "1";
        const correct = oi === q.correct_index;
        btn.classList.add(correct ? "is-correct" : "is-wrong");
        if (!correct && opts.children[q.correct_index]) {
          opts.children[q.correct_index].classList.add("is-correct");
        }
        const explain = card.querySelector(".sp-quiz-explain");
        explain.textContent = (correct ? "✓ Correct! " : "✗ Not quite. ") + (q.explanation || "");
        explain.classList.remove("sp-hidden");
        quizAnswered += 1;
        if (correct) quizRight += 1;
        updateScore();
      });
      opts.appendChild(btn);
    });

    c.appendChild(card);
  });
}

// ---- Restore notes + chat after a reload in this tab ----
(() => {
  const saved = loadSession();
  if (!saved || !saved.material) return;
  session = saved;
  showLoaded(session.files, [], session.truncated);
  session.history.forEach((t) => addBubble(t.role, t.text));
})();
