from datetime import datetime, timezone
from extensions import db


class Project(db.Model):
    """Student portfolio project."""
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech_stack = db.Column(db.String(255), nullable=True)  # Comma-separated: Python, SQL, Tableau
    github_url = db.Column(db.String(255), nullable=True)
    live_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    student = db.relationship("Student", back_populates="projects")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "title": self.title,
            "description": self.description,
            "tech_stack": [s.strip() for s in self.tech_stack.split(",") if s.strip()] if self.tech_stack else [],
            "github_url": self.github_url,
            "live_url": self.live_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Project '{self.title}'>"
