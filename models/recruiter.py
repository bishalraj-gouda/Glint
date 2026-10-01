from extensions import db


class Recruiter(db.Model):
    """Company recruiter profiles."""
    __tablename__ = "recruiters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(100), default="Talent Acquisition Specialist")
    phone = db.Column(db.String(30), nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="recruiter_profile")
    company = db.relationship("Company", back_populates="recruiters")
    jobs = db.relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "name": self.name,
            "designation": self.designation,
            "phone": self.phone
        }

    def __repr__(self):
        return f"<Recruiter {self.name} ({self.company.name if self.company else 'No Company'})>"


# Alias for explicit profile naming convention
RecruiterProfile = Recruiter
