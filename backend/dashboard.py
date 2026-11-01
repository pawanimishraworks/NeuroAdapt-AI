import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import (
    Learner, ConceptMastery, StudentAnswer, Concept,
    Misconception, RevisionSchedule, DiagnosticAttempt,
    LearningActivity, utc_now
)
from concepts import find_weak_prerequisites

def generate_personalized_recommendations(
    db: Session,
    learner_id: str,
    masteries: List[ConceptMastery],
    weak_concepts: List[Dict[str, Any]],
    due_revisions: List[Dict[str, Any]],
    active_misconceptions: List[Misconception]
) -> List[str]:
    """
    Recommendation Engine (Module 10):
    Synthesizes mastery, prerequisite gaps, active misconceptions, and spaced review.
    """
    recs = []

    if not masteries:
        return [
            "Welcome to NeuroAdapt AI! Take your initial Diagnostic Assessment to map your baseline knowledge graph.",
            "Start with foundational concepts: Electric Current and Potential Difference before attempting circuit calculations."
        ]

    # 1. Prerequisite gap recommendations
    if weak_concepts:
        primary_weak = weak_concepts[0]
        cid = primary_weak["concept_id"]
        weak_prereqs = find_weak_prerequisites(db, learner_id, cid)
        if weak_prereqs:
            recs.append(
                f"You are struggling with **{primary_weak['title']}** ({primary_weak['score']}%). "
                f"We recommend revising its prerequisite **{weak_prereqs[0]['title']}** ({weak_prereqs[0]['mastery_score']}%) first."
            )
        else:
            recs.append(
                f"Focus on strengthening **{primary_weak['title']}** (current mastery: {primary_weak['score']}%). "
                "Attempt 3 medium-level practice questions in the Test Centre."
            )

    # 2. Misconception remediation recommendation
    if active_misconceptions:
        top_misc = active_misconceptions[0]
        recs.append(
            f"Active Misconception: **{top_misc.misconception_title}**. "
            f"Remediation advice: {top_misc.remediation_hint or 'Discuss with the AI Tutor to clarify the underlying physical relationship.'}"
        )

    # 3. Spaced revision recommendation
    if due_revisions:
        recs.append(
            f"You have **{len(due_revisions)} concept(s)** due for spaced repetition review today. "
            "Quick revision now will prevent memory decay."
        )

    # 4. Mastery advancement
    mastered = [m for m in masteries if m.mastery_score >= 75.0]
    if len(mastered) >= 3:
        recs.append(
            f"Great progress! You have mastered {len(mastered)} concepts. "
            "Try Level 3 and 4 Counterfactual questions in the Test Centre to stress-test your conceptual depth."
        )

    if not recs:
        recs.append("Continue daily practice to consolidate your mastery across all Class 10 Electricity concepts.")

    return recs

def get_student_dashboard_metrics(db: Session, learner_id: str) -> Dict[str, Any]:
    """
    Assembles real student dashboard metrics from SQLite (Module 8 & 10).
    Provides proper empty state for new learners.
    """
    learner = db.query(Learner).filter(Learner.id == learner_id).first()
    if not learner:
        learner = Learner(id=learner_id, display_name=f"Learner {learner_id[:6]}")
        db.add(learner)
        db.commit()
        db.refresh(learner)

    # Concept masteries
    concepts = db.query(Concept).order_by(Concept.order_index).all()
    mastery_records = db.query(ConceptMastery).filter(ConceptMastery.learner_id == learner_id).all()
    mastery_dict = {m.concept_id: m for m in mastery_records}

    concept_list = []
    weak_concepts = []
    strong_concepts = []
    total_mastery_sum = 0.0

    for c in concepts:
        m = mastery_dict.get(c.id)
        score = round(m.mastery_score, 1) if m else 0.0
        attempts = m.total_attempts if m else 0
        correct = m.correct_attempts if m else 0
        total_mastery_sum += score

        entry = {
            "concept_id": c.id,
            "title": c.title,
            "description": c.description,
            "score": score,
            "attempts": attempts,
            "correct": correct,
            "difficulty": m.current_difficulty if m else 1,
            "trend": m.learning_trend if m else "unattempted",
            "status": "unattempted" if attempts == 0 else ("mastered" if score >= 75 else ("developing" if score >= 40 else "gap"))
        }
        concept_list.append(entry)

        if attempts > 0:
            if score >= 75.0:
                strong_concepts.append(entry)
            elif score < 50.0:
                weak_concepts.append(entry)

    overall_mastery = round(total_mastery_sum / len(concepts), 1) if concepts else 0.0

    # Total attempts & accuracy
    total_attempts = db.query(StudentAnswer).filter(StudentAnswer.learner_id == learner_id).count()
    correct_count = db.query(StudentAnswer).filter(
        StudentAnswer.learner_id == learner_id,
        StudentAnswer.is_correct == True
    ).count()
    incorrect_count = total_attempts - correct_count
    accuracy_percent = round((correct_count / total_attempts) * 100, 1) if total_attempts > 0 else 0.0

    # Diagnostic history
    latest_diag = db.query(DiagnosticAttempt).filter(
        DiagnosticAttempt.learner_id == learner_id
    ).order_by(DiagnosticAttempt.created_at.desc()).first()

    diagnostic_summary = None
    if latest_diag:
        diagnostic_summary = {
            "score_percent": latest_diag.score_percent,
            "total_questions": latest_diag.total_questions,
            "correct_count": latest_diag.correct_count,
            "date": latest_diag.created_at.strftime("%Y-%m-%d %H:%M")
        }

    # Spaced revisions
    now = utc_now()
    due_revisions = db.query(RevisionSchedule).filter(
        RevisionSchedule.learner_id == learner_id,
        RevisionSchedule.due_at <= now
    ).all()
    due_list = []
    for r in due_revisions:
        c = db.query(Concept).filter(Concept.id == r.concept_id).first()
        due_list.append({
            "concept_id": r.concept_id,
            "title": c.title if c else r.concept_id,
            "interval_days": r.interval_days,
            "due_at": r.due_at.isoformat()
        })

    # Active misconceptions
    misconceptions = db.query(Misconception).filter(
        Misconception.learner_id == learner_id
    ).order_by(Misconception.detected_at.desc()).limit(5).all()

    misc_list = []
    for m in misconceptions:
        c = db.query(Concept).filter(Concept.id == m.concept_id).first()
        misc_list.append({
            "id": m.id,
            "concept_id": m.concept_id,
            "concept_title": c.title if c else m.concept_id,
            "title": m.misconception_title,
            "feedback": m.diagnostic_feedback,
            "remediation": m.remediation_hint
        })

    # Timeline data for Chart.js learning progress graph
    recent_answers = db.query(StudentAnswer).filter(
        StudentAnswer.learner_id == learner_id
    ).order_by(StudentAnswer.created_at.asc()).limit(20).all()

    progress_timeline = []
    cumulative_correct = 0
    for idx, ans in enumerate(recent_answers):
        if ans.is_correct:
            cumulative_correct += 1
        progress_timeline.append({
            "attempt": idx + 1,
            "accuracy_so_far": round((cumulative_correct / (idx + 1)) * 100, 1),
            "is_correct": ans.is_correct
        })

    # Recent activities
    activities = db.query(LearningActivity).filter(
        LearningActivity.learner_id == learner_id
    ).order_by(LearningActivity.timestamp.desc()).limit(8).all()

    activity_list = [{
        "type": a.activity_type,
        "description": a.description,
        "time": a.timestamp.strftime("%b %d, %H:%M")
    } for a in activities]

    # Recommendations
    recommendations = generate_personalized_recommendations(
        db, learner_id, mastery_records, weak_concepts, due_list, misconceptions
    )

    return {
        "learner_id": learner_id,
        "display_name": learner.display_name,
        "diagnostic_completed": learner.diagnostic_completed,
        "streak_days": learner.streak_days,
        "overall_mastery": overall_mastery,
        "accuracy_percent": accuracy_percent,
        "total_attempts": total_attempts,
        "correct_answers": correct_count,
        "incorrect_answers": incorrect_count,
        "concept_mastery": concept_list,
        "strong_concepts": strong_concepts,
        "weak_concepts": weak_concepts,
        "diagnostic_summary": diagnostic_summary,
        "due_revisions": due_list,
        "misconceptions": misc_list,
        "recommendations": recommendations,
        "progress_timeline": progress_timeline,
        "recent_activities": activity_list,
        "is_new_learner": total_attempts == 0 and not learner.diagnostic_completed
    }

def get_teacher_cohort_metrics(db: Session) -> Dict[str, Any]:
    """
    Teacher & Cohort Analytics (Module 9):
    Aggregates real anonymous student records in SQLite.
    """
    total_learners = db.query(Learner).count()
    total_answers = db.query(StudentAnswer).count()
    total_correct = db.query(StudentAnswer).filter(StudentAnswer.is_correct == True).count()
    class_accuracy = round((total_correct / total_answers) * 100, 1) if total_answers > 0 else 0.0

    # Concept breakdown across cohort
    concepts = db.query(Concept).order_by(Concept.order_index).all()
    concept_breakdown = []
    mastery_scores = []

    for c in concepts:
        avg_score = db.query(func.avg(ConceptMastery.mastery_score)).filter(
            ConceptMastery.concept_id == c.id
        ).scalar() or 0.0
        students_tested = db.query(ConceptMastery).filter(
            ConceptMastery.concept_id == c.id
        ).count()

        avg_round = round(avg_score, 1)
        mastery_scores.append(avg_round)
        concept_breakdown.append({
            "concept_id": c.id,
            "title": c.title,
            "average_mastery": avg_round,
            "students_tested": students_tested
        })

    class_mastery = round(sum(mastery_scores) / len(mastery_scores), 1) if mastery_scores else 0.0

    # Sort to find most difficult concepts
    sorted_concepts = sorted(concept_breakdown, key=lambda x: x["average_mastery"])
    hardest_concept = sorted_concepts[0]["title"] if sorted_concepts else "None"

    # Cohort common misconceptions
    misc_counts = db.query(
        Misconception.misconception_title,
        func.count(Misconception.id).label("count")
    ).group_by(Misconception.misconception_title).order_by(func.count(Misconception.id).desc()).limit(6).all()

    common_misc = [{
        "title": row[0],
        "count": row[1]
    } for row in misc_counts]

    # Student roster
    learners = db.query(Learner).order_by(Learner.last_active_at.desc()).limit(25).all()
    roster = []
    support_needed = []

    for l in learners:
        att = db.query(StudentAnswer).filter(StudentAnswer.learner_id == l.id).count()
        corr = db.query(StudentAnswer).filter(
            StudentAnswer.learner_id == l.id,
            StudentAnswer.is_correct == True
        ).count()
        acc = round((corr / att) * 100, 1) if att > 0 else 0.0

        avg_m = db.query(func.avg(ConceptMastery.mastery_score)).filter(
            ConceptMastery.learner_id == l.id
        ).scalar() or 0.0

        status = "Active" if att >= 5 else ("Exploring" if att > 0 else "New")

        # Weakest concept for this student
        weakest = db.query(ConceptMastery).filter(
            ConceptMastery.learner_id == l.id
        ).order_by(ConceptMastery.mastery_score.asc()).first()
        weak_title = "None"
        if weakest:
            c = db.query(Concept).filter(Concept.id == weakest.concept_id).first()
            weak_title = c.title if c else weakest.concept_id

        entry = {
            "learner_id": l.id,
            "display_name": l.display_name,
            "attempts": att,
            "accuracy": acc,
            "average_mastery": round(avg_m, 1),
            "weakest_concept": weak_title,
            "status": status,
            "last_active": l.last_active_at.strftime("%b %d, %H:%M")
        }
        roster.append(entry)

        if att >= 3 and (acc < 50.0 or avg_m < 40.0):
            support_needed.append(entry)

    # Interventions
    interventions = []
    if sorted_concepts and sorted_concepts[0]["average_mastery"] < 50.0:
        interventions.append(
            f"Whole-Class Focus Needed: Cohort mastery in **{sorted_concepts[0]['title']}** is low ({sorted_concepts[0]['average_mastery']}%). "
            "Recommend dedicated instructional mini-lab or visual demonstration before proceeding to circuits."
        )

    if common_misc:
        interventions.append(
            f"Frequent Mental Model Flaw: **'{common_misc[0]['title']}'** occurred {common_misc[0]['count']} times across the cohort. "
            "Address this explicitly in the next class session."
        )

    if support_needed:
        interventions.append(
            f"Targeted Intervention: {len(support_needed)} student(s) show persistent difficulties (<50% accuracy). "
            "Suggest foundational review on Electric Current and Potential Difference."
        )

    return {
        "total_learners": total_learners,
        "total_attempts": total_answers,
        "class_accuracy": class_accuracy,
        "class_mastery": class_mastery,
        "hardest_concept": hardest_concept,
        "concept_breakdown": concept_breakdown,
        "common_misconceptions": common_misc,
        "learners_needing_support": support_needed,
        "student_roster": roster,
        "interventions": interventions
    }
