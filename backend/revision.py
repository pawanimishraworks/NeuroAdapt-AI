from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import RevisionSchedule, ConceptMastery, Concept, utc_now

def update_revision_schedule(
    db: Session,
    learner_id: str,
    concept_id: str,
    mastery_score: float,
    has_misconceptions: bool = False
) -> RevisionSchedule:
    """
    Intelligent Spaced Repetition Scheduling:
    - Very weak (<30%): Tomorrow (1 day)
    - Weak (31-60%): In 2 days
    - Improving (61-85%): In 4 days
    - Strong (>85%): In 7-14 days
    - If active misconceptions are present, intervals are halved to ensure prompt remediation.
    """
    now = utc_now()

    if mastery_score <= 30.0:
        base_days = 1
    elif mastery_score <= 60.0:
        base_days = 2
    elif mastery_score <= 85.0:
        base_days = 4
    else:
        base_days = 10

    # Prioritize concepts with repeated misconceptions
    if has_misconceptions and base_days > 1:
        base_days = max(1, base_days // 2)

    due_at = now + timedelta(days=base_days)

    schedule = db.query(RevisionSchedule).filter(
        RevisionSchedule.learner_id == learner_id,
        RevisionSchedule.concept_id == concept_id
    ).first()

    if not schedule:
        schedule = RevisionSchedule(
            learner_id=learner_id,
            concept_id=concept_id,
            due_at=due_at,
            interval_days=base_days,
            last_reviewed_at=now,
            status="pending"
        )
        db.add(schedule)
    else:
        schedule.due_at = due_at
        schedule.interval_days = base_days
        schedule.last_reviewed_at = now
        schedule.status = "pending"

    db.commit()
    db.refresh(schedule)
    return schedule

def get_due_and_upcoming_revisions(db: Session, learner_id: str) -> Dict[str, Any]:
    """
    Returns overdue revisions, due today revisions, and upcoming scheduled revisions.
    """
    now = utc_now()
    schedules = db.query(RevisionSchedule).filter(
        RevisionSchedule.learner_id == learner_id
    ).order_by(RevisionSchedule.due_at.asc()).all()

    due_now = []
    upcoming = []

    for s in schedules:
        c = db.query(Concept).filter(Concept.id == s.concept_id).first()
        title = c.title if c else s.concept_id
        is_overdue = s.due_at <= now

        entry = {
            "concept_id": s.concept_id,
            "title": title,
            "due_at": s.due_at.isoformat(),
            "interval_days": s.interval_days,
            "status": "overdue" if is_overdue else "pending"
        }

        if is_overdue:
            due_now.append(entry)
        else:
            upcoming.append(entry)

    return {
        "due_count": len(due_now),
        "due_revisions": due_now,
        "upcoming_revisions": upcoming
    }

def complete_revision(db: Session, learner_id: str, concept_id: str, recalled_successfully: bool) -> Dict[str, Any]:
    """
    Updates schedule upon learner revision:
    - If recalled successfully, interval expands (e.g. 1d -> 3d -> 7d -> 14d).
    - If failed, interval resets to 1 day.
    """
    now = utc_now()
    schedule = db.query(RevisionSchedule).filter(
        RevisionSchedule.learner_id == learner_id,
        RevisionSchedule.concept_id == concept_id
    ).first()

    if not schedule:
        schedule = RevisionSchedule(
            learner_id=learner_id,
            concept_id=concept_id,
            due_at=now + timedelta(days=1),
            interval_days=1,
            last_reviewed_at=now,
            status="pending"
        )
        db.add(schedule)

    if recalled_successfully:
        next_interval = min(30, schedule.interval_days * 2 + 1)
        schedule.status = "completed"
    else:
        next_interval = 1
        schedule.status = "overdue"

    schedule.interval_days = next_interval
    schedule.due_at = now + timedelta(days=next_interval)
    schedule.last_reviewed_at = now

    db.commit()

    return {
        "concept_id": concept_id,
        "recalled_successfully": recalled_successfully,
        "next_interval_days": next_interval,
        "next_due_at": schedule.due_at.isoformat()
    }
