import json
from datetime import datetime, timezone
from extensions import db


class AIRoadmap(db.Model):
    """Personalized adaptive learning roadmap for a student."""
    __tablename__ = "ai_roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    target_role = db.Column(db.String(100), nullable=False)
    horizon_days = db.Column(db.Integer, default=90, nullable=False)  # 7, 30, 60, 90
    progress_percentage = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    milestones_json = db.Column(db.Text, default="[]", nullable=False)
    current_week_focus = db.Column(db.String(255), default="Core Fundamentals", nullable=False)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.synonym("generated_at")

    # Relationships
    student = db.relationship("Student", back_populates="ai_roadmaps")

    def __init__(self, **kwargs):
        if "milestones" in kwargs:
            kwargs["milestones_json"] = json.dumps(kwargs.pop("milestones"))
        super().__init__(**kwargs)

    @property
    def milestones(self):
        try:
            return json.loads(self.milestones_json or "[]")
        except Exception:
            return []

    @milestones.setter
    def milestones(self, data_list):
        self.milestones_json = json.dumps(data_list)

    def set_milestones(self, data_list):
        self.milestones = data_list

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "target_role": self.target_role,
            "horizon_days": self.horizon_days,
            "progress_percentage": self.progress_percentage,
            "is_active": self.is_active,
            "milestones": self.milestones,
            "current_week_focus": self.current_week_focus,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }

    def __repr__(self):
        return f"<AIRoadmap {self.id} student={self.student_id} horizon={self.horizon_days}d>"
