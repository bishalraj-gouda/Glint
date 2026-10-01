from datetime import datetime, timezone
from extensions import db


class Certification(db.Model):
    """Student professional certifications."""
    __tablename__ = "certifications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    issuing_org = db.Column(db.String(150), nullable=False)  # AWS, Google, Coursera, etc.
    issue_date = db.Column(db.Date, nullable=True)
    credential_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    student = db.relationship("Student", back_populates="certifications")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "issuing_org": self.issuing_org,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "credential_url": self.credential_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Certification '{self.name}' by {self.issuing_org}>"
