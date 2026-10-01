from extensions import db


class Department(db.Model):
    """Academic departments offering degrees."""
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)  # CSE, ECE, IT, etc.
    name = db.Column(db.String(120), nullable=False)

    # Relationships
    students = db.relationship("Student", back_populates="department", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name
        }

    def __str__(self):
        return self.code

    def __repr__(self):
        return f"<Department {self.code}>"
