import os
import json
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Question, Misconception, utc_now

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ----------------------------------------------------------------------------
# CONCEPT-SPECIFIC MISCONCEPTION PATTERNS & HEURISTICS
# ----------------------------------------------------------------------------
REASONING_HEURISTICS = [
    # 1. Current Attenuation / Consumption
    {
        "keywords": ["used up", "consumed", "gets less", "decreases after", "resistor eats", "lost energy means lost current"],
        "misconception": "Current Attenuation (Electric Charge Consumption)",
        "explanation": "You suggested that electric current gets 'consumed' or 'used up' by electrical components. In reality, electric charge is strictly conserved. Current is the rate of charge flow and remains constant entering and exiting components. It is electrical potential energy that transforms into heat or light, not the charges themselves!",
        "remediation": "Review the principle of conservation of electric charge: I_in = I_out."
    },
    # 2. Formula Inversion (V * R vs V / R)
    {
        "keywords": ["multiply", "v*r", "voltage times resistance", "12*4", "220*3.5", "v times r", "multiplied"],
        "misconception": "Ohm's Law Formula Inversion (Multiplication vs Division)",
        "explanation": "Your reasoning indicates calculating voltage multiplied by resistance. According to Ohm's Law (V = IR), current is calculated by dividing voltage by resistance (I = V / R). Current is inversely proportional to resistance.",
        "remediation": "Remember the Ohm's Law triangle: V at the top, I and R at the bottom (I = V/R, R = V/I, V = IR)."
    },
    # 3. Direct Proportionality Error (Thinking R increases I)
    {
        "keywords": ["increases because resistance", "resistance blocks so it speeds up", "more resistance more current", "faster flow with resistance"],
        "misconception": "Inverse Relationship Inversion",
        "explanation": "Your reasoning suggests that increasing resistance increases current. By definition, resistance is opposition to current flow. From I = V / R, when resistance increases under constant voltage, current must decrease.",
        "remediation": "Think of resistance like a constriction in a water pipe: a narrower pipe restricts flow rate, it does not increase it."
    },
    # 4. Voltage-Current Equivalence Error
    {
        "keywords": ["voltage is current", "current is voltage", "voltage flows", "amps push volts", "volts move through wire"],
        "misconception": "Voltage-Current Conceptual Confusion",
        "explanation": "Your explanation treats voltage and current as interchangeable. Voltage (potential difference) is the electrical pressure or energy transferred per unit charge (Joules/Coulomb). Current is the actual physical flow rate of charges (Coulombs/second). Voltage causes current to flow through a resistance.",
        "remediation": "Use the water analogy: Voltage is the water pressure pump; Current is the rate of water flow in liters per second."
    },
    # 5. Parallel Direct Addition Rule Inversion
    {
        "keywords": ["add parallel directly", "6+3=9", "12+4=16", "parallel adds up", "sum of resistances in parallel"],
        "misconception": "Parallel Circuit Resistance Rule Inversion",
        "explanation": "You added branch resistances directly. Direct addition (Req = R1 + R2) only applies to series circuits. Parallel branches create alternate pathways for current, which always reduces total resistance using the reciprocal rule: 1/Req = 1/R1 + 1/R2.",
        "remediation": "Always remember: in a parallel circuit, total equivalent resistance is always smaller than the smallest branch resistor."
    },
    # 6. Linear Power Misconception
    {
        "keywords": ["power doubles because current doubles", "linear power", "p proportional to i only", "p=i"],
        "misconception": "Linear Power Dissipation Error",
        "explanation": "You assumed electrical power scales linearly with current. According to Joule heating (P = I^2 * R), power dissipation is proportional to the square of current (I^2). Doubling current quadruples (4x) the dissipated power.",
        "remediation": "Review the Joule heating quadratic relationship: P = I^2 * R."
    },
    # 7. Unidimensional Stretching Error
    {
        "keywords": ["only length doubles", "area stays constant when stretched", "stretching only changes length"],
        "misconception": "Wire Volume Conservation Oversight",
        "explanation": "When a metal wire is stretched to double its length, its total volume must remain constant. Therefore, its cross-sectional area must simultaneously halve. Since R = ρL/A, doubling L and halving A increases resistance by 4 times, not 2 times.",
        "remediation": "Remember that physical deformation conserves volume (Volume = Length * Area)."
    }
]

def analyze_student_reasoning_and_answer(
    question: Question,
    selected_answer: str,
    reasoning: str,
    is_correct: bool
) -> Tuple[Optional[str], Optional[str], Optional[str], float]:
    """
    Evaluates student answer and free-form reasoning for misconceptions:
    Returns: (misconception_title, explanation, remediation_hint, reasoning_quality_score)
    """
    reasoning_text = (reasoning or "").strip().lower()
    selected_clean = (selected_answer or "").strip()

    # If answer is correct and student provided good reasoning, reward quality
    if is_correct:
        quality_score = 1.0
        if len(reasoning_text) > 15:
            # Check for positive conceptual indicators in question's expected reasoning
            indicators = question.expected_reasoning.lower().split()
            matches = sum(1 for word in indicators if len(word) > 4 and word in reasoning_text)
            if matches >= 2:
                quality_score = 1.3
        return None, None, None, quality_score

    # 1. Distractor-based Misconception Identification
    distractor_map = question.get_distractor_map()
    if selected_clean in distractor_map:
        distractor_feedback = distractor_map[selected_clean]
        return (
            "Targeted Conceptual Distractor Error",
            distractor_feedback,
            "Re-examine the fundamental definitions and units for this concept.",
            0.8
        )

    # 2. Heuristic Reasoning Pattern Matching
    for h in REASONING_HEURISTICS:
        if any(kw in reasoning_text for kw in h["keywords"]):
            return (
                h["misconception"],
                h["explanation"],
                h["remediation"],
                0.6
            )

    # 3. Fallback to Question's Default Expected Reasoning Explanation
    return (
        "Conceptual Misunderstanding",
        f"Your response differs from the expected physical principle. {question.explanation}",
        f"Key concept to review: {question.expected_reasoning}",
        0.7
    )

def record_misconception(
    db: Session,
    learner_id: str,
    concept_id: str,
    misconception_title: str,
    reasoning: str,
    feedback: str,
    remediation_hint: str
) -> Misconception:
    """
    Persists a detected misconception in SQLite to power learner and teacher dashboards.
    """
    record = Misconception(
        learner_id=learner_id,
        concept_id=concept_id,
        misconception_title=misconception_title,
        student_reasoning=reasoning or "",
        diagnostic_feedback=feedback,
        remediation_hint=remediation_hint,
        detected_at=utc_now(),
        resolved=False
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
