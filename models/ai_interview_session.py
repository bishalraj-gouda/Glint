import json
from datetime import datetime, timezone
from extensions import db


class AIInterviewSession(db.Model):
    """Interactive mock interview simulator session with adaptive scoring."""
    __tablename__ = "ai_interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    target_role = db.Column(db.String(100), nullable=False, default="Software Engineer")
    interview_type = db.Column(db.String(50), default="technical", nullable=False)  # technical, hr, behavioral, mixed
    difficulty = db.Column(db.String(30), default="intermediate", nullable=False)   # beginner, intermediate, advanced
    total_questions = db.Column(db.Integer, default=5, nullable=False)
    current_question_index = db.Column(db.Integer, default=0, nullable=False)
    average_score = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(30), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    transcript_json = db.Column(db.Text, default="[]", nullable=False)
    feedback_json = db.Column(db.Text, default="{}", nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="ai_interview_sessions")
    job = db.relationship("Job")
    questions = db.relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan", order_by="InterviewQuestion.question_number")
    answers = db.relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "role_title" in kwargs:
            kwargs["target_role"] = kwargs.pop("role_title")
        if "total_score" in kwargs:
            kwargs["average_score"] = float(kwargs.pop("total_score"))
        if "transcript" in kwargs:
            kwargs["transcript_json"] = json.dumps(kwargs.pop("transcript"))
        if "feedback" in kwargs:
            kwargs["feedback_json"] = json.dumps(kwargs.pop("feedback"))
        super().__init__(**kwargs)

    @property
    def role_title(self):
        return self.target_role

    @role_title.setter
    def role_title(self, val):
        self.target_role = val

    @property
    def total_score(self):
        return int(round(self.average_score))

    @total_score.setter
    def total_score(self, val):
        self.average_score = float(val)

    @property
    def transcript(self):
        try:
            return json.loads(self.transcript_json or "[]")
        except Exception:
            return []

    @transcript.setter
    def transcript(self, val):
        self.transcript_json = json.dumps(val)

    @property
    def feedback(self):
        try:
            return json.loads(self.feedback_json or "{}")
        except Exception:
            return {}

    @feedback.setter
    def feedback(self, val):
        self.feedback_json = json.dumps(val)

    def set_transcript(self, data_list):
        self.transcript = data_list

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else None,
            "target_role": self.target_role,
            "role_title": self.role_title,
            "interview_type": self.interview_type,
            "difficulty": self.difficulty,
            "total_questions": self.total_questions,
            "current_question_index": self.current_question_index,
            "average_score": round(self.average_score, 1),
            "total_score": self.total_score,
            "status": self.status,
            "transcript": self.transcript,
            "feedback": self.feedback,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<AIInterviewSession {self.id} student={self.student_id} role='{self.target_role}' status='{self.status}'>"


class InterviewQuestion(db.Model):
    """Normalized individual interview question belonging to an AI interview session."""
    __tablename__ = "interview_questions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(50), default="intermediate", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = db.relationship("AIInterviewSession", back_populates="questions")
    answer = db.relationship("InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question_number": self.question_number,
            "category": self.category,
            "question": self.question,
            "hint": self.hint,
            "difficulty": self.difficulty,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<InterviewQuestion {self.id} (Session {self.session_id}, #{self.question_number})>"


class InterviewAnswer(db.Model):
    """Candidate submitted response to an interview question."""
    __tablename__ = "interview_answers"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = db.relationship("AIInterviewSession", back_populates="answers")
    question = db.relationship("InterviewQuestion", back_populates="answer")
    evaluation = db.relationship("AIEvaluation", back_populates="interview_answer", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question_id": self.question_id,
            "answer": self.answer,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None
        }

    def __repr__(self):
        return f"<InterviewAnswer {self.id} (Question {self.question_id})>"


class AIEvaluation(db.Model):
    """Detailed multi-axis AI evaluation of a candidate answer."""
    __tablename__ = "ai_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True, nullable=False)
    technical_accuracy = db.Column(db.Integer, default=70, nullable=False)
    communication_clarity = db.Column(db.Integer, default=70, nullable=False)
    confidence_delivery = db.Column(db.Integer, default=70, nullable=False)
    depth_completeness = db.Column(db.Integer, default=70, nullable=False)
    overall_score = db.Column(db.Integer, default=70, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    exemplary_model_answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    interview_answer = db.relationship("InterviewAnswer", back_populates="evaluation")

    def to_dict(self):
        return {
            "id": self.id,
            "answer_id": self.answer_id,
            "technical_accuracy": self.technical_accuracy,
            "communication_clarity": self.communication_clarity,
            "confidence_delivery": self.confidence_delivery,
            "depth_completeness": self.depth_completeness,
            "overall_score": self.overall_score,
            "feedback": self.feedback,
            "exemplary_model_answer": self.exemplary_model_answer,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<AIEvaluation {self.id} (Answer {self.answer_id}, Score {self.overall_score})>"
