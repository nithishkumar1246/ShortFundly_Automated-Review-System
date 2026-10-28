import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "system.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Settings / Company Config
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Master Task & Requirements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        project_scope TEXT NOT NULL,
        objectives TEXT NOT NULL,
        tech_stack TEXT NOT NULL,
        submission_rules TEXT NOT NULL,
        review_requirements TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # Intern Profiles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        doj TEXT NOT NULL,
        mentor_name TEXT NOT NULL,
        mentor_email TEXT NOT NULL,
        current_review_stage INTEGER DEFAULT 1,
        total_reviews INTEGER DEFAULT 4,
        status TEXT DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED, ON_HOLD
        created_at TEXT NOT NULL
    )
    """)

    # Review Schedules
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT NOT NULL,
        stage_number INTEGER NOT NULL,
        stage_name TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        gap_days INTEGER NOT NULL,
        meeting_link TEXT NOT NULL,
        meeting_time TEXT NOT NULL,
        status TEXT DEFAULT 'SCHEDULED', -- SCHEDULED, SUBMITTED, EVALUATED, COMPLETED
        submission_github_url TEXT,
        submitted_at TEXT,
        evaluation_score INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (intern_id) REFERENCES interns(intern_id)
    )
    """)

    # Evaluation Reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT NOT NULL,
        stage_number INTEGER NOT NULL,
        github_url TEXT NOT NULL,
        submission_type TEXT DEFAULT 'GITHUB_URL', -- GITHUB_URL, DOCUMENT_UPLOAD
        submission_title TEXT,
        score INTEGER NOT NULL,
        verdict TEXT NOT NULL, -- PASSED, NEEDS_REVISION, DISTINCTION
        completed_modules TEXT NOT NULL, -- JSON
        code_corrections TEXT NOT NULL,  -- JSON
        missing_components TEXT NOT NULL, -- JSON
        modules_to_add TEXT NOT NULL DEFAULT '[]', -- JSON: Modules to add for next stage
        detailed_summary TEXT NOT NULL,
        evaluated_at TEXT NOT NULL,
        FOREIGN KEY (intern_id) REFERENCES interns(intern_id)
    )
    """)

    # Email Dispatch Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        email_body_html TEXT NOT NULL,
        stage_number INTEGER NOT NULL,
        email_type TEXT DEFAULT 'EVALUATION', -- INVITATION, EVALUATION, GRADUATION
        next_meeting_link TEXT,
        next_review_date TEXT,
        dispatched_at TEXT NOT NULL,
        status TEXT DEFAULT 'DELIVERED'
    )
    """)

    # Ensure schema migrations for existing DB instances
    cursor.execute("PRAGMA table_info(evaluations)")
    columns = [col[1] for col in cursor.fetchall()]
    if "modules_to_add" not in columns:
        cursor.execute("ALTER TABLE evaluations ADD COLUMN modules_to_add TEXT NOT NULL DEFAULT '[]'")
    if "submission_type" not in columns:
        cursor.execute("ALTER TABLE evaluations ADD COLUMN submission_type TEXT DEFAULT 'GITHUB_URL'")
    if "submission_title" not in columns:
        cursor.execute("ALTER TABLE evaluations ADD COLUMN submission_title TEXT")

    cursor.execute("PRAGMA table_info(email_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if "email_type" not in columns:
        cursor.execute("ALTER TABLE email_logs ADD COLUMN email_type TEXT DEFAULT 'EVALUATION'")
    if "delivery_method" not in columns:
        cursor.execute("ALTER TABLE email_logs ADD COLUMN delivery_method TEXT DEFAULT 'SIMULATED'")
    if "delivery_error" not in columns:
        cursor.execute("ALTER TABLE email_logs ADD COLUMN delivery_error TEXT")

    conn.commit()
    conn.close()

init_db()
