import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from database import Base

def utc_now():
    return datetime.utcnow()

# 1. Anonymous Learners (Zero registration/login)
class Learner(Base):
    __tablename__ = "learners"

    id = Column(String(64), primary_key=True, index=True) # e.g. lrn_uuid4
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_active_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    diagnostic_completed = Column(Boolean, default=False, nullable=False)
    streak_days = Column(Integer, default=1, nullable=False)
    display_name = Column(String(100), default="Anonymous Learner", nullable=False)

    masteries = relationship("ConceptMastery", back_populates="learner", cascade="all, delete-orphan")
    answers = relationship("StudentAnswer", back_populates="learner", cascade="all, delete-orphan")
    diagnostics = relationship("DiagnosticAttempt", back_populates="learner", cascade="all, delete-orphan")
    misconceptions = relationship("Misconception", back_populates="learner", cascade="all, delete-orphan")
    revisions = relationship("RevisionSchedule", back_populates="learner", cascade="all, delete-orphan")
    activities = relationship("LearningActivity", back_populates="learner", cascade="all, delete-orphan")
    conversations = relationship("TutorConversation", back_populates="learner", cascade="all, delete-orphan")

# 2. Curriculum Concepts
class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(64), primary_key=True, index=True) # e.g. "ohms-law"
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), default="Electricity", nullable=False)
    order_index = Column(Integer, default=1, nullable=False)

    questions = relationship("Question", back_populates="concept")
    masteries = relationship("ConceptMastery", back_populates="concept")
    revisions = relationship("RevisionSchedule", back_populates="concept")

# 3. Concept Prerequisites (NetworkX DAG representation in DB)
class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    parent_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    child_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)

# 4. Question Bank
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False, default=1, index=True) # 1=Easy, 2=Medium, 3=Hard, 4=Advanced
    options_json = Column(Text, nullable=False) # JSON array of options
    correct_answer = Column(String(256), nullable=False)
    explanation = Column(Text, nullable=False)
    expected_reasoning = Column(Text, nullable=False)
    misconception_distractor_map = Column(Text, default="{}") # JSON mapping option -> misconception
    question_type = Column(String(32), default="conceptual") # conceptual, numerical, counterfactual, application

    concept = relationship("Concept", back_populates="questions")
    answers = relationship("StudentAnswer", back_populates="question")

    def get_options(self):
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    def get_distractor_map(self):
        try:
            return json.loads(self.misconception_distractor_map or "{}")
        except Exception:
            return {}

# 5. Diagnostic Attempts
class DiagnosticAttempt(Base):
    __tablename__ = "diagnostic_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    score_percent = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    weak_concepts_json = Column(Text, default="[]")
    strong_concepts_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    learner = relationship("Learner", back_populates="diagnostics")

# 6. Student Answers
class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_answer = Column(Text, nullable=False)
    reasoning = Column(Text, default="")
    is_correct = Column(Boolean, nullable=False, index=True)
    misconception_detected = Column(String(256), default="")
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    learner = relationship("Learner", back_populates="answers")
    question = relationship("Question", back_populates="answers")

# 7. Concept Mastery Model
class ConceptMastery(Base):
    __tablename__ = "concept_mastery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery_score = Column(Float, default=0.0, nullable=False) # 0.0 - 100.0
    total_attempts = Column(Integer, default=0, nullable=False)
    correct_attempts = Column(Integer, default=0, nullable=False)
    incorrect_attempts = Column(Integer, default=0, nullable=False)
    current_difficulty = Column(Integer, default=1, nullable=False)
    last_practiced_at = Column(DateTime, default=utc_now, nullable=False)
    learning_trend = Column(String(32), default="new", nullable=False) # new, improving, stable, declining
    identified_misconceptions = Column(Text, default="[]")
    next_revision_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("learner_id", "concept_id", name="uq_learner_concept_mastery"),
        Index("ix_mastery_learner_score", "learner_id", "mastery_score"),
    )

    learner = relationship("Learner", back_populates="masteries")
    concept = relationship("Concept", back_populates="masteries")

# 8. Detected Misconceptions
class Misconception(Base):
    __tablename__ = "misconceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    misconception_title = Column(String(256), nullable=False)
    student_reasoning = Column(Text, default="")
    diagnostic_feedback = Column(Text, nullable=False)
    remediation_hint = Column(Text, default="")
    detected_at = Column(DateTime, default=utc_now, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)

    learner = relationship("Learner", back_populates="misconceptions")

# 9. Spaced Repetition Revision Schedule
class RevisionSchedule(Base):
    __tablename__ = "revision_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=False, index=True)
    interval_days = Column(Integer, default=1, nullable=False)
    last_reviewed_at = Column(DateTime, default=utc_now)
    status = Column(String(32), default="pending", nullable=False) # pending, completed, overdue

    __table_args__ = (
        UniqueConstraint("learner_id", "concept_id", name="uq_learner_concept_revision"),
    )

    learner = relationship("Learner", back_populates="revisions")
    concept = relationship("Concept", back_populates="revisions")

# 10. AI Tutor Conversations
class TutorConversation(Base):
    __tablename__ = "tutor_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), default="Physics Discussion")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    learner = relationship("Learner", back_populates="conversations")
    messages = relationship("TutorMessage", back_populates="conversation", cascade="all, delete-orphan")

# 11. AI Tutor Messages
class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("tutor_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(16), nullable=False) # "user" or "tutor"
    content = Column(Text, nullable=False)
    context_concept = Column(String(64), default="")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("TutorConversation", back_populates="messages")

# 12. Learning Activity Log
class LearningActivity(Base):
    __tablename__ = "learning_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(64), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(64), nullable=False) # "diagnostic", "practice", "tutor_chat", "revision"
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    learner = relationship("Learner", back_populates="activities")
