from datetime import datetime, timezone
from extensions import db


class Placement(db.Model):
    """Successful candidate placement record."""
    __tablename__ = "placements"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    package_lpa = db.Column(db.Float, nullable=False)  # in Lakhs Per Annum
    placed_date = db.Column(db.Date, nullable=False)
    academic_year = db.Column(db.String(20), default="2025-2026", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="placements")
    job = db.relationship("Job", back_populates="placements")
    company = db.relationship("Company", back_populates="placements")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_roll": self.student.roll_number if self.student else None,
            "department": self.student.department.code if self.student and self.student.department else None,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else None,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "package_lpa": self.package_lpa,
            "placed_date": self.placed_date.isoformat() if self.placed_date else None,
            "academic_year": self.academic_year
        }

    def __repr__(self):
        return f"<Placement student={self.student_id} company={self.company_id} package={self.package_lpa} LPA>"
