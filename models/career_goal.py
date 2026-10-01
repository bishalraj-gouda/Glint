import json
from datetime import datetime, timezone
from extensions import db


class CareerGoal(db.Model):
    """Structured student career targets and industry preferences."""
    __tablename__ = "career_goals"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = db.Column(db.String(100), nullable=False)
    target_company = db.Column(db.String(150), nullable=True)
    target_industry = db.Column(db.String(100), nullable=True)
    target_skills = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="career_goals")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "target_role": self.target_role,
            "target_company": self.target_company,
            "target_industry": self.target_industry,
            "target_skills": [s.strip() for s in self.target_skills.split(",") if s.strip()] if self.target_skills else [],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<CareerGoal student={self.student_id} target='{self.target_role}'>"


class SkillGapRecord(db.Model):
    """Normalized skill gap analysis records against industry benchmarks."""
    __tablename__ = "skill_gap_analyses"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = db.Column(db.String(100), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    current_level = db.Column(db.String(50), default="none", nullable=False)
    required_level = db.Column(db.String(50), default="intermediate", nullable=False)
    gap_score = db.Column(db.Float, default=0.0, nullable=False)
    recommendation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="skill_gap_analyses")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "target_role": self.target_role,
            "skill": self.skill,
            "current_level": self.current_level,
            "required_level": self.required_level,
            "gap_score": self.gap_score,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<SkillGapRecord student={self.student_id} skill='{self.skill}'>"


class LearningRecommendation(db.Model):
    """Curated or AI-synthesized skill acquisition roadmap tasks and resources."""
    __tablename__ = "learning_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = db.Column(db.String(100), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    resource_url = db.Column(db.String(255), nullable=True)
    priority = db.Column(db.String(30), default="high", nullable=False)
    status = db.Column(db.String(30), default="pending", nullable=False)  # pending, in_progress, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="learning_recommendations")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "skill": self.skill,
            "recommendation": self.recommendation,
            "resource_url": self.resource_url,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<LearningRecommendation student={self.student_id} skill='{self.skill}'>"


class JobMatch(db.Model):
    """AI job recommendation scores, matched/missing skill breakdowns, and explanations."""
    __tablename__ = "job_matches"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = db.Column(db.Float, default=0.0, nullable=False)
    matched_skills_json = db.Column(db.Text, default="[]", nullable=False)
    missing_skills_json = db.Column(db.Text, default="[]", nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="job_matches")
    job = db.relationship("Job")

    @property
    def matched_skills(self):
        try:
            return json.loads(self.matched_skills_json or "[]")
        except Exception:
            return []

    @matched_skills.setter
    def matched_skills(self, val):
        self.matched_skills_json = json.dumps(val)

    @property
    def missing_skills(self):
        try:
            return json.loads(self.missing_skills_json or "[]")
        except Exception:
            return []

    @missing_skills.setter
    def missing_skills(self, val):
        self.missing_skills_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else None,
            "company_name": self.job.company.name if self.job and self.job.company else None,
            "match_score": self.match_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<JobMatch student={self.student_id} job={self.job_id} score={self.match_score}>"


class AIActivityLog(db.Model):
    """Audit log of generative AI calls, student prompts, and synthesized summaries."""
    __tablename__ = "ai_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    action_type = db.Column(db.String(100), nullable=False, index=True)  # twin_synthesis, interview_evaluation, resume_audit
    input_reference = db.Column(db.String(255), nullable=True)
    result_summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="ai_activity_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "action_type": self.action_type,
            "input_reference": self.input_reference,
            "result_summary": self.result_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<AIActivityLog action='{self.action_type}' student={self.student_id}>"
