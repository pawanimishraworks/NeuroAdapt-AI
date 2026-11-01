import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import ConceptMastery, Concept, TutorConversation, TutorMessage, utc_now

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def get_learner_context_summary(db: Session, learner_id: str) -> Dict[str, Any]:
    """
    Assembles real learner context from SQLite for the AI tutor:
    weak concepts, strong concepts, average mastery, and active misconceptions.
    """
    masteries = db.query(ConceptMastery).filter(ConceptMastery.learner_id == learner_id).all()
    if not masteries:
        return {
            "total_concepts_practiced": 0,
            "average_mastery": 0.0,
            "weak_concepts": ["Electric Current", "Potential Difference"],
            "mastered_concepts": [],
            "recent_misconceptions": []
        }

    total_score = sum(m.mastery_score for m in masteries)
    avg_score = round(total_score / len(masteries), 1)

    weak = []
    strong = []
    misc_set = set()

    for m in masteries:
        c = db.query(Concept).filter(Concept.id == m.concept_id).first()
        title = c.title if c else m.concept_id
        if m.mastery_score < 50.0:
            weak.append(f"{title} ({m.mastery_score}%)")
        elif m.mastery_score >= 75.0:
            strong.append(f"{title} ({m.mastery_score}%)")

        try:
            m_list = json.loads(m.identified_misconceptions or "[]")
            for item in m_list:
                misc_set.add(item)
        except Exception:
            pass

    return {
        "total_concepts_practiced": len(masteries),
        "average_mastery": avg_score,
        "weak_concepts": weak,
        "mastered_concepts": strong,
        "recent_misconceptions": list(misc_set)
    }

def call_gemini_api(prompt: str, system_instruction: str) -> Optional[str]:
    """
    Calls Google Gemini API with timeout handling if GEMINI_API_KEY is available.
    """
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text_part:
                    return text_part.strip()
    except Exception as e:
        # Fall back to rule-based engine cleanly on timeout or network issues
        pass

    return None

def generate_socratic_tutor_response(
    db: Session,
    learner_id: str,
    user_message: str,
    context_concept: Optional[str] = None
) -> str:
    """
    Personalized Socratic AI Tutor:
    1. Loads learner mastery profile from SQLite.
    2. Adapts explanation depth:
       - Low mastery (<40%): Scaffolds foundational analogies, simple formulas, step-by-step.
       - High mastery (>75%): Counterfactual challenges, advanced numerical derivations.
    3. Attempts Gemini LLM if configured; otherwise runs expert pedagogical knowledge engine.
    """
    learner_ctx = get_learner_context_summary(db, learner_id)
    text = user_message.lower()

    # Try LLM if configured
    if GEMINI_API_KEY:
        system_prompt = (
            "You are NeuroAdapt AI Socratic Tutor for Class 10 Physics (Electricity).\n"
            f"Student Knowledge Context:\n"
            f"- Average Mastery: {learner_ctx['average_mastery']}%\n"
            f"- Weak Concepts: {', '.join(learner_ctx['weak_concepts']) or 'None'}\n"
            f"- Mastered Concepts: {', '.join(learner_ctx['mastered_concepts']) or 'None'}\n"
            f"- Known Misconceptions: {', '.join(learner_ctx['recent_misconceptions']) or 'None'}\n\n"
            "Pedagogical Guidelines:\n"
            "1. If student mastery is low, use simple water-pipe analogies and clear definitions.\n"
            "2. If student mastery is high, introduce counterfactual questions.\n"
            "3. Guide through Socratic inquiry rather than just giving direct answers.\n"
            "4. Keep explanations under 250 words with clear formatting."
        )
        llm_reply = call_gemini_api(user_message, system_prompt)
        if llm_reply:
            return llm_reply

    # ------------------------------------------------------------------------
    # RULE-BASED FALLBACK TUTOR ENGINE (Always available offline without API key)
    # ------------------------------------------------------------------------
    avg_m = learner_ctx["average_mastery"]

    # 1. Ohm's Law
    if "ohm" in text or "v = ir" in text:
        if avg_m < 45.0:
            return (
                "**Ohm's Law Foundation:**\n\n"
                "Think of an electric circuit like water flowing through a garden pipe:\n"
                "• **Voltage (V)** is the water pump pressure pushing the water.\n"
                "• **Current (I)** is the actual rate of water flow (liters per second).\n"
                "• **Resistance (R)** is a squeeze or valve restricting the pipe.\n\n"
                "The relationship is **$V = I \\times R$**.\n\n"
                "💡 *Quick Check for You:*\n"
                "If the battery voltage $V$ stays at 12 V and we make the resistance twice as big, what will happen to the current flow?"
            )
        else:
            return (
                "**Ohm's Law Advanced Analysis:**\n\n"
                "In an ohmic conductor at constant temperature, current $I$ is directly proportional to voltage $V$:\n"
                "$$I = \\frac{V}{R}$$\n\n"
                "• The slope of a $V-I$ graph gives the resistance $R = \\frac{\\Delta V}{\\Delta I}$.\n"
                "• If temperature rises, metallic resistance increases, causing non-linear curvature.\n\n"
                "💡 *Counterfactual Challenge:*\n"
                "Suppose you have a circuit where voltage increases by 20% and resistance increases by 50%. "
                "Does the current increase or decrease, and by what percentage?"
            )

    # 2. Series vs Parallel Circuits
    if any(k in text for k in ["series", "parallel", "branch"]):
        return (
            "**Series vs. Parallel Circuits Comparison:**\n\n"
            "1. **Series Circuits (Single Loop):**\n"
            "   • Current is identical everywhere: $I_{total} = I_1 = I_2$.\n"
            "   • Equivalent Resistance adds up: $R_{eq} = R_1 + R_2$.\n"
            "   • Voltage divides across components: $V = V_1 + V_2$.\n\n"
            "2. **Parallel Circuits (Multiple Independent Branches):**\n"
            "   • Voltage is identical across each branch: $V_{branch} = V_{supply}$.\n"
            "   • Total resistance decreases: $\\frac{1}{R_{eq}} = \\frac{1}{R_1} + \\frac{1}{R_2}$.\n"
            "   • Current divides across branches: $I_{total} = I_1 + I_2$.\n\n"
            "💡 *Practical Application:*\n"
            "Why are household appliances always wired in parallel rather than series?"
        )

    # 3. Heating Effect / Joule's Law
    if any(k in text for k in ["heat", "heating", "joule", "fuse"]):
        return (
            "**Joule's Law of Heating:**\n\n"
            "When current $I$ passes through a resistor $R$ for time $t$, electrical energy is transformed into thermal energy:\n"
            "$$\\mathbf{H = I^2 \\times R \\times t}$$\n\n"
            "Key Observations:\n"
            "• Heat is proportional to **current squared ($I^2$)**. Doubling current quadruples (4x) heat generation!\n"
            "• High-resistance heating elements (like Nichrome) produce intense heat without melting.\n"
            "• Safety fuses use low-melting-point alloys that melt to break the circuit when current is dangerously high.\n\n"
            "Would you like to solve a numerical problem using $H = I^2Rt$?"
        )

    # 4. Numerical Problem Step-by-Step
    if any(k in text for k in ["numerical", "solve", "problem", "calculate"]):
        return (
            "Let's solve a Class 10 numerical step-by-step!\n\n"
            "**Problem:** An electric lamp of 100 Ω and a toaster of 50 Ω are connected in parallel to a 220 V source.\n\n"
            "**Step 1:** Find equivalent resistance $R_{eq}$:\n"
            "$$\\frac{1}{R_{eq}} = \\frac{1}{100} + \\frac{1}{50} = \\frac{1 + 2}{100} = \\frac{3}{100} \\implies R_{eq} = \\frac{100}{3} \\approx 33.33\\,\\Omega$$\n\n"
            "**Step 2:** Find total current drawn from the 220 V supply:\n"
            "$$I = \\frac{V}{R_{eq}} = \\frac{220}{33.33} = 6.6\\text{ A}$$\n\n"
            "Try calculating the individual current in the 50 Ω toaster: $I = \\frac{220}{50}$. What do you get?"
        )

    # 5. Default Socratic Guidance
    weak_str = ", ".join(learner_ctx["weak_concepts"]) if learner_ctx["weak_concepts"] else "Ohm's Law"
    return (
        f"Hello! I am your NeuroAdapt Socratic Physics Tutor.\n\n"
        f"Looking at your learning profile, your current focus area is **{weak_str}**.\n\n"
        "I can help you with:\n"
        "• Explaining any Electricity concept with analogies\n"
        "• Deriving formulas ($V = IR$, $P = VI$, $H = I^2Rt$)\n"
        "• Step-by-step numerical problem solving\n"
        "• Counterfactual thinking challenges\n\n"
        "What specific concept or question would you like to explore right now?"
    )

def log_tutor_conversation(
    db: Session,
    learner_id: str,
    user_message: str,
    tutor_reply: str,
    context_concept: Optional[str] = None
):
    """
    Saves conversation turn in SQLite tutor tables.
    """
    conv = db.query(TutorConversation).filter(TutorConversation.learner_id == learner_id).first()
    if not conv:
        conv = TutorConversation(learner_id=learner_id, title="Physics Learning Session", created_at=utc_now())
        db.add(conv)
        db.commit()
        db.refresh(conv)

    msg_user = TutorMessage(
        conversation_id=conv.id,
        sender="user",
        content=user_message,
        context_concept=context_concept or "",
        created_at=utc_now()
    )
    msg_tutor = TutorMessage(
        conversation_id=conv.id,
        sender="tutor",
        content=tutor_reply,
        context_concept=context_concept or "",
        created_at=utc_now()
    )
    db.add(msg_user)
    db.add(msg_tutor)
    db.commit()
