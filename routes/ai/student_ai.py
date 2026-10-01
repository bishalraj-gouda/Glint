"""
Student AI Routes for Campus-Link.
Handles AI Career Twin, Skill Gaps, Roadmap, Interview Simulator,
Resume Intelligence, Project Generator, and contextual Career Copilot chat.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from utils.auth import student_required, get_current_user
from models.student import Student
from models.job import Job
from services.ai.career_twin_service import CareerTwinService
from services.ai.skill_gap_service import SkillGapService
from services.ai.career_roadmap_service import CareerRoadmapService
from services.ai.job_match_service import JobMatchService
from services.ai.interview_ai_service import InterviewAIService
from services.ai.resume_ai_service import ResumeAIService
from services.ai.project_ai_service import ProjectAIService
from services.ai.career_chat_service import CareerChatService

student_ai_bp = Blueprint("student_ai", __name__, url_prefix="/student/ai")


def _get_active_student():
    """Helper to retrieve the authenticated student model."""
    user = get_current_user()
    if not user or not user.student_profile:
        return None
    return user.student_profile


# ==============================================================================
# VIEW ROUTES (Full Page Experiences)
# ==============================================================================

@student_ai_bp.route("/twin", methods=["GET", "POST"])
@student_ai_bp.route("/career-twin", methods=["GET", "POST"])
@student_required
def career_twin_page():
    """Redirect to student dashboard."""
    return redirect(url_for("student.dashboard"))


@student_ai_bp.route("/skills", methods=["GET", "POST"])
@student_ai_bp.route("/skill_gap", methods=["GET", "POST"])
@student_ai_bp.route("/skill-gap", methods=["GET", "POST"])
@student_ai_bp.route("/skill-gaps", methods=["GET", "POST"])
@student_required
def skill_gaps_page():
    """Renders the Intelligent Skill Gap Engine & Roadmap Timeline."""
    student = _get_active_student()
    if not student:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("auth.login"))

    payload = request.get_json(silent=True) or {}
    target_role = (
        payload.get("target_role")
        or payload.get("role")
        or request.form.get("target_role")
        or request.form.get("role")
        or request.args.get("target_role")
        or request.args.get("role")
    )
    job_id = (
        payload.get("job_id")
        or request.form.get("job_id", type=int)
        or request.args.get("job_id", type=int)
    )

    # If client requested JSON via AJAX or Accept header
    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.args.get("format") == "json"
    )
    if wants_json:
        return api_analyze_skill_gap()

    gap_data = SkillGapService.analyze_skill_gaps(student.id, target_role=target_role, job_id=job_id)
    roadmap_data = CareerRoadmapService.get_or_generate_roadmap(student.id, target_role=target_role)

    is_roadmap = "roadmap" in request.path or request.args.get("view") == "roadmap"
    return render_template(
        "student/skill_gaps.html",
        student=student,
        gaps=gap_data,
        roadmap=roadmap_data,
        active_page="roadmap" if is_roadmap else "skill_gaps",
        is_roadmap=is_roadmap
    )


@student_ai_bp.route("/roadmap", methods=["GET", "POST"])
@student_required
def roadmap_page():
    """Renders the Placement Acceleration Roadmap."""
    return skill_gaps_page()


@student_ai_bp.route("/interview", methods=["GET", "POST"])
@student_ai_bp.route("/interview-simulator", methods=["GET", "POST"])
@student_required
def interview_simulator_page():
    """Redirects to student dashboard."""
    return redirect(url_for("student.dashboard"))


@student_ai_bp.route("/resume", methods=["GET", "POST"])
@student_ai_bp.route("/resume-intelligence", methods=["GET", "POST"])
@student_required
def resume_intelligence_page():
    """Renders the Resume Intelligence & ATS Matcher."""
    student = _get_active_student()
    if not student:
        return redirect(url_for("auth.login"))

    latest_analysis = None
    if request.method == "POST":
        resume_text = ""
        file_name = "Uploaded_Resume"
        job_id = request.form.get("job_id", type=int)

        if "resume_file" in request.files and request.files["resume_file"].filename:
            file = request.files["resume_file"]
            file_name = file.filename
            if file.filename.lower().endswith(".pdf"):
                resume_text = ResumeAIService.extract_text_from_pdf_bytes(file.read())
            else:
                resume_text = file.read().decode("utf-8", errors="ignore")
        else:
            resume_text = request.form.get("resume_text", "")

        if resume_text and len(resume_text.strip()) >= 50:
            latest_analysis = ResumeAIService.audit_resume(student.id, resume_text, job_id=job_id, file_name=file_name)
            flash("Resume audited successfully with ATS compliance scores.", "success")
        elif request.form.get("resume_text") or "resume_file" in request.files:
            flash("Please provide at least 50 characters of resume text or a valid PDF.", "warning")

    if not latest_analysis:
        latest_analysis = ResumeAIService.get_latest_analysis(student.id)

    target_jobs = Job.query.filter_by(status="active").limit(10).all()

    return render_template(
        "student/resume_intelligence.html",
        student=student,
        latest_analysis=latest_analysis,
        target_jobs=target_jobs,
        active_page="resume_intelligence"
    )


@student_ai_bp.route("/projects", methods=["GET", "POST"])
@student_ai_bp.route("/project-generator", methods=["GET", "POST"])
@student_required
def project_generator_page():
    """Redirects to student dashboard."""
    return redirect(url_for("student.dashboard"))


# ==============================================================================
# API ENDPOINTS (Asynchronous JSON Services)
# ==============================================================================

@student_ai_bp.route("/api/twin", methods=["GET"])
@student_required
def api_get_twin():
    """Returns serialized Career Twin data."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(CareerTwinService.get_or_create_twin(student.id))


@student_ai_bp.route("/api/twin/refresh", methods=["POST"])
@student_required
def api_refresh_twin():
    """Recalculates deterministic scores and requests fresh AI synthesis."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(CareerTwinService.get_or_create_twin(student.id, refresh=True))


@student_ai_bp.route("/api/skill-gap/analyze", methods=["GET", "POST"])
@student_ai_bp.route("/api/skill_gap/analyze", methods=["GET", "POST"])
@student_ai_bp.route("/api/gaps/analyze", methods=["GET", "POST"])
@student_required
def api_analyze_skill_gap():
    """
    Computes exact set operations for student skills against the selected role benchmark,
    regenerates the adaptive curriculum/roadmap, and returns full dynamic state payload.
    """
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    target_role = (
        payload.get("target_role")
        or payload.get("role")
        or request.form.get("target_role")
        or request.form.get("role")
        or request.args.get("target_role")
        or request.args.get("role")
        or getattr(student, "target_role", None)
        or "Full Stack Developer"
    )
    job_id = (
        payload.get("job_id")
        or request.form.get("job_id", type=int)
        or request.args.get("job_id", type=int)
    )

    # 1. Compute set comparisons (Student Skills ∩ Benchmark, Benchmark \ Student Skills, ratio, etc.)
    gap_data = SkillGapService.analyze_skill_gaps(student.id, target_role=target_role, job_id=job_id)

    # 2. Regenerate/Retrieve Learning Roadmap matching this role
    roadmap_data = CareerRoadmapService.get_or_generate_roadmap(student.id, target_role=target_role, regenerate=True)

    # 3. Format complete response matching all requested keys
    matched = gap_data.get("matched_skills", [])
    missing = gap_data.get("missing_skills", [])
    total_req = gap_data.get("total_required", len(matched) + len(missing))
    match_pct = gap_data.get("match_percentage", round((len(matched) / total_req * 100), 1) if total_req else 0)
    probing_q = gap_data.get("practice_interview_questions", [])
    benchmark_role = gap_data.get("benchmark_role", target_role)

    return jsonify({
        "success": True,
        "target_role": benchmark_role,
        "benchmark_role": benchmark_role,
        "target_benchmark_title": f"Target Benchmark: {benchmark_role}",
        "benchmark_match_ratio": match_pct,
        "match_percentage": match_pct,
        "verified_matched_skills": matched,
        "matched_skills": matched,
        "critical_missing_competencies": missing,
        "missing_skills": missing,
        "probing_questions": probing_q,
        "practice_interview_questions": probing_q,
        "total_required": total_req,
        "matched_count": len(matched),
        "missing_count": len(missing),
        "gap_severity": gap_data.get("gap_severity", "Moderate"),
        "market_urgency_summary": gap_data.get("market_urgency_summary", ""),
        "quick_win_milestone": gap_data.get("quick_win_milestone", ""),
        "priority_focus": gap_data.get("priority_focus", []),
        "curriculum": roadmap_data,
        "roadmap": roadmap_data
    })


@student_ai_bp.route("/api/gaps", methods=["GET"])
@student_required
def api_get_gaps():
    """Analyzes skill gaps against specified or default role."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    role = request.args.get("role")
    job_id = request.args.get("job_id", type=int)
    return jsonify(SkillGapService.analyze_skill_gaps(student.id, target_role=role, job_id=job_id))


@student_ai_bp.route("/api/roadmap", methods=["GET"])
@student_required
def api_get_roadmap():
    """Returns active learning roadmap."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    role = request.args.get("role")
    return jsonify(CareerRoadmapService.get_or_generate_roadmap(student.id, target_role=role))


@student_ai_bp.route("/api/roadmap/regenerate", methods=["POST"])
@student_required
def api_regenerate_roadmap():
    """Regenerates roadmap for a new target role."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    role = data.get("role")
    return jsonify(CareerRoadmapService.get_or_generate_roadmap(student.id, target_role=role, regenerate=True))


@student_ai_bp.route("/api/roadmap/task/toggle", methods=["POST"])
@student_required
def api_toggle_roadmap_task():
    """Toggles completion status of a roadmap task."""
    data = request.get_json() or {}
    roadmap_id = data.get("roadmap_id")
    task_id = data.get("task_id")
    if not roadmap_id or not task_id:
        return jsonify({"error": "Missing roadmap_id or task_id"}), 400
    return jsonify(CareerRoadmapService.toggle_task(roadmap_id, task_id))


@student_ai_bp.route("/api/roadmap/task/proof", methods=["POST"])
@student_ai_bp.route("/api/roadmap/task/update", methods=["POST"])
@student_required
def api_submit_task_proof():
    """Submits proof-of-work link and updates status for a roadmap task."""
    data = request.get_json() or {}
    roadmap_id = data.get("roadmap_id")
    task_id = data.get("task_id")
    proof_url = data.get("proof_url")
    proof_notes = data.get("proof_notes")
    completed = data.get("completed")

    if not roadmap_id or not task_id:
        return jsonify({"error": "Missing roadmap_id or task_id"}), 400

    result = CareerRoadmapService.update_task_status(
        roadmap_id=roadmap_id,
        task_id=task_id,
        completed=completed,
        proof_url=proof_url,
        proof_notes=proof_notes
    )
    return jsonify(result)



@student_ai_bp.route("/api/interview/start", methods=["POST"])
@student_required
def api_start_interview():
    """Starts a new mock interview session."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    role_title = data.get("role_title", "Software Development Engineer")
    interview_type = data.get("interview_type", "technical")
    job_id = data.get("job_id")
    return jsonify(InterviewAIService.start_session(student.id, role_title=role_title, interview_type=interview_type, job_id=job_id))


@student_ai_bp.route("/api/interview/submit", methods=["POST"])
@student_required
def api_submit_interview_answer():
    """Submits answer to current question and returns 3-axis evaluation."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    answer = data.get("answer")
    if not session_id or not answer:
        return jsonify({"error": "session_id and answer are required"}), 400
    return jsonify(InterviewAIService.submit_answer(session_id, answer))


@student_ai_bp.route("/api/resume/audit", methods=["POST"])
@student_required
def api_audit_resume():
    """Audits resume text or uploaded PDF file."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401

    resume_text = ""
    file_name = "Uploaded_Resume"
    job_id = None

    if "resume_file" in request.files:
        file = request.files["resume_file"]
        file_name = file.filename
        job_id = request.form.get("job_id", type=int)
        if file.filename.lower().endswith(".pdf"):
            resume_text = ResumeAIService.extract_text_from_pdf_bytes(file.read())
        else:
            resume_text = file.read().decode("utf-8", errors="ignore")
    elif request.is_json:
        data = request.get_json() or {}
        resume_text = data.get("resume_text", "")
        job_id = data.get("job_id")
    else:
        resume_text = request.form.get("resume_text", "")
        job_id = request.form.get("job_id", type=int)

    if not resume_text or len(resume_text.strip()) < 50:
        return jsonify({"error": "Please provide sufficient resume text (at least 50 characters) or upload a readable PDF."}), 400

    result = ResumeAIService.audit_resume(student.id, resume_text, job_id=job_id, file_name=file_name)
    return jsonify(result)


@student_ai_bp.route("/api/project/generate", methods=["POST"])
@student_required
def api_generate_project():
    """Generates project blueprint based on student skill gaps."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    target_role = data.get("target_role")
    domain = data.get("domain")
    return jsonify(ProjectAIService.generate_project_idea(student.id, target_role=target_role, preferred_domain=domain))


@student_ai_bp.route("/api/chat", methods=["POST"])
@student_required
def api_career_chat():
    """Converses with the context-aware Career Copilot."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    message = data.get("message", "")
    history = data.get("history", [])
    if not message.strip():
        return jsonify({"error": "Message cannot be empty"}), 400
    return jsonify(CareerChatService.chat(student.id, message, conversation_history=history))


@student_ai_bp.route("/api/job-match/<int:job_id>", methods=["GET"])
@student_required
def api_get_job_match(job_id):
    """Calculates multi-factor job match score and Gemini explainability."""
    student = _get_active_student()
    if not student:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(JobMatchService.evaluate_job_match(student.id, job_id))
