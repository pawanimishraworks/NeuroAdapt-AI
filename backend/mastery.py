import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import ConceptMastery, Question, Learner, utc_now

def update_learner_mastery(
    db: Session,
    learner_id: str,
    concept_id: str,
    question_difficulty: int,
    is_correct: bool,
    reasoning_quality: float = 1.0, # 0.0 to 1.5 multiplier based on reasoning
    misconception_name: str = ""
) -> dict:
    """
    Weighted Cognitive Mastery Update Algorithm:
    - Factors in previous mastery, correctness, question difficulty, and reasoning quality.
    - Prevents single mistakes from wiping out established mastery through dampening.
    - Updates difficulty calibration and learning trend (improving, stable, declining).
    """
    mastery = db.query(ConceptMastery).filter(
        ConceptMastery.learner_id == learner_id,
        ConceptMastery.concept_id == concept_id
    ).first()

    now = utc_now()

    if not mastery:
        mastery = ConceptMastery(
            learner_id=learner_id,
            concept_id=concept_id,
            mastery_score=0.0,
            total_attempts=0,
            correct_attempts=0,
            incorrect_attempts=0,
            current_difficulty=1,
            last_practiced_at=now,
            learning_trend="new",
            identified_misconceptions="[]",
            next_revision_at=now
        )
        db.add(mastery)

    prev_score = mastery.mastery_score
    diff_weight = {1: 8.0, 2: 12.0, 3: 16.0, 4: 20.0}.get(question_difficulty, 10.0)

    if is_correct:
        # Mastery moves upward smoothly
        # If learner is already at high mastery, gains taper off slightly (logistic feel)
        headroom = 100.0 - prev_score
        gain = (diff_weight * (headroom / 100.0) + (diff_weight * 0.4)) * reasoning_quality
        new_score = min(100.0, prev_score + gain)
        mastery.correct_attempts += 1
        trend = "improving"
    else:
        # Dampened penalty so established mastery is not instantly destroyed
        # For higher previous mastery, mistake dampening protects the score
        penalty_base = diff_weight * 0.65
        # If question was Hard/Advanced (Diff 3/4), error penalty is lower
        if question_difficulty >= 3:
            penalty_base *= 0.6

        new_score = max(0.0, prev_score - penalty_base)
        mastery.incorrect_attempts += 1
        trend = "declining" if prev_score > 30 else "struggling"

    mastery.total_attempts += 1
    mastery.mastery_score = round(new_score, 1)
    mastery.last_practiced_at = now
    mastery.learning_trend = trend

    # Calibrate optimal difficulty based on new mastery:
    # 0–30% -> Level 1 (Easy)
    # 31–60% -> Level 2 (Medium)
    # 61–85% -> Level 3 (Hard)
    # 86–100% -> Level 4 (Advanced)
    if new_score <= 30.0:
        mastery.current_difficulty = 1
    elif new_score <= 60.0:
        mastery.current_difficulty = 2
    elif new_score <= 85.0:
        mastery.current_difficulty = 3
    else:
        mastery.current_difficulty = 4

    # Record identified misconceptions if present
    if misconception_name:
        try:
            curr_misc = json.loads(mastery.identified_misconceptions or "[]")
        except Exception:
            curr_misc = []
        if misconception_name not in curr_misc:
            curr_misc.append(misconception_name)
            mastery.identified_misconceptions = json.dumps(curr_misc)

    db.commit()

    return {
        "previous_score": prev_score,
        "new_score": mastery.mastery_score,
        "delta": round(mastery.mastery_score - prev_score, 1),
        "current_difficulty": mastery.current_difficulty,
        "trend": mastery.learning_trend,
        "total_attempts": mastery.total_attempts,
        "correct_attempts": mastery.correct_attempts
    }
