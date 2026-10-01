import json
from datetime import datetime, timezone
from extensions import db


class AICareerTwin(db.Model):
    """Digital twin of student career readiness, skill gaps, and intelligence."""
    __tablename__ = "ai_career_twins"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False)
    readiness_score = db.Column(db.Float, default=50.0, nullable=False)  # 0 to 100 deterministic
    academic_score = db.Column(db.Float, default=50.0, nullable=False)
    skill_score = db.Column(db.Float, default=50.0, nullable=False)
    project_score = db.Column(db.Float, default=50.0, nullable=False)
    interview_score = db.Column(db.Float, default=50.0, nullable=False)
    target_role = db.Column(db.String(100), nullable=False, default="Software Engineer")
    career_level = db.Column(db.String(50), default="Emerging Talent", nullable=False)
    market_competitiveness = db.Column(db.String(100), default="Premium Product Companies", nullable=False)
    verified_strengths_json = db.Column(db.Text, default="[]", nullable=False)
    skill_gaps_json = db.Column(db.Text, default="[]", nullable=False)
    portfolio_gaps_json = db.Column(db.Text, default="[]", nullable=False)
    interview_gaps_json = db.Column(db.Text, default="[]", nullable=False)
    recommended_action = db.Column(db.String(255), default="Complete profile skills and projects", nullable=False)
    ai_explanation = db.Column(db.Text, nullable=True)
    metadata_json_str = db.Column(db.Text, default="{}", nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_calculated = db.synonym("updated_at")

    # Relationship
    student = db.relationship("Student", back_populates="career_twin")

    @property
    def overall_readiness_score(self):
        return int(round(self.readiness_score))

    @overall_readiness_score.setter
    def overall_readiness_score(self, val):
        self.readiness_score = float(val)

    @property
    def strengths(self):
        try:
            return json.loads(self.verified_strengths_json or "[]")
        except Exception:
            return []

    @strengths.setter
    def strengths(self, val):
        self.verified_strengths_json = json.dumps(val)

    @property
    def gaps(self):
        try:
            return json.loads(self.skill_gaps_json or "[]")
        except Exception:
            return []

    @gaps.setter
    def gaps(self, val):
        self.skill_gaps_json = json.dumps(val)

    @property
    def recommendations(self):
        return [self.recommended_action] if self.recommended_action else []

    @recommendations.setter
    def recommendations(self, val):
        if isinstance(val, list) and val:
            self.recommended_action = str(val[0])
        elif isinstance(val, str):
            self.recommended_action = val

    @property
    def metadata_json(self):
        try:
            return json.loads(self.metadata_json_str or "{}")
        except Exception:
            return {}

    @metadata_json.setter
    def metadata_json(self, val):
        self.metadata_json_str = json.dumps(val)

    @property
    def verified_strengths(self):
        return self.strengths

    @property
    def skill_gaps(self):
        return self.gaps

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "readiness_score": round(self.readiness_score, 1),
            "overall_score": self.overall_readiness_score,
            "sub_scores": {
                "academic": self.academic_score,
                "skills": self.skill_score,
                "projects": self.project_score,
                "interview": self.interview_score
            },
            "target_role": self.target_role,
            "career_level": self.career_level,
            "market_competitiveness": self.market_competitiveness,
            "strengths": self.strengths,
            "critical_gaps": self.gaps,
            "recommendations": self.recommendations,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<AICareerTwin id={self.id} student={self.student_id} score={self.readiness_score}%>"
