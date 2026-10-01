from flask import Blueprint, request, jsonify
from extensions import db
from models.application import Application
from models.job import Job
from utils.auth import login_required, student_required, recruiter_required, get_current_user

applications_bp = Blueprint("applications", __name__, url_prefix="/api/applications")


@applications_bp.route("/apply", methods=["POST"])
@student_required
def apply_to_job():
    """Apply to a job as a student."""
    user = get_current_user()
    student = user.student_profile
    if not student:
        return jsonify({"error": "Student profile required"}), 400

    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Job ID is required"}), 400

    job = db.session.get(Job, job_id)
    if not job or job.status != "active":
        return jsonify({"error": "Job is no longer accepting applications"}), 404

    # Check if already applied
    existing = Application.query.filter_by(job_id=job.id, student_id=student.id).first()
    if existing:
        return jsonify({"error": "You have already applied for this job", "application_id": existing.id}), 409

    # Basic eligibility check
    status = "eligible" if student.cgpa >= job.min_cgpa else "applied"

    application = Application(
        job_id=job.id,
        student_id=student.id,
        status=status,
        match_score=student.readiness_score
    )
    db.session.add(application)
    db.session.commit()

    return jsonify({"success": True, "message": "Application submitted successfully!", "application": application.to_dict()}), 201


@applications_bp.route("/my-applications", methods=["GET"])
@student_required
def my_applications():
    """List applications submitted by logged-in student."""
    user = get_current_user()
    student = user.student_profile
    apps = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return jsonify({"success": True, "count": len(apps), "applications": [a.to_dict() for a in apps]})


@applications_bp.route("/<int:app_id>/status", methods=["PUT", "POST"])
@recruiter_required
def update_application_status(app_id: int):
    """Advance candidate through recruitment pipeline (Recruiter only)."""
    application = Application.query.get_or_404(app_id)
    data = request.get_json(silent=True) or request.form or {}
    new_status = data.get("status")

    valid_statuses = {"applied", "eligible", "ai_matched", "shortlisted", "interview", "selected", "placed", "rejected"}
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status '{new_status}'"}), 400

    application.status = new_status

    if new_status == "placed":
        from models.placement import Placement
        from datetime import datetime, timezone
        existing = Placement.query.filter_by(student_id=application.student_id, job_id=application.job_id).first()
        if not existing:
            placement = Placement(
                student_id=application.student_id,
                job_id=application.job_id,
                company_id=application.job.company_id,
                package_lpa=application.job.salary_max or 10.0,
                placed_date=datetime.now(timezone.utc).date(),
                academic_year="2025-2026"
            )
            db.session.add(placement)

    db.session.commit()

    return jsonify({"success": True, "message": f"Candidate moved to '{new_status}'", "application": application.to_dict()})
