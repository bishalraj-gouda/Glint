from extensions import db


class Company(db.Model):
    """Recruiting companies and organizations."""
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    website = db.Column(db.String(255), nullable=True)
    industry = db.Column(db.String(100), nullable=False)  # Fintech, Healthtech, SaaS, AI, etc.
    logo_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(150), nullable=True)

    # Relationships
    recruiters = db.relationship("Recruiter", back_populates="company", cascade="all, delete-orphan")
    jobs = db.relationship("Job", back_populates="company", cascade="all, delete-orphan")
    placements = db.relationship("Placement", back_populates="company")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "website": self.website,
            "industry": self.industry,
            "logo_url": self.logo_url,
            "description": self.description,
            "location": self.location
        }

    def __repr__(self):
        return f"<Company {self.name}>"
