# NeuroAdapt AI – Adaptive Learning Platform (Hackathon MVP)

An intelligent, AI-powered cognitive adaptive learning platform built for Class 10 Physics (Electricity). It features an interactive concept prerequisite DAG, Bayesian/weighted cognitive mastery tracking, reasoning-based misconception detection, Socratic AI tutoring, and spaced repetition scheduling.

---

## 1. System Architecture

```
D:\NeuroAdapt-AI/
├── index.html               # Welcome Page (No login required - frictionless entry)
├── chat.html                # Socratic AI Tutor Interface
├── dashboard.html           # Live Student Cognitive Mastery Dashboard & DAG Knowledge Map
├── test.html                # Adaptive & Diagnostic Assessment Centre
├── teacher.html             # Teacher Cohort Analytics & Instructional Interventions
├── css/style.css            # Complete UI design system (preserved)
├── js/script.js             # Unified frontend controller & API caller
└── backend/
    ├── database.py          # SQLAlchemy SQLite connection & sessionmaker
    ├── models.py            # 12 SQLAlchemy ORM models
    ├── schemas.py           # Pydantic validation schemas
    ├── seed_data.py         # 9 concepts, prerequisites, and 27+ quality questions
    ├── concepts.py          # NetworkX Directed Acyclic Graph (DAG) operations
    ├── mastery.py           # Weighted cognitive mastery update algorithm
    ├── adaptive_engine.py   # Adaptive question selector & calibrated difficulties
    ├── misconception.py     # Distractor tagging & reasoning pattern detection
    ├── tutor.py             # Socratic AI tutor (Gemini + offline fallback)
    ├── revision.py          # Spaced repetition revision scheduling (SM-2)
    ├── dashboard.py         # Live student and teacher metrics aggregation
    ├── main.py              # FastAPI application router & static file server
    └── test_system.py       # 23-point automated verification test suite
```

---

## 2. Quickstart

### Prerequisites
- Python 3.10 or newer

### Start Backend Server
```powershell
cd D:\NeuroAdapt-AI\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- Application URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Run the 23-Point Verification Test Suite
```powershell
python backend/test_system.py
```

---

## 3. Core Modules & Capabilities

1. **Anonymous Learner Model**:
   - Zero login/password friction.
   - Generates unpredictable anonymous IDs (`lrn_XXXXXXXX`) stored in `localStorage`.
   - All progress persists in SQLite across reloads.
   - Separate isolated learning records for each browser/tab.
   - "Start New Learning Journey" with confirmation reset.

2. **Module 1 – Diagnostic Assessment**:
   - 27+ questions across 9 Class 10 Electricity concepts.
   - Captures student reasoning alongside multiple-choice selections.
   - Evaluates concept-wise and overall baseline mastery.

3. **Module 2 – Concept Graph (NetworkX)**:
   - 9 curriculum nodes and 10 prerequisite edges verified as a Directed Acyclic Graph.
   - Prerequisite dependency tracking: identifies weak predecessor gaps.

4. **Module 3 – Learner Mastery Model**:
   - Weighted cognitive updates factoring in previous mastery, difficulty (Levels 1–4), correctness, and reasoning quality.
   - Single mistake dampening: one incorrect answer does not destroy established mastery.

5. **Module 4 – Adaptive Question Engine**:
   - Calibrates question difficulty: Easy (0–30%), Medium (31–60%), Hard (61–85%), Advanced (86–100%).
   - Excludes recently answered questions to prevent repetition.

6. **Module 5 – Reasoning-Based Misconception Detection**:
   - Distractor mapping + heuristic keyword pattern analysis on free-form student reasoning.
   - Detects formula inversions ($V \times R$), current attenuation ("used up" charge), voltage-current confusion, and parallel resistance errors.

7. **Module 6 – AI Socratic Tutor**:
   - Context-aware tutoring tailored to the student's actual SQLite concept mastery.
   - Explains concepts with physical analogies, step-by-step numerical solutions, and counterfactual questions.
   - Gemini LLM integration with reliable offline rule-based fallback.

8. **Module 7 – Spaced Repetition**:
   - SuperMemo-inspired intervals: Very weak (1d), Weak (2d), Improving (4d), Strong (10d).
   - Surfaces due concepts on the dashboard with one-click review.

9. **Module 8 & 10 – Student Dashboard & Recommendations**:
   - Live metrics: overall accuracy %, concept mastery bars, active misconceptions, due revisions.
   - Interactive NetworkX Concept Map viewer.
   - Chart.js learning progress timeline graph.
   - Personalized pedagogical recommendations.

10. **Module 9 – Teacher Cohort Dashboard**:
    - Aggregates cohort performance across all anonymous student records.
    - Class-wide mastery averages, frequent misconceptions, instructional interventions, and student roster table.
