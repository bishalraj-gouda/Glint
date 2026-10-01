from flask import Blueprint, jsonify
from extensions import db
from models.student import Student
from models.placement import Placement
from models.department import Department
from models.application import Application
from models.skill import Skill, StudentSkill
from models.job import JobSkill
from utils.auth import login_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/placement-rates", methods=["GET"])
@login_required
def get_placement_rates():
    """Calculate dynamic placement rates per academic department."""
    departments = Department.query.all()
    results = []

    for dept in departments:
        total_in_dept = Student.query.filter_by(department_id=dept.id).count()
        placed_in_dept = (
            Placement.query.join(Student)
            .filter(Student.department_id == dept.id)
            .count()
        )
        rate = round((placed_in_dept / total_in_dept * 100), 1) if total_in_dept > 0 else 0.0
        results.append({
            "code": dept.code,
            "name": dept.name,
            "total_students": total_in_dept,
            "placed_students": placed_in_dept,
            "placement_rate": rate
        })

    return jsonify({"success": True, "departments": results})


@analytics_bp.route("/recruitment-funnel", methods=["GET"])
@login_required
def get_recruitment_funnel():
    """Calculate funnel counts across all applications."""
    stages = ["applied", "eligible", "ai_matched", "shortlisted", "interview", "selected", "placed"]
    funnel = {}
    
    for stage in stages:
        funnel[stage] = Application.query.filter_by(status=stage).count()

    # Also aggregate cumulative progress
    return jsonify({
        "success": True,
        "funnel": funnel,
        "total_applications": Application.query.count()
    })


@analytics_bp.route("/campus-skill-intelligence", methods=["GET"])
@login_required
def get_campus_skill_intelligence():
    """Compare recruiter skill demand against campus availability."""
    skills = Skill.query.all()
    comparison = []

    for sk in skills:
        # Demand: count how many jobs require or prefer this skill
        demand_count = JobSkill.query.filter_by(skill_id=sk.id).count()
        # Availability: count how many students possess this skill
        availability_count = StudentSkill.query.filter_by(skill_id=sk.id).count()

        gap = demand_count - availability_count
        comparison.append({
            "skill_id": sk.id,
            "name": sk.name,
            "category": sk.category,
            "industry_demand": demand_count,
            "campus_availability": availability_count,
            "is_critical_gap": demand_count > 0 and availability_count < demand_count
        })

    comparison.sort(key=lambda x: (x["industry_demand"], -x["campus_availability"]), reverse=True)
    return jsonify({"success": True, "skills": comparison})
