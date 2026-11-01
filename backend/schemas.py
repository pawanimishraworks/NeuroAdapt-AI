from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# LEARNER SCHEMAS
# ----------------------------------------------------------------------------
class LearnerStartRequest(BaseModel):
    learner_id: Optional[str] = Field(default=None, description="Existing anonymous learner ID, if restoring session")
    display_name: Optional[str] = Field(default=None, max_length=100)

class LearnerProfileResponse(BaseModel):
    learner_id: str
    display_name: str
    diagnostic_completed: bool
    streak_days: int
    created_at: str
    total_attempts: int
    overall_mastery: float

class LearnerResetRequest(BaseModel):
    learner_id: str
    confirm: bool = Field(default=False)

# ----------------------------------------------------------------------------
# QUESTION & ASSESSMENT SCHEMAS
# ----------------------------------------------------------------------------
class QuestionResponse(BaseModel):
    id: int
    concept_id: str
    prompt: str
    difficulty: int
    options: List[str]
    question_type: str

class DiagnosticItemAnswer(BaseModel):
    question_id: int
    selected_answer: str
    reasoning: Optional[str] = ""

class DiagnosticSubmitRequest(BaseModel):
    learner_id: str
    answers: List[DiagnosticItemAnswer]

class DiagnosticResultResponse(BaseModel):
    score_percent: float
    total_questions: int
    correct_count: int
    strong_concepts: List[str]
    weak_concepts: List[str]
    concept_breakdown: List[Dict[str, Any]]
    recommendations: List[str]

# ----------------------------------------------------------------------------
# ADAPTIVE ANSWER SUBMISSION & FEEDBACK
# ----------------------------------------------------------------------------
class AnswerSubmitRequest(BaseModel):
    learner_id: str
    question_id: int
    answer: str = Field(min_length=1)
    reasoning: Optional[str] = ""

class AnswerFeedbackResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str
    concept_id: str
    previous_mastery: float
    new_mastery: float
    mastery_delta: float
    difficulty_calibrated: int
    misconception_detected: Optional[str] = None
    misconception_explanation: Optional[str] = None
    remediation_hint: Optional[str] = None
    next_revision_due: str
    revision_interval_days: int

# ----------------------------------------------------------------------------
# REASONING ANALYSIS
# ----------------------------------------------------------------------------
class AnalyzeReasoningRequest(BaseModel):
    learner_id: str
    concept_id: str
    question_prompt: str
    student_reasoning: str = Field(min_length=1)
    selected_answer: Optional[str] = ""

# ----------------------------------------------------------------------------
# AI TUTOR SCHEMAS
# ----------------------------------------------------------------------------
class TutorChatRequest(BaseModel):
    learner_id: str
    message: str = Field(min_length=1, max_length=2000)
    context_concept: Optional[str] = None

class TutorGenerateQuestionRequest(BaseModel):
    learner_id: str
    concept_id: str
    difficulty: Optional[int] = 2

# ----------------------------------------------------------------------------
# REVISION SCHEMAS
# ----------------------------------------------------------------------------
class RevisionCompleteRequest(BaseModel):
    learner_id: str
    concept_id: str
    recalled_successfully: bool
