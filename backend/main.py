import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import (
    Learner, Concept, Question, StudentAnswer, DiagnosticAttempt,
    ConceptMastery, Misconception, RevisionSchedule, LearningActivity,
    utc_now
)
from schemas import (
    LearnerStartRequest, LearnerProfileResponse, LearnerResetRequest,
    QuestionResponse, DiagnosticSubmitRequest, DiagnosticResultResponse,
    AnswerSubmitRequest, AnswerFeedbackResponse, AnalyzeReasoningRequest,
    TutorChatRequest, TutorGenerateQuestionRequest, RevisionCompleteRequest
)
from seed_data import seed_database
from concepts import build_concept_graph, get_concept_graph_data, find_weak_prerequisites
from mastery import update_learner_mastery
from adaptive_engine import select_adaptive_question, get_diagnostic_questions_set
from misconception import analyze_student_reasoning_and_answer, record_misconception
from tutor import generate_socratic_tutor_response, log_tutor_conversation
from revision import update_revision_schedule, get_due_and_upcoming_revisions, complete_revision
from dashboard import get_student_dashboard_metrics, get_teacher_cohort_metrics

# ----------------------------------------------------------------------------
# INITIALIZE DATABASE & SEED DATA ON STARTUP
# ----------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

with Session(bind=engine) as init_session:
    seed_database(init_session)

# ----------------------------------------------------------------------------
# FASTAPI APPLICATION SETUP
# ----------------------------------------------------------------------------
app = FastAPI(
    title="NeuroAdapt AI",
    description="Adaptive Cognitive Learning Platform (Class 10 Physics - Electricity)",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ----------------------------------------------------------------------------
# ANONYMOUS LEARNER RESOLUTION HELPER
# ----------------------------------------------------------------------------
def resolve_learner_id(
    header_id: Optional[str] = Header(default=None, alias="X-Learner-Id"),
    query_id: Optional[str] = Query(default=None, alias="learner_id")
) -> str:
    """
    Extracts anonymous learner ID from HTTP Header or Query parameter.
    If none provided, generates a fresh anonymous ID.
    """
    lid = header_id or query_id
    if lid and isinstance(lid, str) and lid.strip():
        return lid.strip()
    return f"lrn_{uuid.uuid4().hex[:10]}"

def ensure_learner_exists(db: Session, learner_id: str, display_name: Optional[str] = None) -> Learner:
    learner = db.query(Learner).filter(Learner.id == learner_id).first()
    if not learner:
        name = display_name or f"Student {learner_id.replace('lrn_', '')[:5].upper()}"
        learner = Learner(
            id=learner_id,
            display_name=name,
            created_at=utc_now(),
            last_active_at=utc_now()
        )
        db.add(learner)
        db.commit()
        db.refresh(learner)
    else:
        learner.last_active_at = utc_now()
        if display_name and display_name.strip():
            learner.display_name = display_name.strip()
        db.commit()
    return learner

# ============================================================================
# 1. WELCOME & ANONYMOUS LEARNER MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": utc_now().isoformat()}

@app.post("/api/learner/start")
def start_learner_session(
    payload: Optional[LearnerStartRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Starts an anonymous learner session or restores an existing session from localStorage.
    No login or registration required.
    """
    lid = payload.learner_id if payload and payload.learner_id else f"lrn_{uuid.uuid4().hex[:10]}"
    name = payload.display_name if payload else None
    learner = ensure_learner_exists(db, lid, name)

    return {
        "learner_id": learner.id,
        "display_name": learner.display_name,
        "diagnostic_completed": learner.diagnostic_completed,
        "streak_days": learner.streak_days,
        "created_at": learner.created_at.isoformat(),
        "message": "Anonymous session active"
    }

@app.get("/api/learner/profile")
def get_learner_profile(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves the learner's profile, streak, and overall progress.
    """
    learner = ensure_learner_exists(db, learner_id)
    dash = get_student_dashboard_metrics(db, learner.id)
    return {
        "learner_id": learner.id,
        "display_name": learner.display_name,
        "diagnostic_completed": learner.diagnostic_completed,
        "streak_days": learner.streak_days,
        "created_at": learner.created_at.isoformat(),
        "total_attempts": dash["total_attempts"],
        "overall_mastery": dash["overall_mastery"],
        "accuracy_percent": dash["accuracy_percent"]
    }

@app.post("/api/learner/reset")
def reset_learner_journey(
    payload: LearnerResetRequest,
    db: Session = Depends(get_db)
):
    """
    Resets progress for the specified anonymous learner after confirmation.
    Does NOT affect any other learners.
    """
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to reset learning journey.")

    learner = db.query(Learner).filter(Learner.id == payload.learner_id).first()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found.")

    db.query(StudentAnswer).filter(StudentAnswer.learner_id == learner.id).delete()
    db.query(ConceptMastery).filter(ConceptMastery.learner_id == learner.id).delete()
    db.query(DiagnosticAttempt).filter(DiagnosticAttempt.learner_id == learner.id).delete()
    db.query(Misconception).filter(Misconception.learner_id == learner.id).delete()
    db.query(RevisionSchedule).filter(RevisionSchedule.learner_id == learner.id).delete()
    db.query(LearningActivity).filter(LearningActivity.learner_id == learner.id).delete()

    learner.diagnostic_completed = False
    learner.streak_days = 1
    db.commit()

    return {"message": f"Learning journey reset for {learner.display_name} ({learner.id})"}

# ============================================================================
# 2. MODULE 1 – DIAGNOSTIC ASSESSMENT ENDPOINTS
# ============================================================================

@app.get("/api/diagnostic")
def get_diagnostic_assessment(
    count: int = 9,
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Delivers a diagnostic assessment covering all 9 Class 10 Electricity concepts.
    """
    ensure_learner_exists(db, learner_id)
    questions = get_diagnostic_questions_set(db, count=max(5, min(count, 27)))

    results = []
    for q in questions:
        results.append({
            "id": q.id,
            "concept_id": q.concept_id,
            "prompt": q.prompt,
            "difficulty": q.difficulty,
            "options": q.get_options(),
            "question_type": q.question_type
        })

    return {
        "assessment_title": "Class 10 Physics: Electricity Diagnostic",
        "total_questions": len(results),
        "questions": results
    }

@app.post("/api/diagnostic/submit")
def submit_diagnostic_assessment(
    payload: DiagnosticSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates diagnostic assessment submissions:
    - Calculates concept-wise and overall mastery.
    - Identifies strong vs weak concepts.
    - Detects initial misconceptions.
    - Updates learner profile.
    """
    learner = ensure_learner_exists(db, payload.learner_id)

    total = len(payload.answers)
    if total == 0:
        raise HTTPException(status_code=400, detail="No answers submitted.")

    correct_count = 0
    concept_stats = {}

    for item in payload.answers:
        q = db.query(Question).filter(Question.id == item.question_id).first()
        if not q:
            continue

        is_corr = item.selected_answer.strip().lower() == q.correct_answer.strip().lower()
        if is_corr:
            correct_count += 1

        cid = q.concept_id
        if cid not in concept_stats:
            concept_stats[cid] = {"total": 0, "correct": 0, "title": q.concept.title if q.concept else cid}
        concept_stats[cid]["total"] += 1
        if is_corr:
            concept_stats[cid]["correct"] += 1

        # Analyze reasoning & detect misconceptions
        misc_title, misc_fb, misc_hint, quality = analyze_student_reasoning_and_answer(
            q, item.selected_answer, item.reasoning or "", is_corr
        )

        # Record answer
        db.add(StudentAnswer(
            learner_id=learner.id,
            question_id=q.id,
            selected_answer=item.selected_answer,
            reasoning=item.reasoning or "",
            is_correct=is_corr,
            misconception_detected=misc_title or "",
            created_at=utc_now()
        ))

        # Update mastery
        update_learner_mastery(
            db, learner.id, cid, q.difficulty, is_corr, quality, misc_title or ""
        )

        if misc_title:
            record_misconception(
                db, learner.id, cid, misc_title, item.reasoning or "", misc_fb or "", misc_hint or ""
            )

        # Spaced repetition initialization
        update_revision_schedule(db, learner.id, cid, 50.0 if is_corr else 25.0, bool(misc_title))

    score_pct = round((correct_count / total) * 100, 1)

    strong_concepts = []
    weak_concepts = []
    concept_breakdown = []

    for cid, s in concept_stats.items():
        pct = round((s["correct"] / s["total"]) * 100, 1)
        entry = {"concept_id": cid, "title": s["title"], "accuracy": pct}
        concept_breakdown.append(entry)
        if pct >= 70.0:
            strong_concepts.append(s["title"])
        else:
            weak_concepts.append(s["title"])

    # Record diagnostic attempt
    diag_record = DiagnosticAttempt(
        learner_id=learner.id,
        score_percent=score_pct,
        total_questions=total,
        correct_count=correct_count,
        weak_concepts_json=json.dumps(weak_concepts),
        strong_concepts_json=json.dumps(strong_concepts),
        created_at=utc_now()
    )
    db.add(diag_record)

    learner.diagnostic_completed = True
    db.add(LearningActivity(
        learner_id=learner.id,
        activity_type="diagnostic",
        description=f"Completed Diagnostic Assessment with score {score_pct}% ({correct_count}/{total} correct)."
    ))
    db.commit()

    recommendations = []
    if weak_concepts:
        recommendations.append(f"Priority focus: Start by strengthening **{weak_concepts[0]}**.")
    if strong_concepts:
        recommendations.append(f"Strong foundation detected in **{', '.join(strong_concepts[:2])}**.")

    return {
        "score_percent": score_pct,
        "total_questions": total,
        "correct_count": correct_count,
        "strong_concepts": strong_concepts,
        "weak_concepts": weak_concepts,
        "concept_breakdown": concept_breakdown,
        "recommendations": recommendations
    }

# ============================================================================
# 3. MODULE 2 & 3 – CONCEPTS, GRAPH & MASTERY ENDPOINTS
# ============================================================================

@app.get("/api/concepts")
def get_concepts_list(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Returns all curriculum concepts with the learner's live mastery scores.
    """
    ensure_learner_exists(db, learner_id)
    graph_data = get_concept_graph_data(db, learner_id)
    return {
        "concepts": graph_data["nodes"],
        "relationships": graph_data["edges"],
        "is_acyclic": graph_data["is_acyclic"]
    }

@app.get("/api/concepts/graph")
def get_concept_networkx_graph(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Full NetworkX Directed Acyclic Graph data structure with topological learning order.
    """
    ensure_learner_exists(db, learner_id)
    return get_concept_graph_data(db, learner_id)

@app.get("/api/mastery")
def get_mastery_breakdown(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Returns detailed mastery status, calibrated difficulties, and practice statistics.
    """
    ensure_learner_exists(db, learner_id)
    dash = get_student_dashboard_metrics(db, learner_id)
    return {
        "overall_mastery": dash["overall_mastery"],
        "concepts": dash["concept_mastery"],
        "strong_concepts": dash["strong_concepts"],
        "weak_concepts": dash["weak_concepts"]
    }

# ============================================================================
# 4. MODULE 4 & 5 – ADAPTIVE ENGINE & MISCONCEPTION DETECTION
# ============================================================================

@app.get("/api/next-question")
def get_next_adaptive_question(
    concept_id: Optional[str] = None,
    difficulty: Optional[int] = None,
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Selects the next adaptive question based on cognitive boundaries,
    prerequisite gaps, and difficulty calibration (0-30% Easy, 31-60% Medium, etc.).
    """
    ensure_learner_exists(db, learner_id)
    q = select_adaptive_question(db, learner_id, target_concept_id=concept_id, preferred_difficulty=difficulty)

    if not q:
        raise HTTPException(status_code=404, detail="No suitable question found.")

    return {
        "id": q.id,
        "concept_id": q.concept_id,
        "concept_title": q.concept.title if q.concept else q.concept_id,
        "prompt": q.prompt,
        "difficulty": q.difficulty,
        "options": q.get_options(),
        "question_type": q.question_type
    }

@app.post("/api/answer")
def submit_adaptive_answer(
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates an answer and student reasoning:
    1. Misconception Detection Engine (distractor map & reasoning pattern analysis).
    2. Learner Mastery Model weighted update.
    3. Spaced Repetition Schedule update.
    4. Activity logging.
    """
    learner = ensure_learner_exists(db, payload.learner_id)
    q = db.query(Question).filter(Question.id == payload.question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")

    is_corr = payload.answer.strip().lower() == q.correct_answer.strip().lower()

    # Misconception analysis
    misc_title, misc_fb, misc_hint, quality = analyze_student_reasoning_and_answer(
        q, payload.answer, payload.reasoning or "", is_corr
    )

    # Record answer in database
    db.add(StudentAnswer(
        learner_id=learner.id,
        question_id=q.id,
        selected_answer=payload.answer.strip(),
        reasoning=(payload.reasoning or "").strip(),
        is_correct=is_corr,
        misconception_detected=misc_title or "",
        created_at=utc_now()
    ))

    # Update cognitive mastery model
    mastery_update = update_learner_mastery(
        db, learner.id, q.concept_id, q.difficulty, is_corr, quality, misc_title or ""
    )

    # Record misconception if detected
    if misc_title:
        record_misconception(
            db, learner.id, q.concept_id, misc_title, payload.reasoning or "", misc_fb or "", misc_hint or ""
        )

    # Update spaced repetition schedule
    revision = update_revision_schedule(
        db, learner.id, q.concept_id, mastery_update["new_score"], bool(misc_title)
    )

    # Activity log
    action_text = f"Answered question on {q.concept.title if q.concept else q.concept_id} ({'Correct' if is_corr else 'Incorrect'})."
    db.add(LearningActivity(learner_id=learner.id, activity_type="practice", description=action_text))
    db.commit()

    return {
        "correct": is_corr,
        "correct_answer": q.correct_answer,
        "explanation": q.explanation,
        "concept_id": q.concept_id,
        "previous_mastery": mastery_update["previous_score"],
        "new_mastery": mastery_update["new_score"],
        "mastery_delta": mastery_update["delta"],
        "difficulty_calibrated": mastery_update["current_difficulty"],
        "misconception_detected": misc_title or None,
        "misconception_explanation": misc_fb or None,
        "remediation_hint": misc_hint or None,
        "next_revision_due": revision.due_at.isoformat(),
        "revision_interval_days": revision.interval_days
    }

@app.get("/api/progress")
def get_learning_progress(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Returns time-series accuracy timeline and progress stats for visualization.
    """
    ensure_learner_exists(db, learner_id)
    dash = get_student_dashboard_metrics(db, learner_id)
    return {
        "timeline": dash["progress_timeline"],
        "accuracy_percent": dash["accuracy_percent"],
        "total_attempts": dash["total_attempts"],
        "overall_mastery": dash["overall_mastery"]
    }

@app.get("/api/misconceptions")
def get_learner_misconceptions(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Returns detected misconceptions history for the learner.
    """
    ensure_learner_exists(db, learner_id)
    dash = get_student_dashboard_metrics(db, learner_id)
    return {"misconceptions": dash["misconceptions"]}

@app.post("/api/analyze-reasoning")
def analyze_freeform_reasoning(
    payload: AnalyzeReasoningRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates free-form student reasoning on a concept.
    """
    ensure_learner_exists(db, payload.learner_id)
    dummy_q = Question(
        concept_id=payload.concept_id,
        prompt=payload.question_prompt,
        difficulty=2,
        options_json="[]",
        correct_answer="",
        explanation="Conceptual evaluation",
        expected_reasoning=f"Correct physical understanding of {payload.concept_id}."
    )
    misc_title, misc_fb, misc_hint, quality = analyze_student_reasoning_and_answer(
        dummy_q, payload.selected_answer or "", payload.student_reasoning, False
    )

    return {
        "misconception_detected": misc_title or None,
        "explanation": misc_fb or "Your reasoning appears aligned with physical principles.",
        "remediation_hint": misc_hint or "Continue practicing application problems.",
        "reasoning_quality": quality
    }

# ============================================================================
# 5. MODULE 6 – AI TUTOR ENDPOINTS
# ============================================================================

@app.post("/api/tutor/chat")
def chat_with_ai_tutor(
    payload: TutorChatRequest,
    db: Session = Depends(get_db)
):
    """
    Context-aware Socratic AI Tutor:
    Integrates live student mastery context and provides pedagogical explanations.
    """
    learner = ensure_learner_exists(db, payload.learner_id)
    reply = generate_socratic_tutor_response(
        db, learner.id, payload.message, payload.context_concept
    )
    log_tutor_conversation(db, learner.id, payload.message, reply, payload.context_concept)

    db.add(LearningActivity(
        learner_id=learner.id,
        activity_type="tutor_chat",
        description=f"Discussed with AI Tutor: '{payload.message[:45]}...'"
    ))
    db.commit()

    return {
        "reply": reply,
        "learner_id": learner.id,
        "context_concept": payload.context_concept
    }

@app.post("/api/tutor/generate-question")
def generate_tutor_practice_question(
    payload: TutorGenerateQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    AI Tutor generates targeted practice or counterfactual challenge question on a concept.
    """
    ensure_learner_exists(db, payload.learner_id)
    diff = payload.difficulty or 2
    q = db.query(Question).filter(
        Question.concept_id == payload.concept_id,
        Question.difficulty == diff
    ).first()

    if not q:
        q = db.query(Question).filter(Question.concept_id == payload.concept_id).first()

    if not q:
        raise HTTPException(status_code=404, detail="No question available for this concept.")

    return {
        "id": q.id,
        "concept_id": q.concept_id,
        "prompt": q.prompt,
        "difficulty": q.difficulty,
        "options": q.get_options(),
        "question_type": q.question_type
    }

# ============================================================================
# 6. MODULE 7 – SPACED REPETITION REVISION ENDPOINTS
# ============================================================================

@app.get("/api/revisions")
def get_revision_schedule_list(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves due and upcoming spaced repetition revisions.
    """
    ensure_learner_exists(db, learner_id)
    return get_due_and_upcoming_revisions(db, learner_id)

@app.post("/api/revisions/complete")
def complete_revision_session(
    payload: RevisionCompleteRequest,
    db: Session = Depends(get_db)
):
    """
    Updates revision schedule upon completing a spaced repetition session.
    """
    ensure_learner_exists(db, payload.learner_id)
    res = complete_revision(
        db, payload.learner_id, payload.concept_id, payload.recalled_successfully
    )

    db.add(LearningActivity(
        learner_id=payload.learner_id,
        activity_type="revision",
        description=f"Completed revision for concept {payload.concept_id} ({'Recalled' if payload.recalled_successfully else 'Needs Review'})."
    ))
    db.commit()

    return res

# ============================================================================
# 7. MODULE 8, 9, 10 – DASHBOARD & TEACHER ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/dashboard/student")
def get_student_dashboard(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    """
    Module 8 & 10: Complete real student dashboard metrics and recommendations.
    """
    ensure_learner_exists(db, learner_id)
    return get_student_dashboard_metrics(db, learner_id)

@app.get("/api/dashboard/teacher")
def get_teacher_dashboard(db: Session = Depends(get_db)):
    """
    Module 9: Complete teacher cohort analytics.
    """
    return get_teacher_cohort_metrics(db)

# ----------------------------------------------------------------------------
# BACKWARD COMPATIBILITY ENDPOINTS (Ensures zero breaking changes for existing code)
# ----------------------------------------------------------------------------
@app.get("/api/dashboard")
def student_dashboard_compat(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    return get_student_dashboard_metrics(db, learner_id)

@app.get("/api/questions/adaptive")
def adaptive_questions_compat(
    mode: str = "adaptive",
    topic: Optional[str] = None,
    difficulty: Optional[int] = None,
    count: int = 5,
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    ensure_learner_exists(db, learner_id)
    # Return questions formatted for test runner
    questions = []
    if mode == "diagnostic":
        q_objs = get_diagnostic_questions_set(db, count=count)
    else:
        q_objs = []
        for _ in range(count):
            q = select_adaptive_question(db, learner_id, target_concept_id=topic, preferred_difficulty=difficulty)
            if q and q not in q_objs:
                q_objs.append(q)

    for q in q_objs:
        questions.append({
            "id": q.id,
            "concept_id": q.concept_id,
            "prompt": q.prompt,
            "difficulty": q.difficulty,
            "options": q.get_options(),
            "question_type": q.question_type
        })

    return {"questions": questions}

@app.post("/api/answers")
def answers_compat(
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db)
):
    return submit_adaptive_answer(payload, db)

@app.get("/api/teacher/analytics")
def teacher_analytics_compat(db: Session = Depends(get_db)):
    return get_teacher_cohort_metrics(db)

@app.get("/api/me")
def me_compat(
    learner_id: str = Depends(resolve_learner_id),
    db: Session = Depends(get_db)
):
    learner = ensure_learner_exists(db, learner_id)
    return {"user": {"id": learner.id, "name": learner.display_name, "role": "student"}}

# ============================================================================
# STATIC FRONTEND FILE SERVING (Preserves existing frontend completely)
# ============================================================================

@app.get("/", include_in_schema=False)
def serve_welcome_page():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "NeuroAdapt AI API running. Visit /docs"}

@app.get("/{page_name}.html", include_in_schema=False)
def serve_html(page_name: str):
    file_path = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")

@app.get("/css/{file_name}", include_in_schema=False)
def serve_css(file_name: str):
    file_path = os.path.join(FRONTEND_DIR, "css", file_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")

@app.get("/js/{file_name}", include_in_schema=False)
def serve_js(file_name: str):
    file_path = os.path.join(FRONTEND_DIR, "js", file_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript not found")
