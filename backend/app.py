import os
import io
import json
import asyncio
import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Body, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from database import get_connection, init_db
from scheduler import calculate_review_schedule
from ai_evaluator import evaluate_submission, parse_github_url, inspect_uploaded_document
from email_service import dispatch_evaluation_email, dispatch_onboarding_invitation_email
from mock_data import seed_initial_data

# Ensure DB is initialized and seeded
init_db()
seed_initial_data()

app = FastAPI(
    title="Automated Intern Review, Task Allocation & Evaluation System",
    description="Enterprise automated AI review bot, dynamic N-review scheduler, and evaluation engine.",
    version="2.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class VerifyInternRequest(BaseModel):
    query: str = Field(..., description="Intern Name or Email or Intern ID")

class RegisterInternRequest(BaseModel):
    name: str
    email: str
    role: str = "Software Engineering Intern"
    department: str = "Cloud & AI Platforms"
    doj: Optional[str] = None
    mentor_name: str = "Engineering Lead"
    mentor_email: str = "mentor@enterprise.io"
    total_reviews: int = 4
    gap_days: int = 12

class MasterTaskUpdateRequest(BaseModel):
    title: str
    project_scope: str
    objectives: str
    tech_stack: str
    submission_rules: str
    review_requirements: str

class SubmitReviewRequest(BaseModel):
    intern_id: str
    github_url: str

class UpdateSettingsRequest(BaseModel):
    company_name: Optional[str] = None
    default_total_reviews: Optional[int] = None
    default_gap_days: Optional[int] = None


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Automated Intern Review System", "timestamp": datetime.datetime.now().isoformat()}


@app.post("/api/interns/verify")
def verify_intern(req: VerifyInternRequest):
    """
    1. INITIALIZATION & DATE OF DOJ:
    The intern enters their name or identifier. System verifies against database
    and officially assigns/displays their Date of Joining (DOJ).
    """
    conn = get_connection()
    cursor = conn.cursor()
    search = req.query.strip().lower()

    cursor.execute("""
    SELECT * FROM interns 
    WHERE LOWER(name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(intern_id) = ?
    LIMIT 1
    """, (f"%{search}%", f"%{search}%", search))
    
    row = cursor.fetchone()
    
    if not row:
        # If not found, check if query contains a plausible name to suggest registration or auto-create demo profile
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Intern record not found for query '{req.query}'. You can register as a new intern or use sample names like 'Aarav Sharma', 'Priya Patel', or 'Marcus Vance'."
        )

    intern = dict(row)
    
    # Fetch active task details
    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    task_row = cursor.fetchone()
    task_details = dict(task_row) if task_row else None

    # Fetch review schedule
    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? ORDER BY stage_number ASC", (intern["intern_id"],))
    schedule_rows = cursor.fetchall()
    schedules = [dict(s) for s in schedule_rows]

    # Auto-dispatch initial Stage 1 invitation email if no email exists yet for this intern
    cursor.execute("SELECT COUNT(*) FROM email_logs WHERE intern_id = ?", (intern["intern_id"],))
    email_count = cursor.fetchone()[0]
    if email_count == 0 and schedules and task_details:
        dispatch_onboarding_invitation_email(
            intern_id=intern["intern_id"],
            intern_name=intern["name"],
            recipient_email=intern["email"],
            doj=intern["doj"],
            first_review=schedules[0],
            master_task=task_details
        )

    conn.close()
    
    return {
        "verified": True,
        "message": f"Welcome back, {intern['name']}! Your official Date of Joining (DOJ) is verified as {intern['doj']}.",
        "intern": intern,
        "assigned_task": task_details,
        "review_schedule": schedules
    }


@app.post("/api/interns/register")
def register_intern(req: RegisterInternRequest):
    """Registers a new intern and dynamically schedules N reviews with strict 10-15 day gaps starting from DOJ."""
    conn = get_connection()
    cursor = conn.cursor()

    # Generate intern ID
    cursor.execute("SELECT COUNT(*) FROM interns")
    count = cursor.fetchone()[0] + 1
    intern_id = f"INT-{100 + count}"

    # DOJ defaults to today if not provided
    doj_str = req.doj if req.doj else datetime.date.today().strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Gap strictly clamped to 10-15
    gap = max(10, min(15, req.gap_days))

    try:
        cursor.execute("""
        INSERT INTO interns (
            intern_id, name, email, role, department, doj, mentor_name, mentor_email, current_review_stage, total_reviews, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intern_id, req.name, req.email, req.role, req.department,
            doj_str, req.mentor_name, req.mentor_email, 1, req.total_reviews, "ACTIVE", now_str
        ))

        # Dynamically compute review schedule
        schedule = calculate_review_schedule(doj_str, total_reviews=req.total_reviews, preferred_gap_days=gap)
        for stage in schedule:
            cursor.execute("""
            INSERT INTO review_schedules (
                intern_id, stage_number, stage_name, scheduled_date, gap_days, meeting_link, meeting_time, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intern_id, stage["stage_number"], stage["stage_name"], stage["scheduled_date"],
                stage["gap_days"], stage["meeting_link"], stage["meeting_time"], stage["status"], now_str
            ))

        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    # Fetch created intern
    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    intern = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? ORDER BY stage_number ASC", (intern_id,))
    schedules = [dict(s) for s in cursor.fetchall()]

    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    task_row = cursor.fetchone()
    task_details = dict(task_row) if task_row else None

    # Auto-dispatch initial Review 1 invitation email
    if schedules and task_details:
        dispatch_onboarding_invitation_email(
            intern_id=intern_id,
            intern_name=req.name,
            recipient_email=req.email,
            doj=doj_str,
            first_review=schedules[0],
            master_task=task_details
        )

    conn.close()

    return {
        "verified": True,
        "message": f"Intern {intern['name']} registered successfully. Assigned DOJ: {intern['doj']}.",
        "intern": intern,
        "assigned_task": task_details,
        "review_schedule": schedules
    }


@app.post("/api/interns/{intern_id}/send-invitation")
def send_onboarding_invitation(intern_id: str):
    """Explicitly triggers or re-dispatches the official Review 1 Invitation Email post explanation call."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")
    intern = dict(row)

    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    task_row = cursor.fetchone()
    task = dict(task_row) if task_row else {}

    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? AND stage_number = 1", (intern_id,))
    first_review_row = cursor.fetchone()
    if not first_review_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Review 1 schedule not found")
    first_review = dict(first_review_row)
    conn.close()

    dispatch_res = dispatch_onboarding_invitation_email(
        intern_id=intern["intern_id"],
        intern_name=intern["name"],
        recipient_email=intern["email"],
        doj=intern["doj"],
        first_review=first_review,
        master_task=task
    )
    return {
        "success": True,
        "message": f"Review 1 invitation email successfully dispatched to {intern['email']}.",
        "dispatch": dispatch_res
    }


@app.get("/api/interns")
def list_interns():
    """Lists all interns for admin dashboard oversight."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interns ORDER BY id DESC")
    interns = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"interns": interns, "count": len(interns)}


@app.get("/api/interns/{intern_id}")
def get_intern_profile(intern_id: str):
    """Retrieves full intern profile, reviews, and evaluation history."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")
    
    intern = dict(row)

    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? ORDER BY stage_number ASC", (intern_id,))
    schedules = [dict(s) for s in cursor.fetchall()]

    cursor.execute("SELECT * FROM evaluations WHERE intern_id = ? ORDER BY stage_number ASC", (intern_id,))
    evaluations = []
    for ev in cursor.fetchall():
        item = dict(ev)
        item["completed_modules"] = json.loads(item["completed_modules"])
        item["code_corrections"] = json.loads(item["code_corrections"])
        item["missing_components"] = json.loads(item["missing_components"])
        item["modules_to_add"] = json.loads(item.get("modules_to_add") or "[]")
        evaluations.append(item)

    conn.close()
    return {
        "intern": intern,
        "review_schedule": schedules,
        "evaluations": evaluations
    }


@app.get("/api/master-task")
def get_master_task():
    """
    2. TASK ALLOCATION & BRIEFING:
    Retrieves the company-uploaded master task details and project scope.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No active master task found")
    return {"master_task": dict(row)}


@app.post("/api/master-task")
def update_master_task(req: MasterTaskUpdateRequest):
    """Admin updates or uploads the master task and review criteria."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO master_tasks (
        title, project_scope, objectives, tech_stack, submission_rules, review_requirements, is_active, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        req.title, req.project_scope, req.objectives, req.tech_stack, req.submission_rules, req.review_requirements, now_str
    ))

    new_id = cursor.lastrowid
    # Deactivate older tasks
    cursor.execute("UPDATE master_tasks SET is_active = 0 WHERE id != ?", (new_id,))
    conn.commit()
    conn.close()

    return {"message": "Master task specification successfully uploaded and activated.", "task_id": new_id}


def _execute_review_evaluation(
    intern_id: str,
    submission_target: str,
    submission_type: str = "GITHUB_URL",
    document_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Shared core evaluation pipeline for GitHub URLs and uploaded task documents/archives."""
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch intern
    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    intern_row = cursor.fetchone()
    if not intern_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")
    intern = dict(intern_row)

    current_stage = intern["current_review_stage"]
    total_reviews = intern["total_reviews"]

    # Fetch current stage schedule
    cursor.execute("""
    SELECT * FROM review_schedules 
    WHERE intern_id = ? AND stage_number = ?
    """, (intern_id, current_stage))
    current_schedule_row = cursor.fetchone()
    if not current_schedule_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Active review stage schedule not found")
    current_schedule = dict(current_schedule_row)

    # Fetch active master task
    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    task_row = cursor.fetchone()
    master_task = dict(task_row) if task_row else {}

    # Run AI Evaluation Engine
    eval_result = evaluate_submission(
        target=submission_target,
        stage_number=current_stage,
        stage_name=current_schedule.get("stage_name", f"Review {current_stage}"),
        master_task=master_task,
        submission_type=submission_type,
        document_meta=document_meta
    )

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Record evaluation (with modules_to_add and submission_type)
    cursor.execute("""
    INSERT INTO evaluations (
        intern_id, stage_number, github_url, submission_type, submission_title, score, verdict,
        completed_modules, code_corrections, missing_components, modules_to_add, detailed_summary, evaluated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intern_id,
        current_stage,
        submission_target,
        submission_type,
        document_meta.get("filename", submission_target) if document_meta else submission_target,
        eval_result["score"],
        eval_result["verdict"],
        json.dumps(eval_result["completed_modules"]),
        json.dumps(eval_result["code_corrections"]),
        json.dumps(eval_result["missing_components"]),
        json.dumps(eval_result.get("modules_to_add", [])),
        eval_result["detailed_summary"],
        now_str
    ))

    # Update current review schedule row
    cursor.execute("""
    UPDATE review_schedules
    SET status = 'COMPLETED', submission_github_url = ?, submitted_at = ?, evaluation_score = ?
    WHERE intern_id = ? AND stage_number = ?
    """, (submission_target, now_str, eval_result["score"], intern_id, current_stage))

    # Rolling loop logic
    is_final_stage = (current_stage >= total_reviews)
    next_review = None

    if not is_final_stage:
        next_stage_num = current_stage + 1
        # Fetch next review schedule
        cursor.execute("""
        SELECT * FROM review_schedules 
        WHERE intern_id = ? AND stage_number = ?
        """, (intern_id, next_stage_num))
        next_row = cursor.fetchone()
        if next_row:
            next_review = dict(next_row)
            # Set next review to ACTIVE
            cursor.execute("""
            UPDATE review_schedules
            SET status = 'ACTIVE'
            WHERE intern_id = ? AND stage_number = ?
            """, (intern_id, next_stage_num))

        # Advance intern's current stage
        cursor.execute("""
        UPDATE interns 
        SET current_review_stage = ?
        WHERE intern_id = ?
        """, (next_stage_num, intern_id))
    else:
        # Intern completed all N review stages!
        cursor.execute("""
        UPDATE interns 
        SET status = 'COMPLETED'
        WHERE intern_id = ?
        """, (intern_id,))

    conn.commit()

    # DUAL DISPATCH: Dispatch detailed feedback email with Next Review scheduling attached
    email_dispatch_res = dispatch_evaluation_email(
        intern_id=intern["intern_id"],
        intern_name=intern["name"],
        recipient_email=intern["email"],
        evaluation=eval_result,
        next_review=next_review,
        is_final_stage=is_final_stage
    )

    # Fetch updated review schedules
    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? ORDER BY stage_number ASC", (intern_id,))
    updated_schedules = [dict(s) for s in cursor.fetchall()]

    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    updated_intern = dict(cursor.fetchone())

    conn.close()

    return {
        "evaluation": eval_result,
        "is_final_stage": is_final_stage,
        "next_review": next_review,
        "email_dispatch": email_dispatch_res,
        "intern": updated_intern,
        "review_schedule": updated_schedules
    }


@app.post("/api/reviews/submit")
def submit_and_evaluate_review(req: SubmitReviewRequest):
    """
    4. GITHUB SUBMISSION & AI EVALUATION PIPELINE +
    5. DUAL DISPATCH & ROLLING LOOP:
    - Intern submits GitHub repository link.
    """
    url_check = parse_github_url(req.github_url)
    if not url_check["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Please provide a standard GitHub repository link, e.g., 'https://github.com/intern/enterprise-system'."
        )
    return _execute_review_evaluation(
        intern_id=req.intern_id,
        submission_target=req.github_url,
        submission_type="GITHUB_URL"
    )


@app.post("/api/reviews/upload")
async def upload_and_evaluate_review(
    intern_id: str = Form(...),
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None)
):
    """
    4B. DOCUMENT / CODE ARCHIVE SUBMISSION & AI EVALUATION:
    - Intern uploads task document (.pdf, .docx, .zip, .py, .js, .txt, .md).
    - AI Evaluator analyzes file contents and compares against company master spec.
    - Dispatches dual evaluation and advances stage rolling loop.
    """
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    doc_meta = inspect_uploaded_document(file.filename, file_bytes)
    if notes:
        doc_meta["notes"] = notes

    return _execute_review_evaluation(
        intern_id=intern_id,
        submission_target=file.filename,
        submission_type="DOCUMENT_UPLOAD",
        document_meta=doc_meta
    )


@app.get("/api/emails")
def list_emails(intern_id: Optional[str] = None):
    """Retrieve email logs for simulated inbox inspection."""
    conn = get_connection()
    cursor = conn.cursor()
    if intern_id:
        cursor.execute("SELECT * FROM email_logs WHERE intern_id = ? ORDER BY id DESC", (intern_id,))
    else:
        cursor.execute("SELECT * FROM email_logs ORDER BY id DESC")
    emails = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"emails": emails, "count": len(emails)}


@app.post("/api/interns/{intern_id}/reset")
def reset_intern_progress(intern_id: str):
    """Convenience endpoint for live demo/testing: resets intern's review loop back to Stage 1."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    intern_row = cursor.fetchone()
    if not intern_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")
    intern = dict(intern_row)

    # Delete existing schedules, evaluations, emails for this intern
    cursor.execute("DELETE FROM review_schedules WHERE intern_id = ?", (intern_id,))
    cursor.execute("DELETE FROM evaluations WHERE intern_id = ?", (intern_id,))
    cursor.execute("DELETE FROM email_logs WHERE intern_id = ?", (intern_id,))

    # Reset intern status
    cursor.execute("""
    UPDATE interns 
    SET current_review_stage = 1, status = 'ACTIVE'
    WHERE intern_id = ?
    """, (intern_id,))

    # Recalculate schedule starting from DOJ with 12-day gap
    schedule = calculate_review_schedule(intern["doj"], total_reviews=intern["total_reviews"], preferred_gap_days=12)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for stage in schedule:
        cursor.execute("""
        INSERT INTO review_schedules (
            intern_id, stage_number, stage_name, scheduled_date, gap_days, meeting_link, meeting_time, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intern_id, stage["stage_number"], stage["stage_name"], stage["scheduled_date"],
            stage["gap_days"], stage["meeting_link"], stage["meeting_time"], stage["status"], now_str
        ))

    conn.commit()

    cursor.execute("SELECT * FROM interns WHERE intern_id = ?", (intern_id,))
    updated_intern = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM review_schedules WHERE intern_id = ? ORDER BY stage_number ASC", (intern_id,))
    schedules = [dict(s) for s in cursor.fetchall()]

    cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    task_row = cursor.fetchone()
    task_details = dict(task_row) if task_row else None

    # Auto-dispatch initial Review 1 invitation email post reset
    if schedules and task_details:
        dispatch_onboarding_invitation_email(
            intern_id=intern_id,
            intern_name=intern["name"],
            recipient_email=intern["email"],
            doj=intern["doj"],
            first_review=schedules[0],
            master_task=task_details
        )

    conn.close()

    return {
        "message": f"Intern {intern['name']} review cycle reset back to Stage 1.",
        "intern": updated_intern,
        "review_schedule": schedules
    }


@app.get("/api/settings")
def get_settings():
    """Retrieve system configuration settings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return {"settings": settings}


@app.post("/api/settings")
def update_settings(req: UpdateSettingsRequest):
    """Update system settings (total reviews, gap days)."""
    conn = get_connection()
    cursor = conn.cursor()

    if req.company_name:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('company_name', ?)", (req.company_name,))
    if req.default_total_reviews:
        val = str(max(2, min(10, req.default_total_reviews)))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('default_total_reviews', ?)", (val,))
    if req.default_gap_days:
        val = str(max(10, min(15, req.default_gap_days)))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('default_gap_days', ?)", (val,))

    conn.commit()
    conn.close()
    return {"message": "Settings updated successfully."}


class SmtpConfigRequest(BaseModel):
    enabled: bool = True
    host: str = "smtp.gmail.com"
    port: int = 587
    user: str
    password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: str = "Nexus Review AI"


class SmtpTestRequest(BaseModel):
    recipient_email: str


@app.get("/api/smtp/config")
def get_smtp_configuration():
    """Retrieve current SMTP email configuration."""
    from email_service import get_smtp_config
    cfg = get_smtp_config()
    return {
        "enabled": cfg["enabled"],
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "from_email": cfg["from_email"],
        "from_name": cfg["from_name"],
        "has_password": bool(cfg["password"]),
        "use_tls": cfg["use_tls"],
        "use_ssl": cfg["use_ssl"],
        "is_configured": bool(cfg["host"] and cfg["user"] and cfg["password"])
    }


@app.post("/api/smtp/config")
def save_smtp_configuration(req: SmtpConfigRequest):
    """Save SMTP email delivery settings into database.
    
    For Gmail: password must be a 16-character App Password (no spaces),
    NOT the regular account password. Regular passwords will cause
    'Connection unexpectedly closed' errors during authentication.
    """
    host = req.host.strip()

    # Validate Gmail App Password length before saving
    if req.password:
        clean_pw = req.password.strip().replace(" ", "")
        if "gmail" in host.lower() and len(clean_pw) != 16:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Gmail requires a 16-character App Password (you entered {len(clean_pw)} characters). "
                    "Your regular Gmail password will NOT work. "
                    "Steps: 1) Enable 2-Step Verification at myaccount.google.com/security  "
                    "2) Go to myaccount.google.com/apppasswords  "
                    "3) Create an App Password → copy the 16-character code (no spaces) → paste it here."
                )
            )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_enabled', ?)", ("true" if req.enabled else "false",))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_host', ?)", (host,))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_port', ?)", (str(req.port),))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_user', ?)", (req.user.strip(),))
    if req.password:
        # Store App Password without spaces
        clean_pw = req.password.strip().replace(" ", "")
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_password', ?)", (clean_pw,))

    from_email = req.from_email.strip() if req.from_email else req.user.strip()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_from_email', ?)", (from_email,))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_from_name', ?)", (req.from_name.strip(),))

    conn.commit()
    conn.close()

    return {"message": "SMTP configuration saved successfully. Live email delivery activated."}


@app.post("/api/smtp/test")
def test_smtp_delivery(req: SmtpTestRequest):
    """Sends a live test email directly to the provided student / intern email address."""
    from email_service import send_live_smtp_email

    test_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 20px; border-radius: 8px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">Automated Live Email Delivery Verified</h2>
        </div>
        <div style="padding: 20px 0; color: #334155; line-height: 1.6;">
            <p>Hello,</p>
            <p>This is an official automated test transmission from the <strong>Nexus Automated Intern Review & Evaluation System</strong>.</p>
            <p>Your SMTP mail dispatch channel is active and verified! All future review evaluations, completed module feedback, code corrections, and Google Meet schedules will be automatically transmitted to this student inbox.</p>
            <div style="background: #f8fafc; border: 1px solid #cbd5e1; padding: 12px 16px; border-radius: 6px; font-size: 13px; margin: 16px 0;">
                Recipient: <strong>{req.recipient_email}</strong><br/>
                Server Timestamp: <strong>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
            </div>
        </div>
        <div style="border-top: 1px solid #e2e8f0; padding-top: 12px; font-size: 12px; color: #94a3b8; text-align: center;">
            Nexus AI Autonomous Review Platform &bull; Live SMTP Channel
        </div>
    </div>
    """

    res = send_live_smtp_email(
        to_email=req.recipient_email.strip(),
        subject="[Test Verified] Automated Intern Review System Live Email Delivery",
        html_body=test_html
    )

    if not res["sent"]:
        raise HTTPException(
            status_code=400,
            detail=f"Live email dispatch failed: {res.get('error') or res.get('message')}"
        )

    return {
        "success": True,
        "message": f"Live test email sent successfully to {req.recipient_email}!",
        "details": res
    }


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    """
    Neural Text-to-Speech via Microsoft Edge TTS.
    Streams MP3 audio with a natural neural voice (en-US-AriaNeural by default).
    Available voices include: en-US-AriaNeural, en-US-JennyNeural, en-US-GuyNeural,
    en-GB-SoniaNeural, en-IN-NeerjaNeural.
    """
    try:
        import edge_tts

        # Clean the text: strip extra whitespace/newlines for natural pacing
        clean_text = " ".join(req.text.split())

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch
        )

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_buffer.seek(0)
        audio_bytes = audio_buffer.getvalue()

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="TTS generated empty audio. Check voice name or network.")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "no-cache",
                "X-Voice": req.voice
            }
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="edge-tts is not installed. Run: pip install edge-tts"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/api/tts/voices")
async def list_tts_voices():
    """Returns available neural TTS voices with recommended options."""
    return {
        "recommended": [
            {"id": "en-US-AriaNeural", "name": "Aria (US Female – Warm)", "locale": "en-US", "gender": "Female"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US Female – Friendly)", "locale": "en-US", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male – Professional)", "locale": "en-US", "gender": "Male"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female – Crisp)", "locale": "en-GB", "gender": "Female"},
            {"id": "en-IN-NeerjaNeural", "name": "Neerja (Indian Female)", "locale": "en-IN", "gender": "Female"},
            {"id": "en-US-DavisNeural", "name": "Davis (US Male – Casual)", "locale": "en-US", "gender": "Male"},
        ]
    }


# Mount frontend static directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found, please check frontend/index.html"}
