from extensions import db


class Role(db.Model):
    """Role-Based Access Control (RBAC) model."""
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 'STUDENT', 'RECRUITER', 'ADMIN'
    description = db.Column(db.String(255), nullable=True)

    # Role definitions
    STUDENT = "STUDENT"
    RECRUITER = "RECRUITER"
    ADMIN = "ADMIN"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }

    def __repr__(self):
        return f"<Role {self.name}>"


ROLE_STUDENT = Role.STUDENT
ROLE_RECRUITER = Role.RECRUITER
ROLE_ADMIN = Role.ADMIN
