"""AI Study Planner + Study Tutor routes.
Pipeline: PDF -> text -> LLM (JSON) -> user marks difficulty -> scheduler -> plan -> PDF
"""
import os
import io
import json
import datetime as dt
from flask import request, jsonify, render_template, send_file
from flask_login import login_required, current_user
import fitz
from pptx import Presentation
from google import genai
from google.genai import types

from studyapp import app, db
from studyapp.models import Schedule

MODEL = "gemini-flash-latest"

DIFFICULTY_WEIGHT = {"weak": 1.5, "medium": 1.0, "strong": 0.5}

_client = None


def get_client():
    """Create the Gemini client lazily so the rest of the app still starts
    when GEMINI_API_KEY isn't set."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


# ---------- PDF text extraction ----------
def extract_pdf_text(data):
    doc = fitz.open(stream=data, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


# ---------- Study-material text extraction (tutor feature) ----------
def extract_pptx_text(data):
    prs = Presentation(io.BytesIO(data))
    lines = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs)
                    if line.strip():
                        lines.append(line)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            lines.append(cell.text)
    return "\n".join(lines).strip()


def extract_txt_text(data):
    return data.decode("utf-8", errors="ignore").strip()


MATERIAL_EXTRACTORS = {
    ".pdf": extract_pdf_text,
    ".pptx": extract_pptx_text,
    ".txt": extract_txt_text,
}

# In-memory tutor sessions, one per logged-in user (cleared on server restart).
TUTOR_STATES = {}
MATERIAL_CHAR_LIMIT = 40000


def get_tutor_state():
    return TUTOR_STATES.setdefault(
        current_user.id, {"material_text": "", "files": [], "chat_history": []}
    )


# ---------- LLM extraction ----------
EXTRACTION_PROMPT = """You are given raw text from a student's SYLLABUS and DATESHEET.
Extract subjects, their topics, and exam dates.

Return ONLY valid JSON (no markdown, no prose) in exactly this shape:
{{
  "subjects": [
    {{
      "name": "Subject name",
      "exam_date": "YYYY-MM-DD or null if unknown",
      "topics": ["topic 1", "topic 2"]
    }}
  ]
}}

Rules:
- Merge syllabus topics with datesheet dates by matching subject names (they may differ slightly).
- Keep topics granular but not trivial (a chapter or major concept per topic).
- If a date is written like "15 March 2026", convert to 2026-03-15.
- If no year is present, assume the next occurrence relative to today.
- Do not invent topics that aren't in the text.

Here is the text:

--- SYLLABUS ---
{syllabus}

--- DATESHEET ---
{datesheet}
"""


def llm_extract(syllabus_text, datesheet_text):
    prompt = EXTRACTION_PROMPT.format(
        syllabus=syllabus_text[:15000],
        datesheet=datesheet_text[:15000]
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt
    )

    raw = response.text.strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)


# ---------- Tutor: chat grounded in uploaded study material ----------
TUTOR_SYSTEM_INSTRUCTION = """You are a personal tutor helping a student understand their own study material.
Answer questions using ONLY the study material provided below — do not use outside knowledge, even if you know the answer.
If the material does not cover what's being asked, say so plainly instead of guessing.
Keep answers concise and clear, and mention which part of the material (e.g. slide, section, file) the answer comes from when it helps.

--- STUDY MATERIAL ---
___MATERIAL___
"""


def tutor_chat_reply(state, message):
    system_instruction = TUTOR_SYSTEM_INSTRUCTION.replace(
        "___MATERIAL___", state["material_text"][:MATERIAL_CHAR_LIMIT]
    )
    contents = [
        {"role": turn["role"], "parts": [{"text": turn["text"]}]}
        for turn in state["chat_history"][-20:]
    ]
    contents.append({"role": "user", "parts": [{"text": message}]})

    response = get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    return response.text.strip()


# ---------- Tutor: quiz generation ----------
QUIZ_PROMPT = """Based ONLY on the study material below, write ___N___ multiple-choice questions that test understanding of it.

Return ONLY valid JSON (no markdown, no prose) in exactly this shape:
{
  "questions": [
    {
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "One sentence on why this is correct, referencing the material"
    }
  ]
}

Rules:
- Base every question strictly on the material below; never invent facts not present in it.
- Exactly 4 options per question, exactly one correct answer.
- Cover a spread of topics/sections rather than clustering on one part.
- Vary difficulty (some recall, some understanding).

--- STUDY MATERIAL ---
___MATERIAL___
"""


def llm_generate_quiz(state, num_questions):
    prompt = QUIZ_PROMPT.replace("___N___", str(num_questions)).replace(
        "___MATERIAL___", state["material_text"][:MATERIAL_CHAR_LIMIT]
    )
    response = get_client().models.generate_content(model=MODEL, contents=prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ---------- Scheduling algorithm ----------
def build_schedule(subjects, start_date, max_hours_per_day, prep_days_before_exam):
    """
    Greedy allocator.
    - Each topic gets weighted hours by difficulty.
    - Topics scheduled before their subject's exam date.
    - `prep_days_before_exam` days immediately before each exam are reserved for revision.
    - Weak topics are scheduled earlier to allow a second pass.
    """
    start = dt.date.fromisoformat(start_date)

    # Flatten topics with metadata
    topics = []
    for subj in subjects:
        exam_date = subj.get("exam_date")
        exam = dt.date.fromisoformat(exam_date) if exam_date else None
        for t in subj["topics"]:
            diff = t.get("difficulty", "medium").lower()
            topics.append({
                "subject": subj["name"],
                "topic": t["name"] if isinstance(t, dict) else t,
                "difficulty": diff,
                "hours": round(1.5 * DIFFICULTY_WEIGHT.get(diff, 1.0), 1),
                "exam": exam,
            })

    # Sort: earliest exam first, then hardest (weak) first
    diff_order = {"weak": 0, "medium": 1, "strong": 2}
    topics.sort(key=lambda x: (
        x["exam"] or dt.date.max,
        diff_order.get(x["difficulty"], 1),
    ))

    # Reserved revision dates (prep leave) per subject
    reserved = {}  # date -> subject name
    for subj in subjects:
        if not subj.get("exam_date"):
            continue
        exam = dt.date.fromisoformat(subj["exam_date"])
        for i in range(1, prep_days_before_exam + 1):
            reserved[exam - dt.timedelta(days=i)] = subj["name"]

    plan = {}  # date -> list of blocks
    cursor = start

    def day_load(d):
        return sum(b["hours"] for b in plan.get(d, []))

    for topic in topics:
        placed = False
        d = cursor
        # try to place the topic on the earliest day with capacity, before exam
        for _ in range(365):
            if topic["exam"] and d >= topic["exam"]:
                break  # can't study after/at exam
            if d in reserved:  # skip reserved revision days for new topics
                d += dt.timedelta(days=1)
                continue
            if day_load(d) + topic["hours"] <= max_hours_per_day:
                plan.setdefault(d, []).append({
                    "subject": topic["subject"],
                    "topic": topic["topic"],
                    "difficulty": topic["difficulty"],
                    "hours": topic["hours"],
                    "type": "study",
                })
                placed = True
                break
            d += dt.timedelta(days=1)
        if not placed:
            # overflow: still place on last possible day before exam
            fallback = (topic["exam"] - dt.timedelta(days=1)) if topic["exam"] else cursor
            plan.setdefault(fallback, []).append({
                "subject": topic["subject"],
                "topic": topic["topic"],
                "difficulty": topic["difficulty"],
                "hours": topic["hours"],
                "type": "study",
                "overflow": True,
            })

    # Add revision blocks on reserved days
    for d, subj_name in reserved.items():
        if d >= start:
            plan.setdefault(d, []).append({
                "subject": subj_name,
                "topic": f"Revision & practice — {subj_name}",
                "difficulty": None,
                "hours": max_hours_per_day,
                "type": "revision",
            })

    # Convert to sorted list
    days = []
    for d in sorted(plan.keys()):
        days.append({
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "blocks": plan[d],
            "total_hours": round(sum(b["hours"] for b in plan[d]), 1),
        })
    return days


# ---------- Routes ----------
# "/" is the Sapience home page (routes.home); the planner replaced the old to-do list.
@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html", title="Study Planner")


@app.route("/tutor")
@login_required
def tutor_page():
    return render_template("tutor.html", title="Study Tutor")


@app.route("/tutor/state")
@login_required
def tutor_state():
    state = get_tutor_state()
    return jsonify({"files": state["files"], "chat_history": state["chat_history"]})


@app.route("/tutor/upload", methods=["POST"])
@login_required
def tutor_upload():
    files = request.files.getlist("materials")
    files = [f for f in files if f and f.filename]
    if not files:
        return jsonify({"error": "Please choose at least one file"}), 400

    texts = []
    names = []
    skipped = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        extractor = MATERIAL_EXTRACTORS.get(ext)
        if not extractor:
            skipped.append(f.filename)
            continue
        text = extractor(f.read())
        if text:
            texts.append(f"--- {f.filename} ---\n{text}")
            names.append(f.filename)
        else:
            skipped.append(f.filename)

    if not texts:
        return jsonify({"error": "Couldn't extract any text from those files"}), 400

    state = get_tutor_state()
    state["material_text"] = "\n\n".join(texts)
    state["files"] = names
    state["chat_history"] = []

    return jsonify({"files": names, "skipped": skipped, "chars": len(state["material_text"])})


@app.route("/tutor/clear", methods=["POST"])
@login_required
def tutor_clear():
    get_tutor_state().update(material_text="", files=[], chat_history=[])
    return jsonify({"ok": True})


@app.route("/tutor/chat", methods=["POST"])
@login_required
def tutor_chat():
    payload = request.get_json() or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    state = get_tutor_state()
    if not state["material_text"]:
        return jsonify({"error": "Upload study material first"}), 400

    try:
        answer = tutor_chat_reply(state, message)
    except Exception as e:
        return jsonify({"error": f"Chat failed: {e}"}), 500

    state["chat_history"].append({"role": "user", "text": message})
    state["chat_history"].append({"role": "model", "text": answer})
    return jsonify({"answer": answer})


@app.route("/tutor/quiz", methods=["POST"])
@login_required
def tutor_quiz():
    state = get_tutor_state()
    if not state["material_text"]:
        return jsonify({"error": "Upload study material first"}), 400

    payload = request.get_json(silent=True) or {}
    num_questions = int(payload.get("num_questions", 5))
    num_questions = max(3, min(num_questions, 10))

    try:
        data = llm_generate_quiz(state, num_questions)
    except Exception as e:
        return jsonify({"error": f"Quiz generation failed: {e}"}), 500

    return jsonify(data)


@app.route("/extract", methods=["POST"])
@login_required
def extract():
    syllabus = request.files.get("syllabus")
    datesheet = request.files.get("datesheet")
    if not syllabus:
        return jsonify({"error": "Syllabus PDF is required"}), 400

    syl_text = extract_pdf_text(syllabus.read())

    date_text = ""
    if datesheet:
        date_text = extract_pdf_text(datesheet.read())

    try:
        data = llm_extract(syl_text, date_text)
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {e}"}), 500

    return jsonify(data)


@app.route("/plan", methods=["POST"])
@login_required
def plan():
    payload = request.get_json()
    subjects = payload["subjects"]
    start_date = payload["start_date"]
    max_hours = float(payload.get("max_hours_per_day", 4))
    prep_days = int(payload.get("prep_days_before_exam", 1))

    days = build_schedule(subjects, start_date, max_hours, prep_days)
    return jsonify({"days": days})


def plan_block_line(block):
    if block.get("type") == "revision":
        return f"• {block['topic']} ({block['hours']}h)"
    tag = (block.get("difficulty") or "medium").upper()
    return f"• [{block['subject']}] {block['topic']} ({block['hours']}h, {tag})"


@app.route("/plan/calendar", methods=["POST"])
@login_required
def plan_to_calendar():
    """Write each plan day into the user's Calendar notes.
    Appends to a day's existing notes and skips lines that are already there,
    so pressing the button twice doesn't duplicate anything."""
    payload = request.get_json(silent=True) or {}
    days = payload.get("days") or []
    if not days:
        return jsonify({"error": "Generate a plan first"}), 400

    touched = 0
    for day in days:
        try:
            date = dt.date.fromisoformat(day["date"])
        except (KeyError, TypeError, ValueError):
            continue
        lines = [plan_block_line(b) for b in day.get("blocks", [])]
        if not lines:
            continue

        schedule = Schedule.query.filter_by(user=current_user, date=date).first()
        if schedule is None:
            db.session.add(Schedule(date=date, notes="Study plan:\n" + "\n".join(lines), user=current_user))
            touched += 1
            continue

        existing = schedule.notes or ""
        new_lines = [line for line in lines if line not in existing]
        if new_lines:
            header = "" if "Study plan:" in existing else "Study plan:\n"
            sep = "\n\n" if existing.strip() else ""
            schedule.notes = existing.rstrip() + sep + header + "\n".join(new_lines)
            touched += 1

    db.session.commit()
    return jsonify({"days": touched})


@app.route("/download", methods=["POST"])
@login_required
def download():
    payload = request.get_json()
    days = payload["days"]
    pdf_bytes = render_plan_pdf(days)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="study_plan.pdf",
    )


def render_plan_pdf(days):
    doc = fitz.open()
    page = doc.new_page()
    y = 60
    page.insert_text((50, y), "AI Study Plan", fontsize=22, fontname="helv")
    y += 40
    for day in days:
        if y > 760:
            page = doc.new_page()
            y = 60
        header = f"{day['date']} ({day['weekday']}) — {day['total_hours']}h"
        page.insert_text((50, y), header, fontsize=13, fontname="hebo")
        y += 20
        for b in day["blocks"]:
            tag = "REVISION" if b["type"] == "revision" else b.get("difficulty", "").upper()
            line = f"   • [{b['subject']}] {b['topic']} ({b['hours']}h) {tag}"
            page.insert_text((60, y), line[:95], fontsize=10, fontname="helv")
            y += 16
            if y > 780:
                page = doc.new_page()
                y = 60
        y += 10
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
