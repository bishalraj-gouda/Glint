from extensions import db
from models.student import Student
from models.skill import Skill, StudentSkill
from models.project import Project
from models.certification import Certification


class ProfileService:
    """Service layer for student profile operations."""

    @staticmethod
    def get_student_by_user_id(user_id: int):
        return Student.query.filter_by(user_id=user_id).first()

    @staticmethod
    def calculate_readiness_score(student: Student) -> float:
        """
        Base calculation of student placement readiness score:
        - CGPA weight: 25% (scale 0-10 -> 0-25)
        - Skills count: 35% (up to 7 skills = 35)
        - Projects: 25% (up to 3 projects = 25)
        - Certifications: 15% (up to 2 certs = 15)
        """
        cgpa_score = min(25.0, (student.cgpa / 10.0) * 25.0)
        skills_score = min(35.0, (len(student.student_skills) / 7.0) * 35.0)
        projects_score = min(25.0, (len(student.projects) / 3.0) * 25.0)
        certs_score = min(15.0, (len(student.certifications) / 2.0) * 15.0)

        total = round(cgpa_score + skills_score + projects_score + certs_score, 1)
        student.readiness_score = total
        db.session.commit()
        return total
