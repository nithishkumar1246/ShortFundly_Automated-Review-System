# 🎥 Video Demo Recording Guide (For 6:00 PM Submission)

This guide provides an exact, step-by-step walkthrough to record your screen demo video matching 100% of the mentor's evaluation criteria.

---

## ⏱️ Target Duration
**2 to 3 minutes**

---

## 🎬 Step-by-Step Recording Script

### Phase 1: Onboarding & DOJ Verification (0:00 - 0:35)
1. **Show the Web Interface**:
   - Open [http://localhost:8000](http://localhost:8000).
   - Point out the active intern **Aarav Sharma**, his verified **Date of Joining (DOJ: 2026-10-01)**, and the **Dynamic Review Roadmap** on the left panel showing all scheduled milestones spaced with strictly enforced 12-day intervals.
2. **Show Task Briefing**:
   - Highlight the bot's onboarding briefing: Project Scope, Core Objectives, Technology Stack, and Strict Submission Guidelines.
   - Click **"Listen Briefing"** (top right) to demonstrate the automated Text-to-Speech verbal briefing.
3. **Dispatch Review 1 Invitation Email (Mentor Instruction 1)**:
   - Click the button **"Send Review 1 Invite"** (or in the chat).
   - Show the confirmation: *Review 1 Invitation Email dispatched with First Review Date, Meeting Time, and Google Meet Link*.
   - Click the **"Email Dispatch Logs"** tab at the top to preview the delivered invitation email with the Google Meet link.

---

### Phase 2: Candidate Submission & AI Evaluation (0:35 - 1:30)
1. **Return to "Intern Bot & Portal" Tab**.
2. **Method A - GitHub URL Submission**:
   - Click the quick chip **"Autofill GitHub URL"** (or paste `https://github.com/aarav-sharma/cloud-microservices-ai`) and hit **Send**.
   - Show the live indicator: *AI Evaluation Engine inspecting repository & verifying code AST...*
3. **Show the 4 Evaluation Pillars in Chat**:
   - **Score Banner**: e.g., `86/100 • PASSED`
   - **Dual Dispatch Notice**: Confirms feedback was simultaneously emailed to the candidate.
   - **Pillar 1: Completed Modules** (*evlo mudichurukanga*): e.g. Repository Scaffolding (100%), Dependency Config (95%), Data Schemas (85%).
   - **Pillar 2: Code Corrections** (*enna enna corrections iruku*): e.g. `[MEDIUM] config/settings.py` - hardcoded DB URI fallback fix.
   - **Pillar 3: Missing Modules** (*enna enna modules miss aayiruku*): e.g. Pre-commit hooks, `/healthz` probe.
   - **Pillar 4: Modules to Add for Next Stage** (*enna enna modules add pannanum*): e.g. REST API Controllers, Relational ORM schemas.
4. **Verbal Feedback Readout**:
   - Click the **"Listen"** button on the score banner to show the bot explaining the evaluation aloud.
5. **Next Review Milestone Attached**:
   - Point out the Next Review card: **Review Stage 2**, scheduled date (12-day gap), time, and official **Google Meet link**.

---

### Phase 3: Document / File Upload Support (1:30 - 2:00)
1. **Method B - Document / Code Archive Upload (Mentor Instruction 2)**:
   - Point out the **Paperclip (📎)** attachment button next to the input field.
   - Click the quick chip **"Quick Upload Code Archive (.zip)"** (or attach any `.zip` / `.py` file).
   - Notice the selected file preview bar: `retail_monitoring_submission_v1.zip (142.5 KB)`.
   - Click **"Evaluate Document"**.
   - The bot evaluates the uploaded archive, grades Stage 2 (`89% PASSED`), and schedules **Review Stage 3** with a fresh Google Meet link!

---

### Phase 4: Rolling Loop to Graduation & Certificate (2:00 - 2:30)
1. **Complete Stage 3 & Stage 4**:
   - Submit the remaining stages to show the continuous rolling loop.
   - On Stage 4 completion: **Confetti celebration triggers!**
   - The bot announces: *ALL REVIEW STAGES COMPLETED with DISTINCTION (95/100)*.
2. **Display Official Certificate**:
   - Click **"View Official Internship Certificate"**.
   - Show the high-resolution certificate with Candidate Name, Certificate ID, Distinction Grade, Official Seal, and Print/PDF support!

---

### Phase 5: Verification of Dual Email Logs & Admin Dashboard (2:30 - 3:00)
1. **Email Dispatch Logs Tab**:
   - Switch to **"Email Dispatch Logs"**.
   - Show the list of all dispatched emails: the initial **Review 1 Invitation Email** and each subsequent **Stage Review Feedback Email**.
   - Click on any email to show the fully formatted HTML email in the reader with the next Google Meet invitation.
2. **Admin Dashboard Tab**:
   - Switch to **"Admin Dashboard"**.
   - Show the KPIs (Total Interns, Completed Reviews, Avg Score, Total Emails).
   - Show the Company Master Task specification and Dynamic Scheduling parameters (flexible $n$ reviews, 10–15 day gap).
   - Show the Intern Database table with the Reset button for repeatable testing.

---

## 📤 Submission Checklist (Before 6:00 PM)

1. [ ] Stop recording and save the video file (e.g., `Intern_Review_System_Demo.mp4`).
2. [ ] Upload the video file to your **Google Drive**.
3. [ ] Set sharing permissions: **"Anyone with the link can view"**.
4. [ ] Push your project to your GitHub:
   ```cmd
   git add .
   git commit -m "feat: Automated Intern Review, Allocation & Evaluation System"
   git remote add origin <your-github-repo-url>
   git branch -M main
   git push -u origin main
   ```
5. [ ] Open the **College Excel Sheet** and paste:
   - **GitHub Repo Link**
   - **Google Drive Video Link**
