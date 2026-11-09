📚 Do you self-study a lot using online resources?
If you're anything like me, you probably save them in a hundred different ways —
 🔖 Bookmarking websites,
 📂 Saving YouTube playlists,
 📩 Or even forwarding links to yourself on WhatsApp.
 
And then the chaos begins.
You vaguely remember a video or article, but...
Was it on YouTube? Did I send it to a friend? Was it bookmarked or buried in my messages?!!
Now you have to scroll endlessly through multiple platforms, fighting distractions and losing time — often ending up in a spiral of clickbait and doomscrolling.

That’s why I built Sapience 🧠
A minimal, personal productivity platform that helps you stay organized and focused:
✅ Resource Hub – Save all your study links (websites, playlists, videos) under titles you can easily search later. No more “where did I save that?”
✅ Study Planner – Upload your syllabus and datesheet, and get a day-by-day study plan built around your exams.
✅ Study Tutor – Upload your notes or slides, ask doubts about them, and quiz yourself.
✅ Calendar – Save your schedules like upcoming exams, contests, deadlines, or classes.
✅ Pomodoro Timer – With customizable work/break sessions or the classic 25–5 timing (just hit reset). 

🗓 How the Study Planner works:
1. Upload – Add your syllabus PDF (and your datesheet PDF, if you have one). AI reads them and pulls out each subject, its topics, and its exam date.
2. Rate your topics – Mark every topic as Weak, Medium, or Strong. Weak topics get more time (2.2h) and earlier slots so there's room for a second pass; Medium gets 1.5h and Strong gets 0.8h.
3. Settings – Pick a start date, how many hours you can study per day, and how many days before each exam to keep free for revision.
4. Your plan – Get a day-by-day plan where topics are fitted in before their exam, earliest exam first, without going over your daily limit. Then:
   📅 Add it to your Calendar with one click (your existing notes on those days are kept), or
   ⬇ Download it as a PDF.

🧑‍🏫 Study Tutor:
Upload your own study material (PDF, PPTX, or TXT) and:
💬 Ask doubts – the tutor answers using only your uploaded material, not the internet, so the answers match what you're actually studying.
📝 Quiz yourself – generate 3–10 multiple-choice questions from your material, with explanations and a score.

🛠 Tech Stack:
Flask + SQLAlchemy
PostgreSQL (Neon)
HTML/CSS (custom) (except for one Bootstrap modal for confirming post deletion)
Google Gemini API for reading syllabi, the tutor, and quizzes
PyMuPDF + python-pptx for reading PDFs and slides
Gunicorn + Render for deployment
Brevo API for password reset emails


website (deployed through render):
https://sapience-study-app.onrender.com
