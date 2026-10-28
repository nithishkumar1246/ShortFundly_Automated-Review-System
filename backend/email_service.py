import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, Any, Optional
from database import get_connection

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_smtp_config() -> Dict[str, Any]:
    """Retrieves SMTP configuration from DB settings or environment variables."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'smtp_%'")
    db_settings = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    host = db_settings.get("smtp_host") or os.environ.get("SMTP_HOST", "")
    port_str = db_settings.get("smtp_port") or os.environ.get("SMTP_PORT", "587")
    try:
        port = int(port_str)
    except Exception:
        port = 587

    user = db_settings.get("smtp_user") or os.environ.get("SMTP_USER", "")
    password = db_settings.get("smtp_password") or os.environ.get("SMTP_PASSWORD", "")
    from_email = db_settings.get("smtp_from_email") or os.environ.get("SMTP_FROM_EMAIL", user)
    from_name = db_settings.get("smtp_from_name") or os.environ.get("SMTP_FROM_NAME", "Nexus Review AI")
    enabled_val = db_settings.get("smtp_enabled") or os.environ.get("SMTP_ENABLED", "")

    # Auto-enable if host and user/password are provided unless explicitly disabled
    is_enabled = enabled_val.lower() in ("true", "1", "yes") if enabled_val else bool(host and user)

    return {
        "enabled": is_enabled,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
        "from_name": from_name,
        "use_tls": port == 587 or db_settings.get("smtp_use_tls", "true").lower() in ("true", "1"),
        "use_ssl": port == 465 or db_settings.get("smtp_use_ssl", "false").lower() in ("true", "1")
    }

def _classify_smtp_error(e: Exception, host: str, password: str) -> str:
    """Produce a human-readable, actionable SMTP error message."""
    err = str(e).lower()
    raw = str(e)

    # Authentication failure - most common: wrong password or App Password not used
    if any(k in err for k in ("535", "534", "authentication", "username and password", "bad credentials")):
        if "gmail" in host:
            return (
                "Gmail authentication failed. Your password must be a 16-character Google App Password "
                "(not your regular account password). "
                "Go to myaccount.google.com/apppasswords > enable 2-Step Verification > create an App Password."
            )
        return f"SMTP authentication rejected by {host}. Check your username and password. Raw error: {raw}"

    # Connection reset - also triggered by Gmail when a regular password is used before AUTH
    if any(k in err for k in ("connection unexpectedly closed", "10053", "10054", "eof", "broken pipe", "connection reset")):
        if "gmail" in host:
            pw_len = len(password.replace(" ", ""))
            if pw_len != 16:
                return (
                    f"Gmail forcibly closed the connection (this almost always means the password is wrong). "
                    f"Your saved password is {pw_len} characters - Gmail App Passwords are exactly 16 characters "
                    f"with no spaces. Go to myaccount.google.com/apppasswords to generate one."
                )
            return (
                "Gmail closed the connection. Ensure 2-Step Verification is ON and you are using an App Password "
                "(16 chars, no spaces) - not your regular Gmail password."
            )
        return f"SMTP server closed the connection unexpectedly. Check host/port settings. Raw: {raw}"

    # Network / DNS
    if any(k in err for k in ("network is unreachable", "name or service not known",
                               "getaddrinfo", "nodename nor servname", "11001", "11004")):
        return f"Cannot reach SMTP server '{host}'. Check your internet connection and hostname."

    # Timeout
    if "timed out" in err or "timeout" in err:
        return f"Connection to {host} timed out. The port may be blocked by your firewall or antivirus."

    # TLS / SSL
    if any(k in err for k in ("ssl", "tls", "certificate")):
        return f"TLS/SSL handshake error with {host}. Try switching port (587 or 465) or toggling TLS."

    return raw


def send_live_smtp_email(
    to_email: str,
    subject: str,
    html_body: str
) -> Dict[str, Any]:
    """
    Sends an actual live email via SMTP directly to the student/intern.
    Diagnoses auth failures and returns an actionable error message.
    Falls back to local simulation if SMTP is not configured.
    """
    cfg = get_smtp_config()

    if not cfg["enabled"] or not cfg["host"] or not cfg["user"]:
        return {
            "sent": False,
            "method": "SIMULATED",
            "message": "Live SMTP not configured yet. Email logged to simulated inbox."
        }

    # Pre-flight: warn about likely wrong password before hitting the wire
    password = cfg["password"] or ""
    if "gmail" in cfg["host"].lower():
        clean_pw = password.replace(" ", "")
        if len(clean_pw) != 16:
            friendly = (
                f"Gmail requires a 16-character App Password (yours is {len(clean_pw)} chars). "
                "Go to myaccount.google.com/apppasswords > create an App Password > paste the 16-char code here."
            )
            print(f"[SMTP PRE-CHECK] {friendly}")
            return {
                "sent": False,
                "method": "SMTP_ERROR",
                "error": friendly,
                "message": friendly
            }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((cfg["from_name"], cfg["from_email"]))
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if cfg["use_ssl"] or cfg["port"] == 465:
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15)
            server.ehlo()
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
            server.ehlo()
            if cfg["use_tls"]:
                server.starttls()
                server.ehlo()  # Re-identify after STARTTLS — required by Gmail

        if cfg["user"] and password:
            server.login(cfg["user"], password)

        server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        server.quit()

        print(f"[LIVE EMAIL SENT] Successfully delivered to {to_email} via {cfg['host']}:{cfg['port']}")
        return {
            "sent": True,
            "method": "SMTP",
            "host": cfg["host"],
            "recipient": to_email,
            "message": f"Live email successfully sent to {to_email}"
        }

    except Exception as e:
        friendly_err = _classify_smtp_error(e, cfg["host"], password)
        print(f"[LIVE EMAIL ERROR] {friendly_err}")
        return {
            "sent": False,
            "method": "SMTP_ERROR",
            "error": friendly_err,
            "message": f"SMTP delivery failed: {friendly_err}"
        }

def generate_evaluation_email_html(
    intern_name: str,
    intern_id: str,
    recipient_email: str,
    evaluation: Dict[str, Any],
    next_review: Optional[Dict[str, Any]] = None,
    is_final_stage: bool = False
) -> str:
    """Generates an HTML email for the dual dispatch review feedback system."""
    score = evaluation.get("score", 0)
    verdict = evaluation.get("verdict", "PASSED")
    stage_number = evaluation.get("stage_number", 1)
    stage_name = evaluation.get("stage_name", f"Review {stage_number}")
    summary = evaluation.get("detailed_summary", "")
    
    # Verdict color pill
    verdict_color = "#10b981" if score >= 85 else ("#f59e0b" if score >= 70 else "#ef4444")
    
    # Modules HTML
    modules_html = ""
    for mod in evaluation.get("completed_modules", []):
        modules_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 10px; font-weight: 600; color: #1e293b;">{mod.get('module')}</td>
            <td style="padding: 12px 10px; color: #10b981; font-weight: bold;">
                <span style="background-color: #ecfdf5; color: #065f46; padding: 3px 8px; border-radius: 9999px; font-size: 11px;">
                    {mod.get('fulfillment_pct', 100)}% Verified
                </span>
            </td>
            <td style="padding: 12px 10px; color: #475569; font-size: 13px;">{mod.get('evidence')}</td>
        </tr>
        """
        
    # Code corrections HTML
    corrections_html = ""
    for corr in evaluation.get("code_corrections", []):
        sev_color = "#ef4444" if corr.get("severity") == "HIGH" else "#f59e0b"
        corrections_html += f"""
        <div style="background-color: #fff1f2; border-left: 4px solid {sev_color}; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px;">
            <div style="font-size: 12px; font-weight: bold; color: {sev_color}; text-transform: uppercase;">
                [{corr.get('severity')}] File: {corr.get('file')}
            </div>
            <div style="font-size: 14px; color: #1e293b; margin: 4px 0;">{corr.get('issue')}</div>
            <div style="font-size: 13px; color: #047857; background: #ecfdf5; padding: 6px 10px; border-radius: 4px; margin-top: 4px;">
                <strong>Action:</strong> {corr.get('recommendation')}
            </div>
        </div>
        """

    # Missing components HTML
    missing_html = ""
    for miss in evaluation.get("missing_components", []):
        missing_html += f"""
        <li style="margin-bottom: 8px; color: #334155; font-size: 13px;">
            <strong>{miss.get('item')}:</strong> {miss.get('impact')}
            <br/><span style="color: #6366f1;">&rarr; Plan: {miss.get('action_required')}</span>
        </li>
        """

    # Modules to Add HTML ("enna enna modules add pannanum")
    modules_to_add_html = ""
    for add_mod in evaluation.get("modules_to_add", []):
        prio = add_mod.get("priority", "HIGH")
        prio_color = "#3b82f6" if prio == "HIGH" else ("#10b981" if prio == "COMPLETED" else "#8b5cf6")
        modules_to_add_html += f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid {prio_color}; padding: 12px 16px; margin-bottom: 10px; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: bold; color: #0f172a;">{add_mod.get('module_name')}</span>
                <span style="background-color: #eff6ff; color: {prio_color}; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 10px; text-transform: uppercase;">
                    {prio} Priority
                </span>
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">{add_mod.get('description')}</div>
            <div style="font-size: 12px; color: #2563eb; font-weight: 500;">
                &bull; Next Milestone Action: {add_mod.get('action')}
            </div>
        </div>
        """

    # Next Review Section or Final Completion
    next_review_block = ""
    if next_review and not is_final_stage:
        next_review_block = f"""
        <div style="margin-top: 30px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: #ffffff; padding: 24px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(49, 46, 129, 0.4);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
                <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;">
                    NEXT MILESTONE ASSIGNMENT
                </span>
                <span style="background: #10b981; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                    {next_review.get('gap_days', 12)}-Day Gap Adherence
                </span>
            </div>
            <h3 style="margin: 0 0 10px 0; font-size: 20px; color: #ffffff;">{next_review.get('stage_name', 'Next Review Stage')}</h3>
            <p style="margin: 0 0 16px 0; color: #cbd5e1; font-size: 14px;">
                Please integrate the code corrections highlighted above before our next sync. Your official meeting invitation is confirmed below:
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px; color: #e2e8f0; font-size: 14px;">
                <tr>
                    <td style="padding: 6px 0; width: 140px; color: #94a3b8;">📅 Scheduled Date:</td>
                    <td style="padding: 6px 0; font-weight: bold; color: #38bdf8;">{next_review.get('scheduled_date')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #94a3b8;">⏰ Meeting Time:</td>
                    <td style="padding: 6px 0; font-weight: bold; color: #f8fafc;">{next_review.get('meeting_time', '11:00 AM IST')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #94a3b8;">🔗 Google Meet:</td>
                    <td style="padding: 6px 0;">
                        <a href="{next_review.get('meeting_link')}" target="_blank" style="color: #67e8f9; text-decoration: underline; font-weight: bold;">
                            {next_review.get('meeting_link')}
                        </a>
                    </td>
                </tr>
            </table>
            <div style="text-align: center; margin-top: 15px;">
                <a href="{next_review.get('meeting_link')}" target="_blank" style="display: inline-block; background-color: #3b82f6; color: #ffffff; font-weight: bold; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);">
                    Add to Calendar & Test Meet Link &rarr;
                </a>
            </div>
        </div>
        """
    else:
        next_review_block = f"""
        <div style="margin-top: 30px; background: linear-gradient(135deg, #064e3b 0%, #047857 100%); color: #ffffff; padding: 24px; border-radius: 12px; text-align: center;">
            <div style="font-size: 36px; margin-bottom: 8px;">🎓 🏆 📜</div>
            <h2 style="margin: 0 0 10px 0; font-size: 22px; color: #ffffff;">INTERNSHIP PROGRAM COMPLETED!</h2>
            <p style="margin: 0 auto 16px auto; max-width: 500px; color: #a7f3d0; font-size: 14px; line-height: 1.5;">
                Congratulations {intern_name}! You have successfully cleared all {stage_number} rigorous evaluation stages with distinction. Your corporate internship certificate and official performance dossier are ready.
            </p>
            <div style="display: inline-block; background-color: #ffffff; color: #065f46; font-weight: bold; padding: 10px 24px; border-radius: 6px; font-size: 13px;">
                Certificate ID: CERT-AIRS-{intern_id} &bull; Status: VERIFIED
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Official Intern Evaluation Feedback - {stage_name}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 10px; color: #334155;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 28px 32px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8; font-weight: bold;">
                            AUTOMATED INTERN EVALUATION SYSTEM
                        </div>
                        <h1 style="margin: 6px 0 0 0; font-size: 22px; color: #ffffff;">Performance Review Feedback Dossier</h1>
                    </div>
                </div>
                <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 13px; color: #cbd5e1;">
                    Intern: <strong>{intern_name}</strong> (ID: {intern_id}) &bull; Review: <strong>Stage {stage_number}</strong>
                </div>
            </div>

            <!-- Body -->
            <div style="padding: 30px;">
                <!-- Score summary banner -->
                <div style="display: flex; align-items: center; justify-content: space-between; background-color: #f1f5f9; padding: 18px 24px; border-radius: 8px; margin-bottom: 24px;">
                    <div>
                        <div style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Evaluation Result</div>
                        <div style="font-size: 24px; font-weight: 800; color: #0f172a; margin-top: 2px;">
                            {stage_name}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span style="display: inline-block; background-color: {verdict_color}; color: #ffffff; font-size: 18px; font-weight: 800; padding: 6px 18px; border-radius: 9999px;">
                            {score}/100 &bull; {verdict}
                        </span>
                    </div>
                </div>

                <!-- Executive Technical Summary -->
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        📌 Executive AI Technical Critique
                    </h3>
                    <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0;">
                        {summary}
                    </p>
                    <div style="margin-top: 8px; font-size: 12px; color: #64748b;">
                        Evaluated Repository: <a href="{evaluation.get('github_url')}" target="_blank" style="color: #2563eb;">{evaluation.get('github_url')}</a>
                    </div>
                </div>

                <!-- Completed Modules -->
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        ✅ Verified & Completed Modules
                    </h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr style="background-color: #f8fafc; text-align: left; color: #64748b; font-size: 12px;">
                                <th style="padding: 8px 10px;">Module Name</th>
                                <th style="padding: 8px 10px;">Fulfillment</th>
                                <th style="padding: 8px 10px;">Verification Evidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            {modules_html}
                        </tbody>
                    </table>
                </div>

                <!-- Code Corrections -->
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        ⚠️ Necessary Code Corrections & Refactoring
                    </h3>
                    {corrections_html}
                </div>

                <!-- Missing Components -->
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        🔍 Missing or Pending Components
                    </h3>
                    <ul style="padding-left: 20px; margin: 0;">
                        {missing_html}
                    </ul>
                </div>

                <!-- Modules to Add for Next Stage -->
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        🚀 Modules to Add for Next Milestone
                    </h3>
                    {modules_to_add_html}
                </div>

                <!-- Next Review Dynamic Scheduling Block -->
                {next_review_block}

            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 20px 32px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
                This evaluation and scheduling dispatch is automatically generated by the Automated Intern Review, Task Allocation & Evaluation Engine.<br/>
                For inquiries, contact your mentor or engineering talent operations. &copy; 2026 Enterprise Systems.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def dispatch_evaluation_email(
    intern_id: str,
    intern_name: str,
    recipient_email: str,
    evaluation: Dict[str, Any],
    next_review: Optional[Dict[str, Any]] = None,
    is_final_stage: bool = False
) -> Dict[str, Any]:
    """
    Dispatches evaluation feedback email directly to the student/intern.
    Sends live email via SMTP if configured, while preserving full audit logs in DB.
    """
    stage_number = evaluation.get("stage_number", 1)
    stage_name = evaluation.get("stage_name", f"Review {stage_number}")
    subject = f"Official Evaluation & Feedback: {stage_name} [{intern_name} - {intern_id}]"
    
    html_content = generate_evaluation_email_html(
        intern_name=intern_name,
        intern_id=intern_id,
        recipient_email=recipient_email,
        evaluation=evaluation,
        next_review=next_review,
        is_final_stage=is_final_stage
    )
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_link = next_review.get("meeting_link") if next_review else None
    next_date = next_review.get("scheduled_date") if next_review else None
    
    # Send actual live email via SMTP directly to the intern
    smtp_res = send_live_smtp_email(
        to_email=recipient_email,
        subject=subject,
        html_body=html_content
    )
    
    delivery_status = "SENT_LIVE_EMAIL" if smtp_res["sent"] else ("DELIVERED" if smtp_res["method"] == "SIMULATED" else "SMTP_ERROR")
    delivery_method = smtp_res["method"]
    delivery_error = smtp_res.get("error")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO email_logs (
        intern_id, recipient_email, subject, email_body_html, stage_number, next_meeting_link, next_review_date, dispatched_at, status, delivery_method, delivery_error
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intern_id, recipient_email, subject, html_content, stage_number, next_link, next_date, now_str, delivery_status, delivery_method, delivery_error
    ))
    
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "email_log_id": log_id,
        "recipient_email": recipient_email,
        "subject": subject,
        "status": delivery_status,
        "delivery_method": delivery_method,
        "delivery_error": delivery_error,
        "dispatched_at": now_str,
        "next_meeting_link": next_link,
        "next_review_date": next_date
    }

def generate_onboarding_invitation_email_html(
    intern_name: str,
    intern_id: str,
    doj: str,
    first_review: Dict[str, Any],
    master_task: Dict[str, Any]
) -> str:
    """Generates the official Onboarding & First Review Invitation Email sent post explanation call."""
    title = master_task.get("title", "Enterprise Engineering Project")
    scope = master_task.get("project_scope", "")
    objectives = master_task.get("objectives", "")
    rules = master_task.get("submission_rules", "")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Official Internship Onboarding & Review 1 Invitation</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 10px; color: #334155;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: #ffffff; padding: 28px 32px;">
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #a5b4fc; font-weight: bold;">
                    ENTERPRISE ONBOARDING &amp; TASK ALLOCATION
                </div>
                <h1 style="margin: 8px 0 0 0; font-size: 22px; color: #ffffff;">Welcome Aboard! Review 1 Invitation</h1>
                <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.15); font-size: 13px; color: #cbd5e1;">
                    Candidate: <strong>{intern_name}</strong> (ID: {intern_id}) &bull; Date of Joining: <strong>{doj}</strong>
                </div>
            </div>

            <!-- Body -->
            <div style="padding: 30px;">
                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin-top: 0;">
                    Hello <strong>{intern_name}</strong>,<br/><br/>
                    Following our project explanation call, your official internship onboarding records have been verified. 
                    Below are your assigned master project deliverables and the confirmed schedule for your <strong>Review Stage 1</strong> evaluation.
                </p>

                <!-- Scheduled Meeting Box -->
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 20px 24px; border-radius: 10px; margin: 20px 0;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #38bdf8; font-weight: bold; margin-bottom: 8px;">
                        📅 Confirmed Review Stage 1 Sync
                    </div>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #e2e8f0;">
                        <tr>
                            <td style="padding: 6px 0; width: 140px; color: #94a3b8;">Milestone Date:</td>
                            <td style="padding: 6px 0; font-weight: bold; color: #38bdf8;">{first_review.get('scheduled_date')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #94a3b8;">Meeting Time:</td>
                            <td style="padding: 6px 0; font-weight: bold; color: #f8fafc;">{first_review.get('meeting_time', '10:30 AM IST')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #94a3b8;">Google Meet Link:</td>
                            <td style="padding: 6px 0;">
                                <a href="{first_review.get('meeting_link')}" target="_blank" style="color: #67e8f9; text-decoration: underline; font-weight: bold;">
                                    {first_review.get('meeting_link')}
                                </a>
                            </td>
                        </tr>
                    </table>
                    <div style="margin-top: 14px;">
                        <a href="{first_review.get('meeting_link')}" target="_blank" style="display: inline-block; background-color: #3b82f6; color: #ffffff; font-weight: bold; text-decoration: none; padding: 10px 22px; border-radius: 6px; font-size: 13px;">
                            Join Google Meet &rarr;
                        </a>
                    </div>
                </div>

                <!-- Assigned Project Details -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 8px 0; font-size: 15px; color: #0f172a;">📌 Assigned Master Project:</h3>
                    <div style="font-size: 14px; font-weight: 700; color: #4338ca; margin-bottom: 8px;">{title}</div>
                    <p style="font-size: 13px; color: #475569; line-height: 1.5; margin: 0 0 12px 0;">{scope}</p>
                    <div style="font-size: 12px; color: #64748b; font-weight: bold; margin-bottom: 4px;">Core Objectives:</div>
                    <pre style="background: #ffffff; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; font-family: inherit; font-size: 12px; color: #334155; white-space: pre-wrap; margin: 0;">{objectives}</pre>
                </div>

                <!-- Submission Guidelines -->
                <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 4px; font-size: 13px; color: #1e3a8a;">
                    <strong>Submission Procedure on Review Day:</strong><br/>
                    On your scheduled review date, join the Google Meet link and submit your completed task to the AI Review Bot either by providing your <strong>GitHub Repository URL</strong> or uploading your <strong>Task Document / Code Archive (.zip)</strong>.
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 18px 32px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
                Automated Intern Review, Task Allocation &amp; Evaluation Engine &bull; Nexus Global Systems &copy; 2026.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def dispatch_onboarding_invitation_email(
    intern_id: str,
    intern_name: str,
    recipient_email: str,
    doj: str,
    first_review: Dict[str, Any],
    master_task: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatches the initial Review 1 invitation email post onboarding call directly to the student/intern."""
    subject = f"Official Onboarding & Review 1 Invitation [{intern_name} - {intern_id}]"
    html_content = generate_onboarding_invitation_email_html(
        intern_name=intern_name,
        intern_id=intern_id,
        doj=doj,
        first_review=first_review,
        master_task=master_task
    )

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Send actual live email via SMTP directly to the intern
    smtp_res = send_live_smtp_email(
        to_email=recipient_email,
        subject=subject,
        html_body=html_content
    )

    delivery_status = "SENT_LIVE_EMAIL" if smtp_res["sent"] else ("DELIVERED" if smtp_res["method"] == "SIMULATED" else "SMTP_ERROR")
    delivery_method = smtp_res["method"]
    delivery_error = smtp_res.get("error")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO email_logs (
        intern_id, recipient_email, subject, email_body_html, stage_number, email_type, next_meeting_link, next_review_date, dispatched_at, status, delivery_method, delivery_error
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intern_id, recipient_email, subject, html_content, 1, "INVITATION",
        first_review.get("meeting_link"), first_review.get("scheduled_date"), now_str, delivery_status, delivery_method, delivery_error
    ))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "email_log_id": log_id,
        "recipient_email": recipient_email,
        "subject": subject,
        "email_type": "INVITATION",
        "status": delivery_status,
        "delivery_method": delivery_method,
        "delivery_error": delivery_error,
        "dispatched_at": now_str,
        "meeting_link": first_review.get("meeting_link"),
        "scheduled_date": first_review.get("scheduled_date")
    }
