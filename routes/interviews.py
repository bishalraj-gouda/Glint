from datetime import datetime
from flask import Blueprint, request, jsonify
from extensions import db
from models.interview import Interview
from models.application import Application
from utils.auth import login_required, student_required, recruiter_required, get_current_user

interviews_bp = Blueprint("interviews", __name__, url_prefix="/api/interviews")


@interviews_bp.route("/student", methods=["GET"])
@student_required
def get_student_interviews():
    """List scheduled interviews for current student."""
    user = get_current_user()
    student = user.student_profile
    interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id)
        .order_by(Interview.scheduled_date.asc())
        .all()
    )
    return jsonify({"success": True, "count": len(interviews), "interviews": [i.to_dict() for i in interviews]})


@interviews_bp.route("/recruiter", methods=["GET"])
@recruiter_required
def get_recruiter_interviews():
    """List interviews managed by current recruiter's company."""
    user = get_current_user()
    recruiter = user.recruiter_profile
    job_ids = [j.id for j in recruiter.company.jobs]
    interviews = (
        Interview.query.join(Application)
        .filter(Application.job_id.in_(job_ids))
        .order_by(Interview.scheduled_date.asc())
        .all()
    ) if job_ids else []
    return jsonify({"success": True, "count": len(interviews), "interviews": [i.to_dict() for i in interviews]})


@interviews_bp.route("/schedule", methods=["POST"])
@recruiter_required
def schedule_interview():
    """Schedule a new interview round for an applicant."""
    data = request.get_json(silent=True) or {}
    app_id = data.get("application_id")
    date_str = data.get("scheduled_date")  # 'YYYY-MM-DD'
    time_str = data.get("scheduled_time", "10:00 AM")
    interview_type = data.get("interview_type", "technical")
    round_number = int(data.get("round_number", 1))
    venue = data.get("meeting_link_or_venue", "https://meet.google.com/placementiq-interview")
    interviewer = data.get("interviewer_name", "Technical Lead")

    if not app_id or not date_str:
        return jsonify({"error": "application_id and scheduled_date are required"}), 400

    app = Application.query.get_or_404(app_id)
    app.status = "interview"

    interview = Interview(
        application_id=app.id,
        scheduled_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
        scheduled_time=time_str,
        interview_type=interview_type,
        round_number=round_number,
        meeting_link_or_venue=venue,
        interviewer_name=interviewer,
        status="scheduled"
    )
    db.session.add(interview)
    db.session.commit()

    return jsonify({"success": True, "message": "Interview scheduled successfully", "interview": interview.to_dict()}), 201
