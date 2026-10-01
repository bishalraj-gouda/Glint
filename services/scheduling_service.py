from datetime import date
from extensions import db
from models.interview import Interview


class SchedulingService:
    """Service handling interview coordination."""

    @staticmethod
    def schedule(application_id: int, sched_date: date, sched_time: str, interview_type: str = "technical"):
        interview = Interview(
            application_id=application_id,
            scheduled_date=sched_date,
            scheduled_time=sched_time,
            interview_type=interview_type,
            status="scheduled"
        )
        db.session.add(interview)
        db.session.commit()
        return interview
