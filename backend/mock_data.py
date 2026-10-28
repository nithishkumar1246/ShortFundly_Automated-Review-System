import datetime
from database import get_connection
from scheduler import calculate_review_schedule
from email_service import dispatch_onboarding_invitation_email

def seed_initial_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Check if settings exist
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('company_name', 'Nexus Global Systems')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('default_total_reviews', '4')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('default_gap_days', '12')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('system_version', '2.5.0-Enterprise')")

    # Check if master tasks exist
    cursor.execute("SELECT COUNT(*) FROM master_tasks")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO master_tasks (
            title, project_scope, objectives, tech_stack, submission_rules, review_requirements, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Enterprise Real-Time AI Task & Intern Performance Intelligence Engine",
            "Architect and construct an end-to-end, resilient microservices system responsible for automated code review, continuous intern milestone tracking, and dynamic scheduling. The system integrates git webhooks, AI-driven code AST analysis, automated grading rubrics, and automated communication channels.",
            "1. Deliver scalable RESTful APIs with Pydantic payload sanitization.\n2. Implement a dynamic N-stage review scheduler with strict 10–15 day inter-review intervals and Google Meet generation.\n3. Implement a dual dispatch feedback engine transmitting evaluations simultaneously to interactive chat and corporate email.\n4. Ensure 80%+ test coverage, containerization with multi-stage Dockerfiles, and CI/CD pipelines.",
            "Backend: Python (FastAPI / Uvicorn), SQLite / PostgreSQL, SQLAlchemy\nFrontend: Modern HTML5, Tailwind CSS, Vanilla JavaScript, Web Speech API (TTS)\nInfrastructure: Docker, Docker Compose, GitHub Actions CI/CD",
            "1. All submissions MUST be valid GitHub public repositories.\n2. Submissions must contain a root README.md with architecture diagrams, setup guidelines, and API endpoint documentation.\n3. Every commit must have meaningful commit messages adhering to Conventional Commits.\n4. Secrets and credentials must NEVER be checked into version control (.env files must be gitignored).",
            "Stage 1 Scaffolding: Repo initialized, requirements pinned, settings management, architecture draft.\nStage 2 Core Logic: REST API routes, normalized database models, data validation, and transaction handling.\nStage 3 Integration: Frontend interactive dashboard, unit & integration test suites (>80% coverage), error middleware.\nStage 4 Production: Docker containerization, healthz telemetry, CI/CD automated pipeline, and deployment dossier.",
            1,
            now_str
        ))

    # Check if sample interns exist
    cursor.execute("SELECT COUNT(*) FROM interns")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        interns_data = [
            {
                "intern_id": "INT-101",
                "name": "Aarav Sharma",
                "email": "aarav.sharma@nexusinnovations.tech",
                "role": "AI Full-Stack Intern",
                "department": "Core Intelligence & Platforms",
                "doj": "2026-10-01",
                "mentor_name": "Dr. Sarah Jenkins",
                "mentor_email": "s.jenkins@nexusinnovations.tech",
                "current_review_stage": 1,
                "total_reviews": 4
            },
            {
                "intern_id": "INT-102",
                "name": "Priya Patel",
                "email": "priya.patel@nexusinnovations.tech",
                "role": "Cloud Backend Intern",
                "department": "Infrastructure & Microservices",
                "doj": "2026-10-10",
                "mentor_name": "Devon Miller",
                "mentor_email": "d.miller@nexusinnovations.tech",
                "current_review_stage": 1,
                "total_reviews": 4
            },
            {
                "intern_id": "INT-103",
                "name": "Marcus Vance",
                "email": "marcus.vance@nexusinnovations.tech",
                "role": "DevOps & Systems Intern",
                "department": "Cloud Platforms",
                "doj": "2026-10-15",
                "mentor_name": "Elena Rostova",
                "mentor_email": "e.rostova@nexusinnovations.tech",
                "current_review_stage": 1,
                "total_reviews": 4
            }
        ]

        for intern in interns_data:
            cursor.execute("""
            INSERT INTO interns (
                intern_id, name, email, role, department, doj, mentor_name, mentor_email, current_review_stage, total_reviews, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intern["intern_id"], intern["name"], intern["email"], intern["role"], intern["department"],
                intern["doj"], intern["mentor_name"], intern["mentor_email"], intern["current_review_stage"],
                intern["total_reviews"], "ACTIVE", now_str
            ))

            # Automatically compute dynamic N-review schedule starting from DOJ
            schedule = calculate_review_schedule(intern["doj"], total_reviews=intern["total_reviews"], preferred_gap_days=12)
            for stage in schedule:
                cursor.execute("""
                INSERT INTO review_schedules (
                    intern_id, stage_number, stage_name, scheduled_date, gap_days, meeting_link, meeting_time, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    intern["intern_id"], stage["stage_number"], stage["stage_name"], stage["scheduled_date"],
                    stage["gap_days"], stage["meeting_link"], stage["meeting_time"], stage["status"], now_str
                ))

            # Fetch active master task to generate initial onboarding invitation
            cursor.execute("SELECT * FROM master_tasks WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
            task_row = cursor.fetchone()
            task_dict = dict(task_row) if task_row else {}
            if schedule and task_dict:
                dispatch_onboarding_invitation_email(
                    intern_id=intern["intern_id"],
                    intern_name=intern["name"],
                    recipient_email=intern["email"],
                    doj=intern["doj"],
                    first_review=schedule[0],
                    master_task=task_dict
                )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_initial_data()
    print("Database seeded successfully.")
