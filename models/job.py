from datetime import datetime, timezone
from extensions import db


class Job(db.Model):
    """Job requisitions posted by recruiters."""
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    role_category = db.Column(db.String(100), nullable=False)  # Software Development, Data Science, Cloud/DevOps, AI/ML
    description = db.Column(db.Text, nullable=False)
    min_cgpa = db.Column(db.Float, default=6.5, nullable=False)
    experience_level = db.Column(db.String(50), default="Fresher (0-1 yrs)")
    location = db.Column(db.String(150), default="Bangalore / Hybrid")
    salary_min = db.Column(db.Float, default=6.0)  # in LPA
    salary_max = db.Column(db.Float, default=12.0) # in LPA
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active', 'closed'
    eligible_departments = db.Column(db.String(255), default="CSE, IT, DS, ECE", nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    company = db.relationship("Company", back_populates="jobs")
    recruiter = db.relationship("Recruiter", back_populates="jobs")
    job_skills = db.relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="job", cascade="all, delete-orphan")
    placements = db.relationship("Placement", back_populates="job")

    @property
    def skills(self):
        """List of skill objects required for this job."""
        return [js.skill for js in self.job_skills if js.skill]

    @property
    def salary_formatted(self):
        """Formatted salary range in LPA."""
        if self.salary_min and self.salary_max:
            return f"₹{self.salary_min:.1f} - {self.salary_max:.1f} LPA"
        elif self.salary_min:
            return f"₹{self.salary_min:.1f} LPA"
        return "Competitive"

    def to_dict(self, detailed: bool = False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "company_logo": self.company.logo_url if self.company else None,
            "title": self.title,
            "role_category": self.role_category,
            "description": self.description,
            "min_cgpa": self.min_cgpa,
            "experience_level": self.experience_level,
            "location": self.location,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_formatted": f"₹{self.salary_min:.1f} - {self.salary_max:.1f} LPA" if self.salary_min and self.salary_max else "Competitive",
            "status": self.status,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "skills": [js.to_dict() for js in self.job_skills]
        }
        if detailed:
            data["applications_count"] = len(self.applications)
        return data

    def __repr__(self):
        return f"<Job {self.id}: '{self.title}' at {self.company.name if self.company else 'Unknown'}>"


class JobSkill(db.Model):
    """Normalized skills required or preferred for a Job."""
    __tablename__ = "job_skills"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    is_required = db.Column(db.Boolean, default=True, nullable=False)  # True = Required, False = Preferred
    importance_weight = db.Column(db.Float, default=1.0, nullable=False)  # 1.0 (Medium), 1.5 (High), 2.0 (Critical)

    # Unique constraint per job-skill
    __table_args__ = (db.UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)

    # Relationships
    job = db.relationship("Job", back_populates="job_skills")
    skill = db.relationship("Skill", back_populates="job_skills")

    def to_dict(self):
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "name": self.skill.name if self.skill else None,
            "category": self.skill.category if self.skill else None,
            "is_required": self.is_required,
            "importance_weight": self.importance_weight
        }

    def __repr__(self):
        return f"<JobSkill job_id={self.job_id} skill='{self.skill.name if self.skill else self.skill_id}' required={self.is_required}>"
