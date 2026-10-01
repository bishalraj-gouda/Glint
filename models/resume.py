from datetime import datetime, timezone
import json
from extensions import db


class Resume(db.Model):
    """Student resume document records and parsed profile telemetry."""
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    file_url = db.Column(db.String(255), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    parsed_data_json = db.Column(db.Text, default="{}", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="resumes")

    @property
    def parsed_data(self):
        try:
            return json.loads(self.parsed_data_json or "{}")
        except Exception:
            return {}

    @parsed_data.setter
    def parsed_data(self, val):
        self.parsed_data_json = json.dumps(val)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "file_url": self.file_url,
            "filename": self.filename,
            "parsed_data": self.parsed_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Resume id={self.id} student={self.student_id} file='{self.filename}'>"
