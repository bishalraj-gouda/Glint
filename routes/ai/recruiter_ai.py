"""
Recruiter AI Routes for Campus-Link.
Provides automated candidate matching & ranking, screening dossiers,
scorecard evaluation summaries, and conversational Recruiter Copilot.
"""
from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from utils.auth import recruiter_required, get_current_user
from models.job import Job
from models.recruiter import Recruiter
from services.ai.recruiter_ai_service import RecruiterAIService

recruiter_ai_bp = Blueprint("recruiter_ai", __name__, url_prefix="/recruiter/ai")


@recruiter_ai_bp.route("/candidate-matcher", methods=["GET", "POST"])
@recruiter_ai_bp.route("/candidate-matching", methods=["GET", "POST"])
@recruiter_ai_bp.route("/matching", methods=["GET", "POST"])
@recruiter_required
def candidate_matching_page():
    """Renders the AI Candidate Matching & Scoring interactive interface."""
    user = get_current_user()
    recruiter = user.recruiter_profile if user else None
    if not recruiter:
        return redirect(url_for("auth.login"))

    company_jobs = Job.query.filter_by(company_id=recruiter.company_id).order_by(Job.created_at.desc()).all()
    selected_job_id = request.values.get("job_id", type=int)
    semantic_query = request.values.get("semantic_query", "").strip()
    min_cgpa = request.values.get("min_cgpa", default=0.0, type=float)
    department = request.values.get("department", default="ALL")

    # If semantic query supplied, execute vector semantic search
    semantic_data = None
    if semantic_query:
        semantic_data = RecruiterAIService.semantic_search_candidates(
            query_text=semantic_query,
            min_cgpa=min_cgpa,
            department=department
        )

    # Default to first job if none specified
    if not selected_job_id and company_jobs:
        selected_job_id = company_jobs[0].id

    ranked_data = {}
    if selected_job_id and not semantic_query:
        ranked_data = RecruiterAIService.rank_candidates_for_job(selected_job_id, min_cgpa, department)

    return render_template(
        "recruiter/candidate_matching.html",
        recruiter=recruiter,
        company=recruiter.company,
        jobs=company_jobs,
        selected_job_id=selected_job_id,
        ranked_data=ranked_data,
        semantic_data=semantic_data,
        semantic_query=semantic_query,
        active_page="candidate_matching"
    )


@recruiter_ai_bp.route("/api/semantic-match", methods=["POST"])
@recruiter_required
def api_semantic_match():
    """API endpoint for vector semantic candidate search."""
    data = request.get_json(silent=True) or request.form
    query_text = data.get("query", "").strip()
    min_cgpa = float(data.get("min_cgpa", 0.0) or 0.0)
    department = data.get("department", "ALL")

    results = RecruiterAIService.semantic_search_candidates(
        query_text=query_text,
        min_cgpa=min_cgpa,
        department=department
    )
    results["success"] = True
    return jsonify(results)


@recruiter_ai_bp.route("/api/rank-candidates/<int:job_id>", methods=["GET"])
@recruiter_required
def api_rank_candidates(job_id: int):
    """API returning live candidate match scores and rankings for a job requisition."""
    min_cgpa = request.args.get("min_cgpa", default=0.0, type=float)
    department = request.args.get("department", default="ALL")
    ranked = RecruiterAIService.rank_candidates_for_job(job_id, min_cgpa, department)
    if "error" in ranked:
        return jsonify(ranked), 404
    return jsonify(ranked)


@recruiter_ai_bp.route("/api/screen/<int:student_id>/job/<int:job_id>", methods=["GET"])
@recruiter_required
def api_screen_candidate(student_id: int, job_id: int):
    """Generates on-demand AI applicant screening dossier and targeted interview questions."""
    report = RecruiterAIService.screen_candidate(student_id, job_id)
    if "error" in report:
        return jsonify(report), 404
    return jsonify(report)


@recruiter_ai_bp.route("/api/evaluation-summary", methods=["POST"])
@recruiter_required
def api_evaluation_summary():
    """Generates an AI evaluation summary for candidate interview scorecards."""
    data = request.get_json(silent=True) or request.form
    interview_id = data.get("interview_id", type=int)
    score = data.get("score")
    draft_notes = data.get("draft_notes", "")

    if not interview_id:
        return jsonify({"error": "interview_id is required"}), 400

    score_val = float(score) if score not in (None, "") else None
    result = RecruiterAIService.generate_evaluation_summary(interview_id, score_val, str(draft_notes))
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@recruiter_ai_bp.route("/api/chat", methods=["POST"])
@recruiter_required
def api_recruiter_chat():
    """Interactive conversational chat endpoint for the AI Recruiter Copilot."""
    user = get_current_user()
    recruiter = user.recruiter_profile if user else None
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 403

    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "").strip()
    history = payload.get("history", [])

    if not message:
        return jsonify({"error": "Message is required"}), 400

    response_data = RecruiterAIService.recruiter_chat(recruiter.id, message, history)
    return jsonify(response_data)
