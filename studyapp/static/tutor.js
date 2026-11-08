const URLS = window.TUTOR_URLS;
const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

function setStatus(el, msg, { error = false, busy = false } = {}) {
  el.className = "sp-status" + (error ? " is-error" : "");
  el.innerHTML = (busy ? '<span class="sp-spinner"></span>' : "") + escapeHtml(msg);
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

function showLoaded(files, skipped) {
  let html = files.map((f) => `<span class="sp-file-chip">📄 ${escapeHtml(f)}</span>`).join("");
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
    const res = await fetch(URLS.upload, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    resetChat();
    resetQuiz();
    setStatus(status, "");
    showLoaded(data.files, data.skipped);
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    $("analyzeBtn").disabled = false;
  }
});

$("changeMaterialBtn").addEventListener("click", async () => {
  await fetch(URLS.clear, { method: "POST" });
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

  addBubble("user", message);
  input.value = "";
  input.disabled = true;
  $("chatSendBtn").disabled = true;
  const thinking = addBubble("model", "thinking…");
  setStatus(status, "");

  try {
    const res = await fetch(URLS.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Chat failed");
    thinking.textContent = data.answer;
  } catch (e) {
    thinking.remove();
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
    const res = await fetch(URLS.quiz, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_questions: parseInt($("quizCount").value, 10) }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Quiz generation failed");
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
    q.options.forEach((opt, oi) => {
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

// ---- Restore this user's session (notes + chat survive a page reload) ----
(async () => {
  try {
    const res = await fetch(URLS.state);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.files || !data.files.length) return;
    showLoaded(data.files, []);
    (data.chat_history || []).forEach((t) => addBubble(t.role, t.text));
  } catch (_) {
    /* stay on the upload panel */
  }
})();
