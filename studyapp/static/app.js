// ---- State ----
let extracted = null;   // { subjects: [{name, exam_date, topics: [{name, difficulty}]}] }
let planDays = null;
let planMaxHours = 4;

const URLS = window.PLANNER_URLS;
const $ = (id) => document.getElementById(id);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

function setStatus(el, msg, { error = false, busy = false } = {}) {
  el.className = "sp-status" + (error ? " is-error" : "");
  el.innerHTML = (busy ? '<span class="sp-spinner"></span>' : "") + escapeHtml(msg);
}

function localISODate(d = new Date()) {
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

function goToStep(n) {
  [1, 2, 3, 4].forEach((i) => {
    $("step" + i).classList.toggle("sp-hidden", i !== n);
    const s = document.querySelector(`.sp-step[data-step="${i}"]`);
    s.classList.toggle("is-active", i === n);
    s.classList.toggle("is-done", i < n);
    s.querySelector(".sp-step-dot").textContent = i < n ? "✓" : i;
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ---- Step 1: File slots ----
function wireSlot(inputId, removeId, dropId) {
  const input = $(inputId);
  const removeBtn = $(removeId);
  const drop = $(dropId);
  const text = drop.querySelector(".sp-drop-text");

  const refresh = () => {
    const f = input.files[0];
    drop.classList.toggle("has-file", !!f);
    removeBtn.classList.toggle("sp-hidden", !f);
    text.textContent = f ? f.name : text.dataset.empty;
  };

  input.addEventListener("change", refresh);
  removeBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    input.value = "";
    refresh();
  });
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.add("is-over")));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("is-over")));
  return refresh;
}
const refreshSyllabus = wireSlot("syllabus", "syllabusRemove", "syllabusDrop");
const refreshDatesheet = wireSlot("datesheet", "datesheetRemove", "datesheetDrop");

// ---- Step 1: Extract ----
$("extractBtn").addEventListener("click", async () => {
  const syllabus = $("syllabus").files[0];
  const datesheet = $("datesheet").files[0];
  const status = $("extractStatus");

  if (!syllabus) {
    setStatus(status, "Pick a syllabus PDF first.", { error: true });
    return;
  }

  const fd = new FormData();
  fd.append("syllabus", syllabus);
  if (datesheet) fd.append("datesheet", datesheet);

  setStatus(status, "Reading your syllabus…", { busy: true });
  $("extractBtn").disabled = true;

  try {
    const res = await fetch(URLS.extract, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Extraction failed");
    if (!data.subjects || !data.subjects.length) throw new Error("No subjects found in that PDF.");
    extracted = data;
    renderSubjects();
    setStatus(status, "");
    goToStep(2);
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    $("extractBtn").disabled = false;
  }
});

// ---- Step 2: Rate topics ----
function renderSubjects() {
  const c = $("subjectsContainer");
  c.innerHTML = "";

  extracted.subjects.forEach((subj, si) => {
    subj.topics = subj.topics.map((t) =>
      typeof t === "string" ? { name: t, difficulty: "medium" } : { name: t.name, difficulty: t.difficulty || "medium" }
    );

    const card = document.createElement("div");
    card.className = "sp-subject";
    const exam = subj.exam_date
      ? `<span class="sp-exam-tag">exam · ${escapeHtml(subj.exam_date)}</span>`
      : `<span class="sp-exam-tag is-missing">no exam date found</span>`;
    card.innerHTML = `<div class="sp-subject-head"><h3 class="sp-subject-name">${escapeHtml(subj.name)}</h3>${exam}</div>`;

    subj.topics.forEach((topic, ti) => {
      const row = document.createElement("div");
      row.className = "sp-topic";
      row.innerHTML = `<span class="sp-topic-name">${escapeHtml(topic.name)}</span>
        <div class="sp-diff" role="group" aria-label="Confidence">
          ${["weak", "medium", "strong"].map((d) =>
            `<button type="button" class="sp-chip ${d}${d === topic.difficulty ? " is-on" : ""}"
               data-s="${si}" data-t="${ti}" data-d="${d}" aria-pressed="${d === topic.difficulty}">${d}</button>`
          ).join("")}
        </div>`;
      card.appendChild(row);
    });
    c.appendChild(card);
  });
}

$("subjectsContainer").addEventListener("click", (e) => {
  const btn = e.target.closest(".sp-chip");
  if (!btn) return;
  const { s, t, d } = btn.dataset;
  extracted.subjects[s].topics[t].difficulty = d;
  btn.parentElement.querySelectorAll(".sp-chip").forEach((b) => {
    b.classList.toggle("is-on", b === btn);
    b.setAttribute("aria-pressed", b === btn);
  });
});

$("backTo1").addEventListener("click", () => goToStep(1));
$("toSettings").addEventListener("click", () => {
  if (!$("startDate").value) $("startDate").value = localISODate();
  goToStep(3);
});

// ---- Step 3: Settings ----
$("maxHours").addEventListener("input", (e) => ($("hoursLabel").textContent = e.target.value));
$("prepDays").addEventListener("input", (e) => ($("prepLabel").textContent = e.target.value));
$("backTo2").addEventListener("click", () => goToStep(2));

$("generateBtn").addEventListener("click", async () => {
  const status = $("planStatus");
  if (!$("startDate").value) {
    setStatus(status, "Pick a start date.", { error: true });
    return;
  }
  setStatus(status, "Building your plan…", { busy: true });
  $("generateBtn").disabled = true;
  planMaxHours = parseFloat($("maxHours").value);

  try {
    const res = await fetch(URLS.plan, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjects: extracted.subjects,
        start_date: $("startDate").value,
        max_hours_per_day: planMaxHours,
        prep_days_before_exam: parseInt($("prepDays").value, 10),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Planning failed");
    planDays = data.days;
    renderPlan();
    setStatus(status, "");
    setStatus($("calendarStatus"), "");
    goToStep(4);
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    $("generateBtn").disabled = false;
  }
});

// ---- Step 4: Plan ----
function renderPlan() {
  const c = $("planContainer");
  const summary = $("planSummary");
  c.innerHTML = "";
  summary.innerHTML = "";

  if (!planDays.length) {
    c.innerHTML = "<p class='sp-hint'>No study days fit. Check the start date is before your exams.</p>";
    return;
  }

  const studyHours = planDays.reduce(
    (sum, d) => sum + d.blocks.filter((b) => b.type === "study").reduce((s, b) => s + b.hours, 0), 0
  );
  const topicCount = planDays.reduce((n, d) => n + d.blocks.filter((b) => b.type === "study").length, 0);
  const overflow = planDays.some((d) => d.blocks.some((b) => b.overflow));
  summary.innerHTML = `
    <span class="sp-stat"><b>${planDays.length}</b> days</span>
    <span class="sp-stat"><b>${topicCount}</b> topics</span>
    <span class="sp-stat"><b>${Math.round(studyHours * 10) / 10}</b> study hours</span>
    ${overflow ? `<span class="sp-stat">⚠ some days are over your limit</span>` : ""}`;

  const today = localISODate();

  planDays.forEach((day) => {
    const [y, m, d] = day.date.split("-").map(Number);
    const isRevision = day.blocks.every((b) => b.type === "revision");
    const pct = Math.min(100, Math.round((day.total_hours / planMaxHours) * 100));

    const blocks = day.blocks.map((b) => {
      const cls = b.type === "revision" ? "revision" : b.difficulty || "medium";
      const tag = b.type === "revision" ? "REVISION" : (b.difficulty || "medium").toUpperCase();
      return `<div class="sp-block">
        <span class="sp-tag ${cls}">${tag}</span>
        ${b.overflow ? `<span class="sp-tag overflow">OVER LIMIT</span>` : ""}
        <span>${escapeHtml(b.topic)}</span>
        <span class="sp-block-meta">${escapeHtml(b.subject)} · ${b.hours}h</span>
      </div>`;
    }).join("");

    const el = document.createElement("article");
    el.className = "sp-ticket" + (isRevision ? " is-revision" : "") + (day.date === today ? " is-today" : "");
    el.innerHTML = `
      <div class="sp-stub">
        <span class="sp-stub-week">${escapeHtml(day.weekday.slice(0, 3))}</span>
        <span class="sp-stub-day">${d}</span>
        <span class="sp-stub-month">${MONTHS[m - 1]} ${y}</span>
      </div>
      <div class="sp-ticket-body">
        <div class="sp-load">
          <div class="sp-load-bar"><div class="sp-load-fill${pct >= 100 ? " is-full" : ""}" style="width:${pct}%"></div></div>
          <span>${day.total_hours}h</span>
        </div>
        ${blocks}
      </div>`;
    c.appendChild(el);
  });
}

$("downloadBtn").addEventListener("click", async () => {
  const btn = $("downloadBtn");
  btn.disabled = true;
  try {
    const res = await fetch(URLS.download, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days: planDays }),
    });
    if (!res.ok) throw new Error("Couldn't build the PDF");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "study_plan.pdf";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    setStatus($("calendarStatus"), e.message, { error: true });
  } finally {
    btn.disabled = false;
  }
});

$("calendarBtn").addEventListener("click", async () => {
  const btn = $("calendarBtn");
  const status = $("calendarStatus");
  btn.disabled = true;
  setStatus(status, "Writing your plan into the calendar…", { busy: true });
  try {
    const res = await fetch(URLS.toCalendar, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days: planDays }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Couldn't update the calendar");
    status.className = "sp-status";
    status.innerHTML = `✓ Added to ${data.days} day${data.days === 1 ? "" : "s"} in your calendar. ` +
      `<a href="${URLS.calendar}" style="color:#000;text-decoration:underline">open calendar →</a>`;
  } catch (e) {
    setStatus(status, e.message, { error: true });
  } finally {
    btn.disabled = false;
  }
});

$("restartBtn").addEventListener("click", () => {
  extracted = null;
  planDays = null;
  $("syllabus").value = "";
  $("datesheet").value = "";
  refreshSyllabus();
  refreshDatesheet();
  goToStep(1);
});
