from datetime import datetime, timezone
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from extensions import db
from models.user import User
from models.recruiter import Recruiter
from models.company import Company
from models.job import Job, JobSkill
from models.skill import Skill
from models.student import Student
from models.application import Application
from models.interview import Interview
from models.placement import Placement
from utils.auth import recruiter_required, get_current_user

recruiter_bp = Blueprint("recruiter", __name__, url_prefix="/recruiter")


@recruiter_bp.route("/dashboard")
@recruiter_required
def dashboard():
    """Recruiter master dashboard shell."""
    user = get_current_user()
    recruiter = user.recruiter_profile if user else None
    
    if not recruiter:
        return redirect(url_for("auth.login"))

    # Dynamic metrics from database
    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
    job_ids = [j.id for j in company_jobs]

    active_jobs_count = len([j for j in company_jobs if j.status == "active"])
    
    total_applicants = 0
    shortlisted_count = 0
    interview_count = 0
    placed_count = 0
    recent_applications = []

    if job_ids:
        all_apps = Application.query.filter(Application.job_id.in_(job_ids)).all()
        total_applicants = len(all_apps)
        shortlisted_count = len([a for a in all_apps if a.status in ("shortlisted", "interview", "selected", "placed")])
        interview_count = len([a for a in all_apps if a.status in ("interview", "selected", "placed")])
        placed_count = len([a for a in all_apps if a.status in ("selected", "placed")])
        recent_applications = (
            Application.query.filter(Application.job_id.in_(job_ids))
            .order_by(Application.applied_at.desc())
            .limit(6)
            .all()
        )

    kpis = {
        "active_jobs": active_jobs_count,
        "total_applicants": total_applicants,
        "shortlisted": shortlisted_count,
        "interviews": interview_count,
        "placed": placed_count
    }

    return render_template(
        "recruiter/dashboard.html",
        recruiter=recruiter,
        company=recruiter.company,
        kpis=kpis,
        jobs=company_jobs,
        recent_applications=recent_applications,
        active_page="dashboard"
    )


@recruiter_bp.route("/post-job", methods=["GET", "POST"])
@recruiter_bp.route("/post-opportunity", methods=["GET", "POST"])
@recruiter_required
def post_job_view():
    """View and handler for publishing new campus job requisitions."""
    user = get_current_user()
    recruiter = user.recruiter_profile if user else None
    if not recruiter:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        data = request.form if request.form else (request.get_json(silent=True) or {})
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        role_category = data.get("role_category", "Software Development").strip()
        location = data.get("location", "Bangalore / Hybrid").strip()
        experience_level = data.get("experience_level", "Fresher (0-1 yrs)").strip()

        if not title or not description:
            flash("Job title and description are required.", "danger")
            return redirect(url_for("recruiter.post_job_view"))

        try:
            min_cgpa = float(data.get("min_cgpa", 7.0))
            salary_min = float(data.get("salary_min", 6.0))
            salary_max = float(data.get("salary_max", 12.0))
        except (ValueError, TypeError):
            min_cgpa = 7.0
            salary_min = 6.0
            salary_max = 12.0

        deadline = None
        deadline_str = data.get("deadline")
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                deadline = None

        job = Job(
            company_id=recruiter.company_id,
            recruiter_id=recruiter.id,
            title=title,
            role_category=role_category,
            description=description,
            min_cgpa=min_cgpa,
            experience_level=experience_level,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            deadline=deadline,
            status="active"
        )
        db.session.add(job)
        db.session.flush()

        # Handle selected skills
        selected_skill_ids = request.form.getlist("skills") if request.form else data.get("skills", [])
        for sid in selected_skill_ids:
            try:
                js = JobSkill(job_id=job.id, skill_id=int(sid), is_required=True, importance_weight=1.5)
                db.session.add(js)
            except Exception:
                continue

        # Handle custom comma-separated skills
        custom_skills_raw = data.get("custom_skills", "")
        if custom_skills_raw:
            for sname in [s.strip() for s in custom_skills_raw.split(",") if s.strip()]:
                sk = Skill.query.filter(Skill.name.ilike(sname)).first()
                if not sk:
                    sk = Skill(name=sname, category="technical")
                    db.session.add(sk)
                    db.session.flush()
                # Attach to job if not already added
                existing_js = JobSkill.query.filter_by(job_id=job.id, skill_id=sk.id).first()
                if not existing_js:
                    js = JobSkill(job_id=job.id, skill_id=sk.id, is_required=True, importance_weight=1.2)
                    db.session.add(js)

        db.session.commit()
        flash(f"Opportunity '{job.title}' posted successfully!", "success")

        if request.is_json:
            return jsonify({"success": True, "message": "Job posted successfully", "job": job.to_dict()}), 201

        return redirect(url_for("recruiter.candidates_view", job_id=job.id))

    # GET request
    skills = Skill.query.order_by(Skill.name.asc()).all()
    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).order_by(Job.created_at.desc()).all()

    return render_template(
        "recruiter/post_job.html",
        recruiter=recruiter,
        company=recruiter.company,
        skills=skills,
        existing_jobs=company_jobs,
        active_page="post_job"
    )


@recruiter_bp.route("/candidates", methods=["GET"])
@recruiter_bp.route("/pipeline", methods=["GET"])
@recruiter_required
def candidates_view():
    """View candidate recruitment pipeline with filtering, stage transitions, and AI match analytics."""
    user = get_current_user()
    recruiter = user.recruiter_profile if user else None
    if not recruiter:
        return redirect(url_for("auth.login"))

    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
    job_ids = [j.id for j in company_jobs]

    if not job_ids:
        return render_template(
            "recruiter/candidates.html",
            recruiter=recruiter,
            company=recruiter.company,
            jobs=[],
            applications=[],
            stage_counts={"all": 0, "applied": 0, "eligible": 0, "shortlisted": 0, "interview": 0, "selected": 0, "placed": 0, "rejected": 0},
            selected_job_id=None,
            selected_stage=None,
            search_query="",
            total_candidates_count=0,
            active_page="candidates"
        )

    # Filter parameters
    selected_job_id = request.args.get("job_id", type=int)
    selected_stage = request.args.get("stage", "").strip()
    search_query = request.args.get("q", "").strip()

    # Pre-calculate counts across the selected requisition or all requisitions
    count_base = Application.query.filter(Application.job_id.in_(job_ids))
    if selected_job_id:
        count_base = count_base.filter(Application.job_id == selected_job_id)

    all_stage_apps = count_base.all()
    stage_counts = {
        "all": len(all_stage_apps),
        "applied": len([a for a in all_stage_apps if a.status == "applied"]),
        "eligible": len([a for a in all_stage_apps if a.status == "eligible"]),
        "shortlisted": len([a for a in all_stage_apps if a.status == "shortlisted"]),
        "interview": len([a for a in all_stage_apps if a.status == "interview"]),
        "selected": len([a for a in all_stage_apps if a.status == "selected"]),
        "placed": len([a for a in all_stage_apps if a.status == "placed"]),
        "rejected": len([a for a in all_stage_apps if a.status == "rejected"])
    }

    # Query filtered applications
    app_query = Application.query.filter(Application.job_id.in_(job_ids))
    if selected_job_id:
        app_query = app_query.filter(Application.job_id == selected_job_id)
    if selected_stage and selected_stage != "all":
        app_query = app_query.filter(Application.status == selected_stage)
    if search_query:
        app_query = app_query.join(Student).filter(
            db.or_(
                Student.name.ilike(f"%{search_query}%"),
                Student.roll_number.ilike(f"%{search_query}%"),
                Student.target_role.ilike(f"%{search_query}%")
            )
        )

    applications = app_query.order_by(Application.match_score.desc(), Application.applied_at.desc()).all()

    return render_template(
        "recruiter/candidates.html",
        recruiter=recruiter,
        company=recruiter.company,
        jobs=company_jobs,
        applications=applications,
        stage_counts=stage_counts,
        selected_job_id=selected_job_id,
        selected_stage=selected_stage,
        search_query=search_query,
        total_candidates_count=len(all_stage_apps),
        active_page="candidates"
    )


@recruiter_bp.route("/candidates/<int:app_id>/status", methods=["POST"])
@recruiter_required
def update_candidate_status(app_id: int):
    """Advance candidate through recruitment stages (Shortlist, Interview, Select, Placed, Rejected)."""
    user = get_current_user()
    recruiter = user.recruiter_profile
    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
    job_ids = [j.id for j in company_jobs]

    application = Application.query.get_or_404(app_id)
    if application.job_id not in job_ids:
        flash("You are not authorized to update applications for this requisition.", "danger")
        return redirect(url_for("recruiter.candidates_view"))

    data = request.form if request.form else (request.get_json(silent=True) or {})
    new_status = data.get("status")

    valid_statuses = {"applied", "eligible", "ai_matched", "shortlisted", "interview", "selected", "placed", "rejected"}
    if new_status not in valid_statuses:
        flash(f"Invalid status '{new_status}' provided.", "danger")
        return redirect(request.referrer or url_for("recruiter.candidates_view"))

    application.status = new_status

    # If marked as placed, record in placements table if not already present
    if new_status == "placed":
        existing_placement = Placement.query.filter_by(student_id=application.student_id, job_id=application.job_id).first()
        if not existing_placement:
            pkg = application.job.salary_max or 10.0
            placement = Placement(
                student_id=application.student_id,
                job_id=application.job_id,
                company_id=recruiter.company_id,
                package_lpa=pkg,
                placed_date=datetime.now(timezone.utc).date(),
                academic_year="2025-2026"
            )
            db.session.add(placement)

    db.session.commit()
    flash(f"Moved {application.student.name} to '{new_status.replace('_', ' ').capitalize()}'.", "success")

    if request.is_json:
        return jsonify({"success": True, "status": new_status, "application": application.to_dict()})

    return redirect(request.referrer or url_for("recruiter.candidates_view"))


@recruiter_bp.route("/schedule", methods=["GET", "POST"])
@recruiter_bp.route("/interviews", methods=["GET", "POST"])
@recruiter_bp.route("/interview-schedule", methods=["GET", "POST"])
@recruiter_required
def schedule_view():
    """View and manage interview calendar and rounds."""
    user = get_current_user()
    recruiter = user.recruiter_profile
    if not recruiter:
        return redirect(url_for("auth.login"))

    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
    job_ids = [j.id for j in company_jobs]

    if request.method == "POST":
        data = request.form if request.form else (request.get_json(silent=True) or {})
        app_id = data.get("application_id", type=int)
        date_str = data.get("scheduled_date")
        time_str = data.get("scheduled_time", "10:00 AM")
        interview_type = data.get("interview_type", "technical")
        round_number = int(data.get("round_number", 1))
        venue = data.get("meeting_link_or_venue", "https://meet.google.com/placementiq-interview")
        interviewer = data.get("interviewer_name", f"{recruiter.name} (Technical Panel)")

        if not app_id or not date_str:
            flash("Candidate and interview date are required.", "danger")
            return redirect(url_for("recruiter.schedule_view"))

        app = Application.query.get_or_404(app_id)
        if app.job_id not in job_ids:
            flash("Unauthorized candidate selected.", "danger")
            return redirect(url_for("recruiter.schedule_view"))

        try:
            sched_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for("recruiter.schedule_view"))

        # Update application stage to 'interview'
        app.status = "interview"

        interview = Interview(
            application_id=app.id,
            scheduled_date=sched_date,
            scheduled_time=time_str,
            interview_type=interview_type,
            round_number=round_number,
            meeting_link_or_venue=venue,
            interviewer_name=interviewer,
            status="scheduled"
        )
        db.session.add(interview)
        db.session.commit()

        flash(f"Interview scheduled successfully for {app.student.name} ({app.job.title}) on {sched_date.strftime('%d %b %Y')} at {time_str}!", "success")

        if request.is_json:
            return jsonify({"success": True, "interview": interview.to_dict()}), 201

        return redirect(url_for("recruiter.schedule_view"))

    # GET request
    interviews = []
    if job_ids:
        query = (
            Interview.query.join(Application)
            .filter(Application.job_id.in_(job_ids))
            .order_by(Interview.scheduled_date.asc())
        )
        status_filter = request.args.get("status")
        if status_filter in ("scheduled", "completed", "cancelled"):
            query = query.filter(Interview.status == status_filter)
        interviews = query.all()

    # Metrics
    all_company_interviews = (
        Interview.query.join(Application)
        .filter(Application.job_id.in_(job_ids))
        .all()
    ) if job_ids else []
    upcoming_count = len([i for i in all_company_interviews if i.status == "scheduled"])
    completed_count = len([i for i in all_company_interviews if i.status == "completed"])

    # Eligible candidate applicants for interview scheduling dropdown
    eligible_candidates = []
    if job_ids:
        eligible_candidates = (
            Application.query.filter(
                Application.job_id.in_(job_ids),
                Application.status.in_(("shortlisted", "interview", "eligible", "applied"))
            )
            .order_by(Application.match_score.desc())
            .all()
        )

    selected_candidate_id = request.args.get("candidate_id", type=int) or request.args.get("app_id", type=int)

    return render_template(
        "recruiter/schedule.html",
        recruiter=recruiter,
        company=recruiter.company,
        interviews=interviews,
        upcoming_count=upcoming_count,
        completed_count=completed_count,
        eligible_candidates=eligible_candidates,
        selected_candidate_id=selected_candidate_id,
        filter_status=request.args.get("status"),
        active_page="schedule"
    )


@recruiter_bp.route("/schedule/<int:interview_id>/update", methods=["POST"])
@recruiter_required
def update_interview(interview_id: int):
    """Update interview evaluation score, feedback, or status."""
    user = get_current_user()
    recruiter = user.recruiter_profile

    interview = Interview.query.get_or_404(interview_id)
    if interview.application.job.company_id != recruiter.company_id:
        flash("Unauthorized interview operation.", "danger")
        return redirect(url_for("recruiter.schedule_view"))

    action = request.form.get("action")
    if action == "cancel":
        interview.status = "cancelled"
        db.session.commit()
        flash("Interview round cancelled.", "warning")
        return redirect(url_for("recruiter.schedule_view"))

    # Evaluation scorecard submission
    score_val = request.form.get("score")
    feedback_val = request.form.get("feedback")
    advance_status = request.form.get("advance_status")

    if score_val is not None and score_val != "":
        try:
            interview.score = float(score_val)
        except ValueError:
            pass

    if feedback_val is not None:
        interview.feedback = feedback_val.strip()

    interview.status = "completed"

    if advance_status in ("interview", "selected", "placed", "rejected"):
        interview.application.status = advance_status
        if advance_status == "placed":
            existing_placement = Placement.query.filter_by(student_id=interview.application.student_id, job_id=interview.application.job_id).first()
            if not existing_placement:
                pkg = interview.application.job.salary_max or 10.0
                placement = Placement(
                    student_id=interview.application.student_id,
                    job_id=interview.application.job_id,
                    company_id=recruiter.company_id,
                    package_lpa=pkg,
                    placed_date=datetime.now(timezone.utc).date(),
                    academic_year="2025-2026"
                )
                db.session.add(placement)

    db.session.commit()
    flash(f"Evaluation scorecard updated for {interview.application.student.name}!", "success")
    return redirect(url_for("recruiter.schedule_view"))


@recruiter_bp.route("/api/kpis", methods=["GET"])
@recruiter_required
def api_kpis():
    """Return live recruiter KPI counts."""
    user = get_current_user()
    recruiter = user.recruiter_profile
    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).all()
    job_ids = [j.id for j in company_jobs]
    
    total_applicants = 0
    if job_ids:
        total_applicants = Application.query.filter(Application.job_id.in_(job_ids)).count()

    return jsonify({
        "active_jobs": len(company_jobs),
        "total_applicants": total_applicants,
        "company": recruiter.company.name if recruiter.company else None
    })


@recruiter_bp.route("/ai/candidate-matcher", methods=["GET", "POST"])
@recruiter_bp.route("/candidate-matching", methods=["GET", "POST"])
@recruiter_bp.route("/candidate-matcher", methods=["GET", "POST"])
@recruiter_required
def candidate_matching_page():
    """Explicit recruiter navigation route for AI Candidate Matcher."""
    from routes.ai.recruiter_ai import candidate_matching_page as render_matcher
    return render_matcher()


@recruiter_bp.route("/batch-resume-parser", methods=["GET"])
@recruiter_bp.route("/resumes/batch", methods=["GET"])
@recruiter_required
def batch_resume_parser_view():
    """Redirects to the AI Candidate Matching interface."""
    return redirect(url_for("recruiter_ai.candidate_matching_page"))


@recruiter_bp.route("/api/batch-parse-resumes", methods=["POST"])
@recruiter_required
def api_batch_parse_resumes():
    """Multi-file upload endpoint handling PDF/Docx files to parse skills/experience into candidate profiles."""
    from services.batch_resume_service import BatchResumeService

    files = request.files.getlist("resumes") or request.files.getlist("files")
    if not files or len(files) == 0:
        return jsonify({"error": "No resume files uploaded."}), 400

    target_job_id = request.form.get("job_id", type=int)
    results = BatchResumeService.process_batch(files, target_job_id=target_job_id)

    return jsonify({
        "success": True,
        "total_files": len(files),
        "parsed_count": len([r for r in results if r.get("status") == "parsed"]),
        "candidates": results
    })


@recruiter_bp.route("/api/import-parsed-candidate", methods=["POST"])
@recruiter_required
def api_import_parsed_candidate():
    """Imports or updates a parsed candidate into the student pool and candidate pipeline."""
    from services.batch_resume_service import BatchResumeService

    data = request.get_json() or {}
    job_id = data.get("job_id")
    candidate_data = data.get("candidate", {})

    if not candidate_data:
        return jsonify({"error": "Candidate data required"}), 400

    result = BatchResumeService.import_candidate_to_database(candidate_data, job_id=job_id)
    return jsonify(result)

