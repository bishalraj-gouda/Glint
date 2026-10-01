import json
from datetime import datetime, timezone
from extensions import db


class Application(db.Model):
    """Job application with tracking pipeline and explainable match score."""
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(
        db.String(30), 
        default="applied", 
        nullable=False
    )  # applied, eligible, ai_matched, shortlisted, interview, selected, placed, rejected
    match_score = db.Column(db.Float, default=0.0, nullable=False)  # 0 to 100
    match_breakdown_json = db.Column(db.Text, nullable=True)  # JSON string of explainability factors
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Unique constraint: a student applies only once to a job
    __table_args__ = (db.UniqueConstraint("job_id", "student_id", name="uq_job_student_application"),)

    # Relationships
    job = db.relationship("Job", back_populates="applications")
    student = db.relationship("Student", back_populates="applications")
    interviews = db.relationship("Interview", back_populates="application", cascade="all, delete-orphan")

    @property
    def breakdown(self):
        """Parse match breakdown JSON."""
        if self.match_breakdown_json:
            try:
                return json.loads(self.match_breakdown_json)
            except Exception:
                return {}
        return {}

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else None,
            "company_name": self.job.company.name if self.job and self.job.company else None,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_roll": self.student.roll_number if self.student else None,
            "student_department": self.student.department.code if self.student and self.student.department else None,
            "status": self.status,
            "match_score": self.match_score,
            "match_breakdown": self.breakdown,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "interviews_count": len(self.interviews)
        }

    def __repr__(self):
        return f"<Application id={self.id} student={self.student_id} job={self.job_id} status='{self.status}'>"
