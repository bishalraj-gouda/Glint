from extensions import db
from models.application import Application
from models.student import Student
from models.job import Job


class ApplicationService:
    """Service handling job applications and status transitions."""

    @staticmethod
    def apply(student_id: int, job_id: int) -> Application:
        student = db.session.get(Student, student_id)
        job = db.session.get(Job, job_id)

        if not student or not job:
            raise ValueError("Student or Job does not exist.")

        status = "eligible" if student.cgpa >= job.min_cgpa else "applied"
        app = Application(
            student_id=student_id,
            job_id=job_id,
            status=status,
            match_score=student.readiness_score
        )
        db.session.add(app)
        db.session.commit()
        return app
