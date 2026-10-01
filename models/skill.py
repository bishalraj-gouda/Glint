from datetime import datetime, timezone
from extensions import db


class Skill(db.Model):
    """Normalized skill taxonomy model."""
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, default="technical")  # technical, soft, tool, domain
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student_skills = db.relationship("StudentSkill", back_populates="skill", cascade="all, delete-orphan")
    job_skills = db.relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Skill {self.name} ({self.category})>"


class StudentSkill(db.Model):
    """Association model between Student and Skill with proficiency."""
    __tablename__ = "student_skills"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    proficiency_level = db.Column(db.String(20), default="intermediate", nullable=False)  # beginner, intermediate, advanced
    verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Unique constraint per student-skill
    __table_args__ = (db.UniqueConstraint("student_id", "skill_id", name="uq_student_skill"),)

    # Relationships
    student = db.relationship("Student", back_populates="student_skills")
    skill = db.relationship("Skill", back_populates="student_skills")

    def to_dict(self):
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "name": self.skill.name if self.skill else None,
            "category": self.skill.category if self.skill else None,
            "proficiency_level": self.proficiency_level,
            "verified": self.verified
        }

    def __repr__(self):
        return f"<StudentSkill student_id={self.student_id} skill='{self.skill.name if self.skill else self.skill_id}' level='{self.proficiency_level}'>"
