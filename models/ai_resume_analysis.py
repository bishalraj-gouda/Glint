import json
from datetime import datetime, timezone
from extensions import db


class AIResumeAnalysis(db.Model):
    """Resume audit, ATS compatibility score, and keyword gap report."""
    __tablename__ = "ai_resume_analyses"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    target_role = db.Column(db.String(100), default="Software Engineer", nullable=False)
    ats_score = db.Column(db.Float, default=70.0, nullable=False)
    role_alignment_score = db.Column(db.Float, default=70.0, nullable=False)
    strengths_json = db.Column(db.Text, default="[]", nullable=False)
    missing_skills_json = db.Column(db.Text, default="[]", nullable=False)
    missing_keywords_json = db.Column(db.Text, default="[]", nullable=False)
    project_suggestions_json = db.Column(db.Text, default="[]", nullable=False)
    summary = db.Column(db.Text, nullable=True)
    raw_text_snippet = db.Column(db.Text, nullable=True)
    analyzed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.synonym("analyzed_at")

    # Relationships
    student = db.relationship("Student", back_populates="ai_resume_analyses")
    job = db.relationship("Job")

    @property
    def strengths(self):
        try:
            return json.loads(self.strengths_json or "[]")
        except Exception:
            return []

    @strengths.setter
    def strengths(self, val):
        self.strengths_json = json.dumps(val)

    @property
    def extracted_skills(self):
        return self.strengths

    @extracted_skills.setter
    def extracted_skills(self, val):
        self.strengths = val

    @property
    def missing_skills(self):
        try:
            return json.loads(self.missing_skills_json or "[]")
        except Exception:
            return []

    @missing_skills.setter
    def missing_skills(self, val):
        self.missing_skills_json = json.dumps(val)

    @property
    def missing_keywords(self):
        try:
            return json.loads(self.missing_keywords_json or "[]")
        except Exception:
            return []

    @missing_keywords.setter
    def missing_keywords(self, val):
        self.missing_keywords_json = json.dumps(val)

    @property
    def project_suggestions(self):
        try:
            return json.loads(self.project_suggestions_json or "[]")
        except Exception:
            return []

    @project_suggestions.setter
    def project_suggestions(self, val):
        self.project_suggestions_json = json.dumps(val)

    @property
    def suggestions(self):
        return self.project_suggestions

    @suggestions.setter
    def suggestions(self, val):
        self.project_suggestions = val

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "filename": self.filename,
            "target_role": self.target_role,
            "ats_score": round(self.ats_score, 1),
            "role_alignment_score": round(self.role_alignment_score, 1),
            "strengths": self.strengths,
            "missing_skills": self.missing_skills,
            "missing_keywords": self.missing_keywords,
            "project_suggestions": self.project_suggestions,
            "suggestions": self.suggestions,
            "summary": self.summary,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None
        }

    def __repr__(self):
        return f"<AIResumeAnalysis id={self.id} student={self.student_id} ats={self.ats_score}%>"
