from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from extensions import db
from models.user import User
from models.student import Student
from models.application import Application
from models.interview import Interview
from models.job import Job
from utils.auth import student_required, get_current_user

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@student_required
def dashboard():
    """Student master dashboard shell with foundational layout and KPI placeholders."""
    user = get_current_user()
    student = user.student_profile if user else None
    
    if not student and user:
        # Gracefully auto-provision base profile if student record wasn't created yet
        try:
            from models.department import Department
            dept = Department.query.first()
            student = Student(
                user_id=user.id,
                name=user.email.split("@")[0].replace(".", " ").title(),
                roll_number=f"STU{user.id:04d}",
                department_id=dept.id if dept else 1,
                target_role="Software Engineer",
                cgpa=7.5,
                readiness_score=70.0
            )
            db.session.add(student)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return redirect(url_for("auth.login"))
    elif not student:
        return redirect(url_for("auth.login"))

    # Fetch applications count and latest interviews for shell display
    recent_apps = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).limit(5).all()
    upcoming_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id, Interview.status == "scheduled")
        .order_by(Interview.scheduled_date.asc())
        .limit(3)
        .all()
    )
    # Query all active campus drives
    active_jobs = Job.query.filter_by(status="active").order_by(Job.id.desc()).all()

    return render_template(
        "student/dashboard.html",
        student=student,
        recent_apps=recent_apps,
        upcoming_interviews=upcoming_interviews,
        active_jobs=active_jobs,
        recommended_jobs=active_jobs,
        active_page="dashboard"
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@student_required
def profile_view():
    """Student comprehensive profile, external portfolio handles, and GitHub integration."""
    from flask import flash
    from services.github_service import GitHubService

    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        student.headline = request.form.get("headline", "").strip()
        student.bio = request.form.get("bio", "").strip()
        student.github_url = request.form.get("github_url", "").strip()
        student.linkedin_url = request.form.get("linkedin_url", "").strip()
        student.portfolio_url = request.form.get("portfolio_url", "").strip()
        student.target_role = request.form.get("target_role", student.target_role).strip()
        student.preferred_locations = request.form.get("preferred_locations", student.preferred_locations).strip()
        student.preferred_industries = request.form.get("preferred_industries", student.preferred_industries).strip()

        # If sync requested or github url updated, trigger GitHub taxonomy enrichment
        sync_github = request.form.get("sync_github") == "1"
        if sync_github and student.github_url:
            res = GitHubService.enrich_student_from_github(student, student.github_url)
            if "error" in res:
                flash(f"Profile saved, but GitHub sync notice: {res['error']}", "warning")
            else:
                added = res.get("newly_added_skills", [])
                skill_msg = f" Discovered and verified skills: {', '.join(added)}." if added else ""
                flash(f"Profile and GitHub data synced successfully!{skill_msg}", "success")
        else:
            db.session.commit()
            flash("Profile updated successfully!", "success")

    return render_template(
        "student/profile.html",
        student=student,
        active_page="profile"
    )


@student_bp.route("/profile/skill/add", methods=["POST"])
@student_required
def add_skill():
    """Add a new verified technical skill to student profile."""
    from models.skill import Skill, StudentSkill
    from flask import flash
    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    data = request.get_json(silent=True) or request.form
    skill_name = data.get("skill_name", "").strip()
    proficiency = data.get("proficiency", "intermediate").strip().lower()
    if proficiency not in ["beginner", "intermediate", "advanced", "expert"]:
        proficiency = "intermediate"

    if skill_name:
        # Case-insensitive lookup or create
        skill = Skill.query.filter(Skill.name.ilike(skill_name)).first()
        if not skill:
            skill = Skill(name=skill_name, category="technical")
            db.session.add(skill)
            db.session.flush()

        existing = StudentSkill.query.filter_by(student_id=student.id, skill_id=skill.id).first()
        if existing:
            existing.proficiency_level = proficiency
        else:
            new_ss = StudentSkill(
                student_id=student.id,
                skill_id=skill.id,
                proficiency_level=proficiency,
                verified=False
            )
            db.session.add(new_ss)
        db.session.commit()

        if request.is_json:
            return jsonify({
                "success": True,
                "skill_id": skill.id,
                "skill_name": skill.name,
                "proficiency": proficiency
            })
        flash(f"Added skill: {skill.name} ({proficiency.capitalize()})", "success")
        return redirect(url_for("student.profile_view") + "#skills-edit-section")

    if request.is_json:
        return jsonify({"error": "Skill name required"}), 400
    flash("Please enter a valid skill name.", "warning")
    return redirect(url_for("student.profile_view") + "#skills-edit-section")


@student_bp.route("/profile/skill/<int:skill_id>/delete", methods=["POST"])
@student_required
def delete_skill(skill_id):
    """Remove a verified skill from student profile."""
    from models.skill import StudentSkill
    from flask import flash
    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    ss = StudentSkill.query.filter_by(student_id=student.id, skill_id=skill_id).first()
    if ss:
        db.session.delete(ss)
        db.session.commit()
        if request.is_json:
            return jsonify({"success": True})
        flash("Skill removed from profile.", "success")
    else:
        if request.is_json:
            return jsonify({"error": "Skill not found on profile"}), 404
        flash("Skill not found.", "warning")

    return redirect(url_for("student.profile_view") + "#skills-edit-section")


@student_bp.route("/api/github/sync", methods=["POST"])
@student_required
def api_sync_github():
    """On-demand REST API to synchronize GitHub profile, repos, and verified skill taxonomy."""
    from services.github_service import GitHubService

    user = get_current_user()
    student = user.student_profile
    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    payload = request.get_json(silent=True) or {}
    github_url = payload.get("github_url") or student.github_url

    if not github_url:
        return jsonify({"error": "No GitHub URL or handle provided"}), 400

    result = GitHubService.enrich_student_from_github(student, github_url)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400

    return jsonify({
        "success": True,
        "github_data": result,
        "message": f"Successfully synchronized {result.get('public_repos_count', 0)} repositories and {len(result.get('primary_languages', []))} primary languages."
    })


@student_bp.route("/jobs")
@student_required
def jobs_view():
    """Student ongoing campus recruitment drives and opportunities view."""
    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    # Fetch active campus drives
    jobs = Job.query.filter_by(status="active").order_by(Job.id.desc()).all()
    applied_job_ids = [app.job_id for app in student.applications]

    # Computed drive metrics
    total_drives = len(jobs)
    eligible_drives = sum(1 for j in jobs if student.cgpa >= j.min_cgpa)
    applied_count = len(applied_job_ids)

    # Top package & unique role categories
    max_salary = 0.0
    categories = set()
    for j in jobs:
        sal = j.salary_max or j.salary_min or 0.0
        if sal > max_salary:
            max_salary = sal
        if j.role_category:
            categories.add(j.role_category)

    max_salary_str = f"₹{max_salary:.1f} LPA" if max_salary > 0 else "Competitive"

    return render_template(
        "student/jobs.html",
        student=student,
        jobs=jobs,
        applied_job_ids=applied_job_ids,
        total_drives=total_drives,
        eligible_drives=eligible_drives,
        applied_count=applied_count,
        max_salary_str=max_salary_str,
        categories=sorted(list(categories)),
        active_page="jobs"
    )


@student_bp.route("/applications")
@student_required
def applications_view():
    """Student applications history view."""
    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    apps = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    upcoming_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id, Interview.status == "scheduled")
        .order_by(Interview.scheduled_date.asc())
        .all()
    )
    completed_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id, Interview.status != "scheduled")
        .order_by(Interview.scheduled_date.desc())
        .all()
    )
    upcoming_count = len(upcoming_interviews)
    applications_count = len(apps)
    shortlisted_or_selected_count = sum(1 for a in apps if a.status in ("shortlisted", "interview", "selected", "placed"))

    return render_template(
        "student/interviews.html",
        student=student,
        upcoming_interviews=upcoming_interviews,
        completed_interviews=completed_interviews,
        applications=apps,
        upcoming_count=upcoming_count,
        applications_count=applications_count,
        shortlisted_or_selected_count=shortlisted_or_selected_count,
        active_page="applications"
    )


@student_bp.route("/interviews")
@student_required
def interviews_view():
    """Student dedicated interviews and application pipeline view."""
    user = get_current_user()
    student = user.student_profile
    if not student:
        return redirect(url_for("auth.login"))

    upcoming_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id, Interview.status == "scheduled")
        .order_by(Interview.scheduled_date.asc())
        .all()
    )
    completed_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id, Interview.status != "scheduled")
        .order_by(Interview.scheduled_date.desc())
        .all()
    )
    apps = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    upcoming_count = len(upcoming_interviews)
    applications_count = len(apps)
    shortlisted_or_selected_count = sum(1 for a in apps if a.status in ("shortlisted", "interview", "selected", "placed"))

    return render_template(
        "student/interviews.html",
        student=student,
        upcoming_interviews=upcoming_interviews,
        completed_interviews=completed_interviews,
        applications=apps,
        upcoming_count=upcoming_count,
        applications_count=applications_count,
        shortlisted_or_selected_count=shortlisted_or_selected_count,
        active_page="interviews"
    )


# --- REST API Endpoints ---

@student_bp.route("/api/profile", methods=["GET"])
@student_required
def api_get_profile():
    """Retrieve complete profile of logged-in student."""
    user = get_current_user()
    if not user or not user.student_profile:
        return jsonify({"error": "Student profile not found"}), 404
    return jsonify(user.student_profile.to_dict(detailed=True))


@student_bp.route("/api/profile", methods=["PUT"])
@student_required
def api_update_profile():
    """Update profile information for logged-in student."""
    user = get_current_user()
    student = user.student_profile
    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    data = request.get_json(silent=True) or {}
    student.name = data.get("name", student.name)
    student.target_role = data.get("target_role", student.target_role)
    student.bio = data.get("bio", student.bio)
    student.preferred_locations = data.get("preferred_locations", student.preferred_locations)
    student.preferred_industries = data.get("preferred_industries", student.preferred_industries)

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully", "profile": student.to_dict()})


# --- Explicit Student AI Navigation Page Handlers ---

@student_bp.route("/ai/career-twin", methods=["GET", "POST"])
@student_bp.route("/career-twin", methods=["GET", "POST"])
@student_required
def career_twin_page():
    """Redirect to student dashboard."""
    return redirect(url_for("student.dashboard"))


@student_bp.route("/ai/skill-gap", methods=["GET", "POST"])
@student_bp.route("/ai/skill_gap", methods=["GET", "POST"])
@student_bp.route("/skill-gaps", methods=["GET", "POST"])
@student_bp.route("/skill-gap", methods=["GET", "POST"])
@student_bp.route("/skill_gap", methods=["GET", "POST"])
@student_bp.route("/roadmap", methods=["GET", "POST"])
@student_bp.route("/ai/roadmap", methods=["GET", "POST"])
@student_required
def skill_gaps_page():
    """Explicit student navigation route for Skill Gaps & Roadmap."""
    from routes.ai.student_ai import skill_gaps_page as render_gaps
    return render_gaps()


@student_bp.route("/interview-prep", methods=["GET", "POST"])
@student_bp.route("/ai/interview-prep", methods=["GET", "POST"])
@student_bp.route("/ai/interview-simulator", methods=["GET", "POST"])
@student_bp.route("/interview-simulator", methods=["GET", "POST"])
@student_required
def interview_prep_page():
    """Explicit student navigation route for Interview Prep."""
    from routes.ai.student_ai import interview_prep_page as render_prep
    return render_prep()

# Alias for backwards compatibility
interview_simulator_page = interview_prep_page


@student_bp.route("/ai/resume-intelligence", methods=["GET", "POST"])
@student_bp.route("/resume-intelligence", methods=["GET", "POST"])
@student_required
def resume_intelligence_page():
    """Explicit student navigation route for Resume Intelligence."""
    from routes.ai.student_ai import resume_intelligence_page as render_resume
    return render_resume()


@student_bp.route("/ai/project-generator", methods=["GET", "POST"])
@student_bp.route("/project-generator", methods=["GET", "POST"])
@student_required
def project_generator_page():
    """Redirects to student dashboard."""
    return redirect(url_for("student.dashboard"))
