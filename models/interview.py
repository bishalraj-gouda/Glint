from datetime import datetime, timezone
from extensions import db


class Interview(db.Model):
    """Interview scheduling and feedback round."""
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = db.Column(db.Date, nullable=False)
    scheduled_time = db.Column(db.String(20), nullable=False)  # e.g., '10:00 AM'
    interview_type = db.Column(db.String(50), default="technical", nullable=False)  # technical, hr, coding, managerial
    round_number = db.Column(db.Integer, default=1, nullable=False)
    meeting_link_or_venue = db.Column(db.String(255), default="https://meet.google.com/xyz-placementiq")
    interviewer_name = db.Column(db.String(120), default="Technical Lead")
    status = db.Column(db.String(30), default="scheduled", nullable=False)  # scheduled, completed, cancelled
    feedback = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, nullable=True)  # 0 to 100
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    application = db.relationship("Application", back_populates="interviews")

    @property
    def google_calendar_url(self) -> str:
        """Generates a Google Calendar event template link."""
        from urllib.parse import urlencode
        from datetime import datetime as dt, timedelta

        app = self.application
        candidate_name = app.student.name if app and app.student else "Candidate"
        job_title = app.job.title if app and app.job else "Interview"
        company_name = app.job.company.name if app and app.job and app.job.company else "Company"

        title = f"Interview: {candidate_name} - {job_title} ({self.interview_type.capitalize()} Round {self.round_number})"
        
        start_dt = None
        if self.scheduled_date:
            time_str = (self.scheduled_time or "10:00 AM").strip()
            for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p", "%I %p"):
                try:
                    parsed_time = dt.strptime(time_str, fmt).time()
                    start_dt = dt.combine(self.scheduled_date, parsed_time)
                    break
                except ValueError:
                    continue
            if not start_dt:
                start_dt = dt.combine(self.scheduled_date, dt.min.time().replace(hour=10))

        dates = ""
        if start_dt:
            end_dt = start_dt + timedelta(hours=1)
            dates = f"{start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}"

        details = (
            f"PlacementIQ Campus Recruitment Interview\n"
            f"Company: {company_name}\n"
            f"Candidate: {candidate_name}\n"
            f"Role: {job_title}\n"
            f"Round: {self.round_number} ({self.interview_type.capitalize()})\n"
            f"Interviewer: {self.interviewer_name}\n"
            f"Meeting Link: {self.meeting_link_or_venue}"
        )

        params = {
            "action": "TEMPLATE",
            "text": title,
            "details": details,
            "location": self.meeting_link_or_venue or "Virtual Room",
        }
        if dates:
            params["dates"] = dates

        return f"https://calendar.google.com/calendar/render?{urlencode(params)}"

    def to_dict(self):
        app = self.application
        return {
            "id": self.id,
            "application_id": self.application_id,
            "student_id": app.student_id if app else None,
            "student_name": app.student.name if app and app.student else None,
            "job_id": app.job_id if app else None,
            "job_title": app.job.title if app and app.job else None,
            "company_name": app.job.company.name if app and app.job and app.job.company else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time": self.scheduled_time,
            "interview_type": self.interview_type,
            "round_number": self.round_number,
            "meeting_link_or_venue": self.meeting_link_or_venue,
            "interviewer_name": self.interviewer_name,
            "status": self.status,
            "feedback": self.feedback,
            "score": self.score,
            "google_calendar_url": self.google_calendar_url
        }

    def __repr__(self):
        return f"<Interview id={self.id} app={self.application_id} type='{self.interview_type}' status='{self.status}'>"
