from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    """User authentication and identity model with Flask-Login and RBAC support."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    raw_password = db.Column(db.String(255), default="Recruiter@123", nullable=True)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'recruiter', 'admin', 'STUDENT', 'RECRUITER', 'ADMIN'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student_profile = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recruiter_profile = db.relationship("Recruiter", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def get_id(self) -> str:
        """Flask-Login user identifier."""
        return str(self.id)

    @property
    def normalized_role(self) -> str:
        """Returns standard uppercase role ('STUDENT', 'RECRUITER', 'ADMIN')."""
        return (self.role or "").upper()

    def has_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles (case-insensitive)."""
        target_roles = {r.upper() for r in roles}
        return self.normalized_role in target_roles

    def is_student(self) -> bool:
        """Helper checking if user is student."""
        return self.normalized_role == "STUDENT"

    def is_recruiter(self) -> bool:
        """Helper checking if user is recruiter."""
        return self.normalized_role == "RECRUITER"

    def is_admin(self) -> bool:
        """Helper checking if user is admin."""
        return self.normalized_role == "ADMIN"

    def set_password(self, password: str) -> None:
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)
        self.raw_password = password

    def check_password(self, password: str) -> bool:
        """Verify given password against hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "normalized_role": self.normalized_role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
