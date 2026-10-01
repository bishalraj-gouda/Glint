from datetime import datetime, timezone
from extensions import db


class Student(db.Model):
    """Student comprehensive academic and career profile."""
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    year = db.Column(db.Integer, default=4, nullable=False)  # 1st, 2nd, 3rd, 4th year
    cgpa = db.Column(db.Float, default=7.5, nullable=False)
    target_role = db.Column(db.String(100), default="Software Engineer", nullable=False)
    preferred_locations = db.Column(db.String(255), default="Bangalore, Hyderabad, Remote")
    preferred_industries = db.Column(db.String(255), default="Technology, AI, Fintech")
    resume_filename = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    headline = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    portfolio_url = db.Column(db.String(255), nullable=True)
    github_data_json = db.Column(db.Text, default="{}", nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    college = db.Column(db.String(150), default="Campus Institute of Technology", nullable=True)
    degree = db.Column(db.String(100), default="B.Tech", nullable=True)
    branch = db.Column(db.String(100), default="Computer Science & Engineering", nullable=True)
    graduation_year = db.Column(db.Integer, default=2026, nullable=True)
    profile_completion = db.Column(db.Float, default=80.0, nullable=False)
    experience_level = db.Column(db.String(50), default="Fresher (0-1 yrs)", nullable=True)
    resume_url = db.Column(db.String(255), nullable=True)
    readiness_score = db.Column(db.Float, default=70.0, nullable=False)  # 0 to 100
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="student_profile")
    department = db.relationship("Department", back_populates="students")
    student_skills = db.relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")
    projects = db.relationship("Project", back_populates="student", cascade="all, delete-orphan")
    certifications = db.relationship("Certification", back_populates="student", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")
    placements = db.relationship("Placement", back_populates="student")

    # Supabase Architecture Relationships
    resumes = db.relationship("Resume", back_populates="student", cascade="all, delete-orphan", order_by="desc(Resume.created_at)")
    career_goals = db.relationship("CareerGoal", back_populates="student", cascade="all, delete-orphan")
    skill_gap_analyses = db.relationship("SkillGapRecord", back_populates="student", cascade="all, delete-orphan", order_by="desc(SkillGapRecord.created_at)")
    learning_recommendations = db.relationship("LearningRecommendation", back_populates="student", cascade="all, delete-orphan")
    job_matches = db.relationship("JobMatch", back_populates="student", cascade="all, delete-orphan")
    ai_activity_logs = db.relationship("AIActivityLog", back_populates="student", cascade="all, delete-orphan", order_by="desc(AIActivityLog.created_at)")

    # AI Relationships
    career_twin = db.relationship("AICareerTwin", back_populates="student", uselist=False, cascade="all, delete-orphan")
    ai_interview_sessions = db.relationship("AIInterviewSession", back_populates="student", cascade="all, delete-orphan", order_by="desc(AIInterviewSession.created_at)")
    ai_roadmaps = db.relationship("AIRoadmap", back_populates="student", cascade="all, delete-orphan", order_by="desc(AIRoadmap.generated_at)")
    ai_resume_analyses = db.relationship("AIResumeAnalysis", back_populates="student", cascade="all, delete-orphan", order_by="desc(AIResumeAnalysis.analyzed_at)")

    def build_ai_context(self) -> dict:
        """Construct sanitized, structured student context for grounded Gemini intelligence."""
        return {
            "student_id": self.id,
            "name": self.name,
            "roll_number": self.roll_number,
            "department": self.department.code if self.department else "General",
            "year": self.year,
            "cgpa": self.cgpa,
            "target_role": self.target_role,
            "readiness_score": self.readiness_score,
            "verified_skills": [
                {
                    "name": ss.skill.name,
                    "proficiency": ss.proficiency_level,
                    "verified": ss.verified,
                    "category": ss.skill.category
                }
                for ss in self.student_skills if ss.skill
            ],
            "projects": [
                {
                    "title": p.title,
                    "description": p.description,
                    "tech_stack": p.tech_stack
                }
                for p in self.projects
            ],
            "certifications": [
                {
                    "name": c.name,
                    "issuing_org": c.issuing_org
                }
                for c in self.certifications
            ],
            "applications_count": len(self.applications),
            "recent_interview_count": len([i for a in self.applications for i in a.interviews if i.status == "completed"])
        }

    @property
    def full_name(self) -> str:
        """Full name accessor."""
        return self.name

    @property
    def department_obj(self):
        """Compatibility accessor for department relation."""
        return self.department

    @property
    def department_code(self) -> str:
        """Safe department code accessor."""
        return self.department.code if self.department else "General"

    @property
    def department_name(self) -> str:
        """Safe department name accessor."""
        return self.department.name if self.department else "General"

    @property
    def skills(self):
        """List of skill objects with attached proficiency and verified status."""
        result = []
        for ss in self.student_skills:
            if ss.skill:
                skill_obj = ss.skill
                skill_obj.proficiency = ss.proficiency_level or "Intermediate"
                skill_obj.verified = ss.verified
                result.append(skill_obj)
        return result

    @property
    def skills_list(self):
        """Helper to get list of skill dicts."""
        return [ss.to_dict() for ss in self.student_skills]

    @property
    def github_data(self) -> dict:
        """Cached public repository and language telemetry from GitHub."""
        import json
        try:
            return json.loads(self.github_data_json or "{}")
        except Exception:
            return {}

    @github_data.setter
    def github_data(self, val):
        import json
        self.github_data_json = json.dumps(val)

    def to_dict(self, detailed: bool = False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "roll_number": self.roll_number,
            "name": self.name,
            "headline": self.headline,
            "github_url": self.github_url,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "department": self.department.code if self.department else None,
            "department_name": self.department.name if self.department else None,
            "year": self.year,
            "cgpa": self.cgpa,
            "target_role": self.target_role,
            "preferred_locations": self.preferred_locations,
            "preferred_industries": self.preferred_industries,
            "bio": self.bio,
            "phone": self.phone,
            "college": self.college,
            "degree": self.degree,
            "branch": self.branch,
            "graduation_year": self.graduation_year,
            "profile_completion": self.profile_completion,
            "experience_level": self.experience_level,
            "resume_url": self.resume_url,
            "avatar_url": self.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={self.roll_number}",
            "readiness_score": self.readiness_score,
            "skills": [s.to_dict() for s in self.student_skills],
            "github_data": self.github_data
        }
        if detailed:
            data["projects"] = [p.to_dict() for p in self.projects]
            data["certifications"] = [c.to_dict() for c in self.certifications]
            data["applications_count"] = len(self.applications)
        return data

    def __repr__(self):
        return f"<Student {self.roll_number} - {self.name}>"


# Alias for explicit profile naming convention
StudentProfile = Student
