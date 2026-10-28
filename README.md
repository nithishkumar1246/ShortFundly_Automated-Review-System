# 🤖 Automated Intern Review, Task Allocation & Evaluation System

An enterprise-grade, autonomous AI review and evaluation engine designed for engineering internship lifecycle management. The system automates onboarding task allocation, dynamic N-stage review scheduling with strict 10–15 day intervals, code & document evaluation against corporate master rubrics, verbal AI critique synthesis, and dual dispatch notifications (interactive chat + corporate email with Google Meet invitations).

---

## 🎯 Alignment with Core Evaluation Requirements

| Evaluation Requirement | System Implementation |
| :--- | :--- |
| **1. Date of Joining (DOJ) & Verification** | Interns are verified by name or ID. System validates their registered profile, confirms Date of Joining (DOJ), and loads the active review roadmap. |
| **2. Post-Explanation Call Invitation Email** | Dispatches official **Review 1 Invitation Email** containing the confirmed First Review Date, Meeting Time, Google Meet link, and assigned project scope. |
| **3. Review Meeting Link & Submission** | Interns join the generated Google Meet link (`meet.google.com/xxx-yyyy-zzz`) and submit completed work via **GitHub Repository URL** or **Task Document / Code Archive (.zip, .pdf, .py)**. |
| **4. AI Evaluation Engine (4 Pillars)** | Compares submission against Company Master Rubric and generates:<br>• **Completed Modules** (*evlo mudichurukanga*) with fulfillment %<br>• **Code Corrections** (*enna enna corrections iruku*) with severity & refactoring tips<br>• **Missing Components** (*enna enna modules miss aayiruku*)<br>• **Modules to Add** (*enna enna modules add pannanum*) for the next milestone. |
| **5. Verbal Feedback Explanation** | Intern can listen to the AI critique aloud using the built-in Text-to-Speech (TTS) engine. |
| **6. Dual Dispatch & Next Milestone Schedule** | Evaluation report is displayed in chat and simultaneously emailed to the candidate with the **Next Review Date (10–15 day gap)**, Time, and Google Meet link. |
| **7. Continuous Rolling Loop & Graduation** | Repeats across Stage 1 &rarr; Stage 2 &rarr; Stage 3 &rarr; Stage 4 (or Stage $N$). Upon final stage, generates an official **Certificate of Merit & Completion**. |

---

## 🚀 Quick Start (Run Locally)

### Prerequisites
- **Python 3.10+** ([python.org](https://www.python.org/downloads/))

---

### Option 1: 1-Click Launch (Windows)
Double-click `start.bat` in the project root:
```cmd
.\start.bat
```

---

### Option 2: Terminal / Command Prompt
1. Navigate to the project directory:
   ```bash
   cd "e:\Automated review system"
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch server:
   ```bash
   python run.py
   ```

4. Open in your browser:
   - 🌐 **Web Interface**: [http://localhost:8000](http://localhost:8000)
   - 📑 **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - 🩺 **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🧪 Automated End-to-End Test

To test the entire pipeline (verification, invite dispatch, GitHub evaluation, document upload evaluation, stage progression, email logs, and reset):
```bash
python backend/test_pipeline.py
```

---

## 📁 System Architecture

```text
Automated review system/
├── backend/
│   ├── app.py              # FastAPI application & REST endpoints
│   ├── database.py         # SQLite schema, migrations & DB connections
│   ├── ai_evaluator.py     # AI evaluation engine (code AST & document inspector)
│   ├── scheduler.py        # Dynamic N-review scheduler (10-15 day gaps & Google Meet)
│   ├── email_service.py    # Dual dispatch HTML email generator & logger
│   ├── mock_data.py        # Seed dataset (interns, master tasks, schedules)
│   └── test_pipeline.py    # Integration test suite
├── frontend/
│   ├── index.html          # Responsive dark-mode portal UI (Tailwind & Lucide)
│   ├── app.js              # State management, TTS speech synthesis, chat & upload logic
│   └── styles.css          # Animations & print certificate styles
├── run.py                  # Server bootstrap entry point
├── start.bat               # Windows 1-click launcher
├── requirements.txt        # Python dependency manifest
├── DEMO_WALKTHROUGH.md     # Step-by-step video demonstration guide
└── README.md               # Project documentation
```

---
