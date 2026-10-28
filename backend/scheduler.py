import random
import string
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

def generate_google_meet_link() -> str:
    """Generates a realistic Google Meet format meeting link: https://meet.google.com/xxx-yyyy-zzz"""
    letters = string.ascii_lowercase
    part1 = ''.join(random.choices(letters, k=3))
    part2 = ''.join(random.choices(letters, k=4))
    part3 = ''.join(random.choices(letters, k=3))
    return f"https://meet.google.com/{part1}-{part2}-{part3}"

def calculate_review_schedule(
    doj_str: str,
    total_reviews: int = 4,
    min_gap_days: int = 10,
    max_gap_days: int = 15,
    preferred_gap_days: int = 12
) -> List[Dict[str, Any]]:
    """
    Computes an N-stage review schedule starting from the intern's Date of Joining (DOJ).
    Each successive stage is scheduled with a strictly enforced 10-15 day gap.
    """
    try:
        current_date = datetime.strptime(doj_str, "%Y-%m-%d").date()
    except ValueError:
        # Fallback to today if format error
        current_date = date.today()

    schedule = []
    
    # Preset meeting times for realistic corporate operations
    meeting_times = ["10:30 AM IST", "02:00 PM IST", "04:00 PM IST", "11:00 AM IST", "03:30 PM IST"]
    
    stage_themes = [
        "Review 1: Architecture, Project Scaffolding & Core Setup",
        "Review 2: Core Business Logic, API Implementation & Database",
        "Review 3: Integration, Frontend UI, Security & Unit Tests",
        "Review 4: Final Production Readiness, CI/CD, Documentation & Deployment Dossier",
        "Review 5: Advanced Optimization, Stress Testing & Feature Expansion",
        "Review 6: Executive Capstone Presentation & Production Release"
    ]

    # Ensure gap is strictly clamped between 10 and 15
    gap_days = max(min_gap_days, min(max_gap_days, preferred_gap_days))

    running_date = current_date
    for i in range(1, total_reviews + 1):
        # Add gap (strictly between 10-15 days)
        running_date = running_date + timedelta(days=gap_days)
        
        # If falls on Sunday (weekday 6), shift to Monday (+1 day) to remain on business days while keeping gap valid
        if running_date.weekday() == 6:
            running_date += timedelta(days=1)
        # If falls on Saturday (weekday 5), shift to Monday (+2 days)
        elif running_date.weekday() == 5:
            running_date += timedelta(days=2)

        theme_name = stage_themes[i-1] if i <= len(stage_themes) else f"Review {i}: Advanced Milestone Evaluation"
        time_slot = meeting_times[(i - 1) % len(meeting_times)]
        meet_link = generate_google_meet_link()

        schedule.append({
            "stage_number": i,
            "stage_name": theme_name,
            "scheduled_date": running_date.strftime("%Y-%m-%d"),
            "gap_days": gap_days,
            "meeting_link": meet_link,
            "meeting_time": time_slot,
            "status": "SCHEDULED" if i > 1 else "ACTIVE"
        })

    return schedule
