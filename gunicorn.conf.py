# Gunicorn loads this file automatically when started from the project root
# (e.g. Render's `gunicorn run:app`).

# Gemini calls (syllabus extraction, tutor answers, quizzes) can take longer than
# gunicorn's default 30s. Past that the worker is killed and the browser gets an
# HTML error page instead of JSON.
timeout = 120
