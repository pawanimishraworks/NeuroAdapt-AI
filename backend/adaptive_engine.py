from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Question, ConceptMastery, StudentAnswer, Concept
from concepts import build_concept_graph, find_weak_prerequisites

def select_adaptive_question(
    db: Session,
    learner_id: str,
    target_concept_id: Optional[str] = None,
    preferred_difficulty: Optional[int] = None
) -> Optional[Question]:
    """
    Adaptive Question Selection Engine:
    1. Identifies learner's weak concepts and prerequisite dependencies.
    2. Determines calibrated difficulty level (1-4).
    3. Excludes recently answered questions to prevent repetition.
    4. Selects optimal question matching the cognitive boundary.
    """
    # 1. Recent answered questions for this learner (exclude last 10)
    recent_q_ids = [
        row[0] for row in db.query(StudentAnswer.question_id).filter(
            StudentAnswer.learner_id == learner_id
        ).order_by(StudentAnswer.created_at.desc()).limit(10).all()
    ]

    # 2. Determine target concept
    selected_concept_id = target_concept_id
    calibrated_diff = preferred_difficulty

    if not selected_concept_id:
        # Check if learner has weak prerequisites in their learning path
        masteries = db.query(ConceptMastery).filter(
            ConceptMastery.learner_id == learner_id
        ).order_by(ConceptMastery.mastery_score.asc()).all()

        if masteries:
            # Pick lowest mastered concept
            weakest = masteries[0]
            # Check if this weak concept has any even weaker prerequisite
            weak_prereqs = find_weak_prerequisites(db, learner_id, weakest.concept_id)
            if weak_prereqs:
                selected_concept_id = weak_prereqs[0]["concept_id"]
                calibrated_diff = 1 # Scaffold foundation first
            else:
                selected_concept_id = weakest.concept_id
                calibrated_diff = weakest.current_difficulty
        else:
            # New learner: start with foundational concepts (order_index 1)
            first_concept = db.query(Concept).order_by(Concept.order_index.asc()).first()
            selected_concept_id = first_concept.id if first_concept else "electric-current"
            calibrated_diff = 1

    if not calibrated_diff:
        calibrated_diff = 1

    # 3. Query questions for target concept matching calibrated difficulty, excluding recent
    q = db.query(Question).filter(
        Question.concept_id == selected_concept_id,
        Question.difficulty == calibrated_diff,
        ~Question.id.in_(recent_q_ids) if recent_q_ids else True
    ).order_by(func.random()).first()

    # If no question at exact difficulty, try any difficulty in same concept (excluding recent)
    if not q:
        q = db.query(Question).filter(
            Question.concept_id == selected_concept_id,
            ~Question.id.in_(recent_q_ids) if recent_q_ids else True
        ).order_by(func.random()).first()

    # If all questions in concept recently answered, relax recent filter
    if not q:
        q = db.query(Question).filter(
            Question.concept_id == selected_concept_id
        ).order_by(func.random()).first()

    # Global fallback if still none
    if not q:
        q = db.query(Question).order_by(func.random()).first()

    return q

def get_diagnostic_questions_set(db: Session, count: int = 9) -> List[Question]:
    """
    Selects a balanced representative question set for the Diagnostic Assessment,
    covering all 9 concepts across foundational and intermediate difficulties.
    """
    concepts = db.query(Concept).order_by(Concept.order_index).all()
    selected_questions = []

    for c in concepts:
        # Pick 1 representative question from each concept (prioritize Difficulty 1 and 2 for diagnostic)
        q = db.query(Question).filter(
            Question.concept_id == c.id,
            Question.difficulty.in_([1, 2])
        ).order_by(func.random()).first()

        if not q:
            q = db.query(Question).filter(Question.concept_id == c.id).first()

        if q and q not in selected_questions:
            selected_questions.append(q)

    # If requested count is higher (e.g. 15 or 25), fill with remaining questions
    if len(selected_questions) < count:
        additional = db.query(Question).filter(
            ~Question.id.in_([q.id for q in selected_questions])
        ).order_by(func.random()).limit(count - len(selected_questions)).all()
        selected_questions.extend(additional)

    return selected_questions[:count]
