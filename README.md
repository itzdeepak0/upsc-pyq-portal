# UPSC Prelims Interactive PYQ & Test Portal
**Stack:** Python 3.14 • Django 6.1 • SQLite3 • Tailwind CSS • Lucide Icons

This application extracts UPSC Prelims Test Series PDFs (such as the KingMakers IAS Academy GMT series) into a structured **SQLite database** and provides a modern, responsive, interactive web application for test prep.

---

## 🚀 Key Features

1. **Structured SQLite Database (`db.sqlite3`)**:
   - **502 pre-loaded questions** parsed directly from the May 2026 and June 2026 test series.
   - Clean relational schema: `Question`, `Subject`, `Source`, `ExamSession`, `ExamResponse`.
   - Captures original question stem, multi-statement lists, 4 options (a-d), correct answer key, detailed point-by-point explanations, value additions, and current affairs triggers ("In NEWS").

2. **Interactive Practice / Study Mode (`/practice/`)**:
   - One-question-per-card distraction-free study layout.
   - **Instant Feedback:** Clicking any option immediately verifies correctness:
     - 🟢 Correct option glows emerald with a checkmark (+2.0 Marks).
     - 🔴 Incorrect user selection glows rose with an X (-0.66 Marks) and highlights the correct answer in emerald.
   - **Auto-revealing Explanation Drawer:**
     - 📖 *Detailed Explanation:* Statement-by-statement logical proof.
     - 💡 *Value Addition:* Extra facts, tables, and constitutional provisions.
     - 📰 *In NEWS:* Current affairs trigger behind the question.
   - Real-time bookmarking with 1-click save.

3. **Timed UPSC Mock Exam Simulation (`/exam/setup/`)**:
   - Customize test: select specific test series, specific subject (e.g., Polity, Economy), or full syllabus.
   - Choose question count (25, 50, 100, 200) and duration (30, 60, 120 mins).
   - Authentic examination palette:
     - 🟢 Answered
     - 🔴 Visited & Unanswered
     - 🟣 Marked for Review
     - ⚪ Not Visited
   - Real-time countdown timer with auto-submit.
   - **Comprehensive Results & Analysis Dashboard:**
     - UPSC scoring (+2.0 for correct, -0.66 for incorrect).
     - Total Net Marks, Accuracy percentage, Speed.
     - Subject-wise strength/weakness breakdown table.
     - Filterable solution review sheet (Review All, Review Incorrect, Review Skipped).

4. **Monthly Editions Manager (`/editions/`)**:
   - Overview of all monthly test series editions (May 2026, June 2026, July 2026, etc.).
   - 1-click **Download JSON Backup** for any month.
   - 1-click **Launch Full Mock Test** for that month.
   - Delete/re-index controls.

---

## 📥 3 Easy Ways to Add Future PDFs (Upcoming Months)

Whenever you get upcoming test series PDFs (e.g. July 2026, August 2026, etc.), you can add them using any of these 3 ways:

### Option 1: Web Interface with Month & Year Picker (`/upload/`)
1. Open the website and click **"+ Add Month PDF"** in the top navigation bar.
2. Select the month (e.g., *July*, *August*, or *Auto-Detect*).
3. Select your PDF file and click **Parse & Import Questions into SQLite**.
4. The system automatically extracts all questions, classifies their subjects, saves a JSON backup, and updates your database immediately!

### Option 2: Drag & Drop onto `add_pdf.bat` (Desktop Shortcut)
1. In Windows File Explorer, find `add_pdf.bat` in the project directory.
2. **Drag and drop** your new PDF file directly onto `add_pdf.bat`.
3. It will automatically parse all questions into SQLite and show a completion banner!

### Option 3: Hot Folder (`incoming_pdfs/`)
1. Copy or drop any upcoming PDFs into the `incoming_pdfs/` folder.
2. Click **"Scan & Import Pending PDFs"** on the `/upload/` webpage or run:
   ```bash
   python manage.py scan_incoming
   ```

---

## 🏃 Quick Start

### 1. Launch the Server
Double-click `run.bat` or run:
```bash
python manage.py runserver
```
Then open your browser at **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**.

### 2. Django Admin Panel
Access the backend admin panel at **[http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)**:
- **Username:** `admin`
- **Password:** `admin123`
