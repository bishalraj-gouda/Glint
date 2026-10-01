from flask import Blueprint, request, jsonify
from extensions import db
from models.job import Job, JobSkill
from models.skill import Skill
from utils.auth import login_required, recruiter_required, get_current_user

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@jobs_bp.route("", methods=["GET"])
@login_required
def get_jobs():
    """List all active jobs with optional filtering."""
    role_category = request.args.get("category")
    location = request.args.get("location")
    
    query = Job.query.filter_by(status="active")
    if role_category:
        query = query.filter(Job.role_category.ilike(f"%{role_category}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
        
    jobs = query.order_by(Job.created_at.desc()).all()
    return jsonify({"success": True, "count": len(jobs), "jobs": [j.to_dict() for j in jobs]})


@jobs_bp.route("/<int:job_id>", methods=["GET"])
@login_required
def get_job_detail(job_id: int):
    """Retrieve details for a specific job."""
    job = Job.query.get_or_404(job_id)
    return jsonify({"success": True, "job": job.to_dict(detailed=True)})


@jobs_bp.route("", methods=["POST"])
@recruiter_required
def create_job():
    """Create a new job requisition (Recruiters only)."""
    user = get_current_user()
    recruiter = user.recruiter_profile
    if not recruiter:
        return jsonify({"error": "Recruiter profile required"}), 400

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    role_category = data.get("role_category", "Software Development").strip()

    if not title or not description:
        return jsonify({"error": "Job title and description are required"}), 400

    job = Job(
        company_id=recruiter.company_id,
        recruiter_id=recruiter.id,
        title=title,
        role_category=role_category,
        description=description,
        min_cgpa=float(data.get("min_cgpa", 6.5)),
        experience_level=data.get("experience_level", "Fresher (0-1 yrs)"),
        location=data.get("location", "Bangalore / Hybrid"),
        salary_min=float(data.get("salary_min", 6.0)),
        salary_max=float(data.get("salary_max", 12.0)),
        status="active"
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"success": True, "message": "Job created successfully", "job": job.to_dict()}), 201
