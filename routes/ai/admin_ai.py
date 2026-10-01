"""
Admin AI Routes for Campus-Link.
Provides Institutional Placement Intelligence briefings, cohort forecasts,
and dynamic institutional Skill Gap Report generation.
"""
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from utils.auth import admin_required
from models.department import Department
from services.ai.placement_ai_service import PlacementAIService
from services.analytics_service import AnalyticsService

admin_ai_bp = Blueprint("admin_ai", __name__, url_prefix="/admin/ai")


@admin_ai_bp.route("/insights", methods=["GET"])
@admin_required
def insights_page():
    """Redirects to the main Institutional Dashboard."""
    return redirect(url_for("admin.dashboard"))


@admin_ai_bp.route("/skill-gap-report", methods=["GET"])
@admin_required
def skill_report_page():
    """Redirects to the Campus Skill Gaps analytics view."""
    return redirect(url_for("admin.skills_view"))


@admin_ai_bp.route("/api/institutional-intelligence", methods=["GET"])
@admin_required
def api_get_institutional_intelligence():
    """Generates TPO & Dean institutional strategic placement briefing."""
    briefing = PlacementAIService.get_institutional_intelligence()
    return jsonify(briefing)


@admin_ai_bp.route("/api/generate-skill-report", methods=["POST"])
@admin_required
def api_generate_skill_report():
    """API endpoint generating dynamic institutional curriculum and skill deficit reports."""
    data = request.get_json(silent=True) or request.form
    dept_code = data.get("department_code", "ALL")
    report = PlacementAIService.generate_skill_gap_report(dept_code)
    return jsonify(report)
