import os
import io
import csv
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, Response, current_app
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from models.company import Company
from models.job import Job
from models.application import Application
from models.interview import Interview
from models.placement import Placement
from models.department import Department
from models.skill import Skill
from services.analytics_service import AnalyticsService
from utils.auth import admin_required, get_current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ==============================================================================
# 1. CORE DASHBOARD & ANALYTICS VIEWS
# ==============================================================================

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """College placement command center with dynamic metrics calculated from database."""
    total_students = Student.query.count()
    eligible_students = Student.query.filter(Student.cgpa >= 6.5).count()
    active_recruiters = Recruiter.query.count()
    active_companies = Company.query.count()
    active_jobs = Job.query.filter_by(status="active").count()
    total_applications = Application.query.count()
    total_interviews = Interview.query.count()
    total_placed = Placement.query.count()

    placement_rate = round((total_placed / total_students * 100), 1) if total_students > 0 else 0.0

    kpis = {
        "total_students": total_students,
        "eligible_students": eligible_students,
        "active_recruiters": active_recruiters,
        "active_companies": active_companies,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "total_interviews": total_interviews,
        "total_placed": total_placed,
        "placement_rate": placement_rate
    }

    recent_placements = Placement.query.order_by(Placement.placed_date.desc()).limit(5).all()
    departments = Department.query.all()

    return render_template(
        "admin/dashboard.html",
        kpis=kpis,
        recent_placements=recent_placements,
        departments=departments,
        active_page="dashboard"
    )


@admin_bp.route("/analytics")
@admin_required
def analytics_view():
    """Campus placement analytics and compensation intelligence view."""
    analytics_data = AnalyticsService.get_placement_analytics()
    return render_template(
        "admin/analytics.html",
        analytics=analytics_data,
        active_page="analytics"
    )


@admin_bp.route("/skills")
@admin_required
def skills_view():
    """Campus skill intelligence and market demand-supply gap view."""
    skill_gap_data = AnalyticsService.get_campus_skill_gaps()
    return render_template(
        "admin/skills.html",
        skill_data=skill_gap_data,
        active_page="skills"
    )


# ==============================================================================
# 2. INSTITUTIONAL DATABASE EXPLORER & MANAGEMENT MODULE
# ==============================================================================

TABLE_METADATA = {
    "students": {
        "title": "Students",
        "singular": "Student",
        "icon": "users",
        "description": "Enrolled student placement profiles, academic records, and CGPA metrics",
        "columns": ["ID", "Roll Number", "Name", "Department", "CGPA", "Grad Year", "Status", "Actions"]
    },
    "recruiters": {
        "title": "Recruiters",
        "singular": "Recruiter",
        "icon": "briefcase",
        "description": "Corporate campus recruiter accounts and liaison contacts",
        "columns": ["ID", "Recruiter Name", "Company", "Designation", "Phone", "Email", "Password", "Actions"]
    },
    "companies": {
        "title": "Companies",
        "singular": "Company",
        "icon": "building",
        "description": "Partner corporate hiring organizations and campus drive hosts",
        "columns": ["ID", "Company Name", "Industry", "Location", "Website", "Active Jobs", "Actions"]
    },
    "jobs": {
        "title": "Job Postings",
        "singular": "Job Posting",
        "icon": "file-text",
        "description": "Campus hiring requisitions, eligibility criteria, and compensation packages",
        "columns": ["ID", "Job Title", "Company", "CTC (LPA)", "Min CGPA", "Applications", "Status", "Actions"]
    },
    "applications": {
        "title": "Applications",
        "singular": "Application",
        "icon": "send",
        "description": "Student job submissions and placement pipeline tracking",
        "columns": ["ID", "Student", "Target Job", "Company", "Status", "Applied Date", "Actions"]
    },
    "placements": {
        "title": "Placements",
        "singular": "Placement",
        "icon": "award",
        "description": "Official campus placement offers, CTC packages, and accepted roles",
        "columns": ["ID", "Placed Student", "Hiring Company", "Role", "Package (LPA)", "Placed Date", "Actions"]
    },
    "departments": {
        "title": "Departments",
        "singular": "Department",
        "icon": "layers",
        "description": "Academic engineering departments and student distribution",
        "columns": ["ID", "Department Name", "Branch Code", "Enrolled Students", "Actions"]
    },
    "skills": {
        "title": "Skills Taxonomy",
        "singular": "Skill",
        "icon": "cpu",
        "description": "Institutional normalized skills repository and taxonomy categorization",
        "columns": ["ID", "Skill Name", "Category", "Verified Students", "Actions"]
    },
    "users": {
        "title": "System Users",
        "singular": "User Account",
        "icon": "shield",
        "description": "Authentication credentials, assigned roles, and account security",
        "columns": ["ID", "Email Address", "System Role", "Active Status", "Registered Date", "Actions"]
    }
}


def _get_table_counts():
    """Computes exact row counts for all managed database tables."""
    return {
        "students": Student.query.count(),
        "recruiters": Recruiter.query.count(),
        "companies": Company.query.count(),
        "jobs": Job.query.count(),
        "applications": Application.query.count(),
        "placements": Placement.query.count(),
        "departments": Department.query.count(),
        "skills": Skill.query.count(),
        "users": User.query.count()
    }


def _get_db_file_info():
    """Returns database engine type and storage usage."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    size_str = "InMemory"
    engine_name = "SQLite 3"

    if "sqlite:///" in db_uri:
        db_path = db_uri.replace("sqlite:///", "")
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = "Active File"
    elif "postgresql" in db_uri:
        engine_name = "PostgreSQL"
        size_str = "Cloud Cluster"
    elif "mysql" in db_uri:
        engine_name = "MySQL"
        size_str = "Cloud DB"

    return engine_name, size_str


@admin_bp.route("/database")
@admin_required
def database_view():
    """Institutional Database Explorer & Record Manager view."""
    active_table = request.args.get("table", "students").lower()
    if active_table not in TABLE_METADATA:
        active_table = "students"

    search_query = request.args.get("q", "").strip()
    table_counts = _get_table_counts()
    total_records = sum(table_counts.values())
    engine_name, db_size = _get_db_file_info()

    # Query active table with optional search
    rows_data = []

    if active_table == "students":
        q = Student.query
        if search_query:
            q = q.filter(Student.name.ilike(f"%{search_query}%") | Student.roll_number.ilike(f"%{search_query}%"))
        items = q.order_by(Student.id.desc()).all()
        for s in items:
            dept_code = s.department.code if s.department else "—"
            cgpa_val = f"{s.cgpa:.2f}" if s.cgpa is not None else "—"
            status_text = "Placed" if s.placements else ("Eligible" if (s.cgpa or 0) >= 6.5 else "In Progress")
            status_badge = "shortlisted" if s.placements else ("eligible" if (s.cgpa or 0) >= 6.5 else "pending")
            rows_data.append({
                "id": s.id,
                "cells": [s.id, s.roll_number, s.name, dept_code, cgpa_val, s.graduation_year or "—"],
                "badge": {"text": status_text, "class": status_badge},
                "raw": {
                    "id": s.id, "roll_number": s.roll_number, "name": s.name, "user_id": s.user_id,
                    "department": dept_code, "cgpa": s.cgpa, "graduation_year": s.graduation_year,
                    "created_at": s.created_at.isoformat() if hasattr(s, "created_at") and s.created_at else None
                }
            })

    elif active_table == "recruiters":
        q = Recruiter.query
        if search_query:
            q = q.filter(Recruiter.name.ilike(f"%{search_query}%"))
        items = q.order_by(Recruiter.id.desc()).all()
        for r in items:
            comp_name = r.company.name if r.company else "—"
            email_val = r.user.email if r.user else "—"
            pwd_val = (r.user.raw_password if (r.user and r.user.raw_password) else "Recruiter@123") if r.user else "—"
            pwd_cell = f'<div style="display:inline-flex;align-items:center;gap:6px;"><code style="background:#FAF7F2;border:1px solid #EAE3D7;padding:3px 8px;border-radius:6px;font-family:monospace;font-size:0.84rem;color:#1F1C18;font-weight:700;">{pwd_val}</code><button type="button" class="btn-action-icon" style="padding:3px 6px;" onclick="navigator.clipboard.writeText(\'{pwd_val}\');if(window.showGlobalToast)window.showGlobalToast(\'Copied recruiter password: {pwd_val}\');" title="Copy Password"><i data-lucide="copy" style="width:12px;height:12px;"></i></button></div>'
            rows_data.append({
                "id": r.id,
                "cells": [r.id, r.name, comp_name, r.designation or "—", r.phone or "—", email_val, pwd_cell],
                "raw": {
                    "id": r.id, "name": r.name, "company": comp_name, "designation": r.designation,
                    "phone": r.phone, "email": email_val, "password": pwd_val, "user_id": r.user_id
                }
            })

    elif active_table == "companies":
        q = Company.query
        if search_query:
            q = q.filter(Company.name.ilike(f"%{search_query}%") | Company.industry.ilike(f"%{search_query}%"))
        items = q.order_by(Company.id.desc()).all()
        for c in items:
            jobs_count = len(c.jobs) if c.jobs else 0
            rows_data.append({
                "id": c.id,
                "cells": [c.id, c.name, c.industry or "—", c.location or "—", c.website or "—", f"{jobs_count} Jobs"],
                "raw": {
                    "id": c.id, "name": c.name, "industry": c.industry, "location": c.location,
                    "website": c.website, "description": c.description, "active_jobs": jobs_count
                }
            })

    elif active_table == "jobs":
        q = Job.query
        if search_query:
            q = q.filter(Job.title.ilike(f"%{search_query}%"))
        items = q.order_by(Job.id.desc()).all()
        for j in items:
            comp_name = j.company.name if j.company else "—"
            if j.salary_min and j.salary_max:
                pkg = f"{j.salary_min:.1f} - {j.salary_max:.1f} LPA"
            elif j.salary_max or j.salary_min:
                pkg = f"{j.salary_max or j.salary_min:.1f} LPA"
            else:
                pkg = "Competitive"
            min_cg = f"{j.min_cgpa:.1f}" if j.min_cgpa else "None"
            apps_count = len(j.applications) if j.applications else 0
            is_active = (j.status == "active")
            rows_data.append({
                "id": j.id,
                "cells": [j.id, j.title, comp_name, pkg, min_cg, f"{apps_count} Submissions"],
                "badge": {"text": j.status.upper(), "class": "eligible" if is_active else "rejected"},
                "can_toggle": True,
                "status_action": "close" if is_active else "activate",
                "raw": {
                    "id": j.id, "title": j.title, "company": comp_name, "salary": pkg,
                    "salary_min": j.salary_min, "salary_max": j.salary_max,
                    "min_cgpa": j.min_cgpa, "status": j.status, "applications_count": apps_count
                }
            })

    elif active_table == "applications":
        q = Application.query
        if search_query:
            q = q.filter(Application.status.ilike(f"%{search_query}%"))
        items = q.order_by(Application.id.desc()).all()
        for a in items:
            st_name = a.student.name if a.student else "—"
            j_title = a.job.title if a.job else "—"
            c_name = a.job.company.name if a.job and a.job.company else "—"
            app_date = a.applied_at.strftime("%Y-%m-%d") if getattr(a, "applied_at", None) else "—"
            badge_map = {
                "placed": "shortlisted", "selected": "shortlisted",
                "shortlisted": "eligible", "interviewing": "eligible",
                "applied": "pending", "pending": "pending", "rejected": "rejected"
            }
            rows_data.append({
                "id": a.id,
                "cells": [a.id, st_name, j_title, c_name],
                "badge": {"text": a.status.upper(), "class": badge_map.get(a.status.lower(), "pending")},
                "cells_after": [app_date],
                "raw": {
                    "id": a.id, "student_name": st_name, "job_title": j_title, "company": c_name,
                    "status": a.status, "applied_at": app_date, "match_score": a.match_score
                }
            })

    elif active_table == "placements":
        q = Placement.query
        items = q.order_by(Placement.placed_date.desc()).all()
        for p in items:
            st_name = p.student.name if p.student else "—"
            c_name = p.company.name if p.company else "—"
            j_title = p.job.title if p.job else "—"
            pkg = f"{p.package_lpa:.1f} LPA" if p.package_lpa else "—"
            p_date = p.placed_date.strftime("%Y-%m-%d") if p.placed_date else "—"
            rows_data.append({
                "id": p.id,
                "cells": [p.id, st_name, c_name, j_title, pkg, p_date],
                "badge": {"text": "VERIFIED", "class": "shortlisted"},
                "raw": {
                    "id": p.id, "student_name": st_name, "company": c_name, "role": j_title,
                    "package_lpa": p.package_lpa, "placed_date": p_date
                }
            })

    elif active_table == "departments":
        q = Department.query
        if search_query:
            q = q.filter(Department.name.ilike(f"%{search_query}%") | Department.code.ilike(f"%{search_query}%"))
        items = q.order_by(Department.id.asc()).all()
        for d in items:
            st_count = d.students.count() if d.students else 0
            rows_data.append({
                "id": d.id,
                "cells": [d.id, d.name, d.code, f"{st_count} Students"],
                "raw": {
                    "id": d.id, "name": d.name, "code": d.code, "student_count": st_count
                }
            })

    elif active_table == "skills":
        q = Skill.query
        if search_query:
            q = q.filter(Skill.name.ilike(f"%{search_query}%") | Skill.category.ilike(f"%{search_query}%"))
        items = q.order_by(Skill.name.asc()).all()
        for sk in items:
            st_skills_count = len(sk.student_skills) if sk.student_skills else 0
            rows_data.append({
                "id": sk.id,
                "cells": [sk.id, sk.name, sk.category.title(), f"{st_skills_count} Profiles"],
                "raw": {
                    "id": sk.id, "name": sk.name, "category": sk.category, "verified_students": st_skills_count
                }
            })

    elif active_table == "users":
        q = User.query
        if search_query:
            q = q.filter(User.email.ilike(f"%{search_query}%") | User.role.ilike(f"%{search_query}%"))
        items = q.order_by(User.id.desc()).all()
        for u in items:
            is_act = getattr(u, "is_active", True)
            u_date = u.created_at.strftime("%Y-%m-%d") if hasattr(u, "created_at") and u.created_at else "—"
            rows_data.append({
                "id": u.id,
                "cells": [u.id, u.email, u.role.upper()],
                "badge": {"text": "ACTIVE" if is_act else "SUSPENDED", "class": "eligible" if is_act else "rejected"},
                "cells_after": [u_date],
                "can_toggle": True,
                "status_action": "deactivate" if is_act else "activate",
                "raw": {
                    "id": u.id, "email": u.email, "role": u.role, "is_active": is_act, "registered_date": u_date
                }
            })

    current_meta = TABLE_METADATA.get(active_table, TABLE_METADATA["students"])

    return render_template(
        "admin/database.html",
        active_page="database",
        active_table=active_table,
        table_meta=current_meta,
        all_tables=TABLE_METADATA,
        table_counts=table_counts,
        total_records=total_records,
        engine_name=engine_name,
        db_size=db_size,
        search_query=search_query,
        rows=rows_data
    )


@admin_bp.route("/database/export/<table_name>")
@admin_required
def export_table_csv(table_name):
    """Generates and downloads a clean CSV spreadsheet for any database table."""
    table_key = table_name.lower()
    if table_key not in TABLE_METADATA:
        return jsonify({"error": "Invalid table specified"}), 400

    output = io.StringIO()
    writer = csv.writer(output)

    if table_key == "students":
        writer.writerow(["ID", "Roll Number", "Name", "Department", "CGPA", "Graduation Year"])
        for s in Student.query.all():
            writer.writerow([s.id, s.roll_number, s.name, s.department.code if s.department else "", s.cgpa or "", s.graduation_year or ""])
    elif table_key == "recruiters":
        writer.writerow(["ID", "Name", "Company", "Designation", "Phone", "Email", "Password"])
        for r in Recruiter.query.all():
            pwd_val = (r.user.raw_password if (r.user and r.user.raw_password) else "Recruiter@123") if r.user else ""
            writer.writerow([r.id, r.name, r.company.name if r.company else "", r.designation or "", r.phone or "", r.user.email if r.user else "", pwd_val])
    elif table_key == "companies":
        writer.writerow(["ID", "Name", "Industry", "Location", "Website", "Active Jobs"])
        for c in Company.query.all():
            writer.writerow([c.id, c.name, c.industry or "", c.location or "", c.website or "", len(c.jobs) if c.jobs else 0])
    elif table_key == "jobs":
        writer.writerow(["ID", "Title", "Company", "Salary Min (LPA)", "Salary Max (LPA)", "Min CGPA", "Status"])
        for j in Job.query.all():
            writer.writerow([j.id, j.title, j.company.name if j.company else "", j.salary_min or "", j.salary_max or "", j.min_cgpa or "", j.status])
    elif table_key == "applications":
        writer.writerow(["ID", "Student", "Job Title", "Company", "Status", "Applied At"])
        for a in Application.query.all():
            writer.writerow([a.id, a.student.name if a.student else "", a.job.title if a.job else "", a.job.company.name if a.job and a.job.company else "", a.status, getattr(a, "applied_at", "")])
    elif table_key == "placements":
        writer.writerow(["ID", "Student", "Company", "Role", "Package (LPA)", "Placed Date"])
        for p in Placement.query.all():
            writer.writerow([p.id, p.student.name if p.student else "", p.company.name if p.company else "", p.job.title if p.job else "", p.package_lpa or "", p.placed_date])
    elif table_key == "departments":
        writer.writerow(["ID", "Name", "Code", "Enrolled Students"])
        for d in Department.query.all():
            writer.writerow([d.id, d.name, d.code, d.students.count() if d.students else 0])
    elif table_key == "skills":
        writer.writerow(["ID", "Skill Name", "Category", "Verified Profiles"])
        for sk in Skill.query.all():
            writer.writerow([sk.id, sk.name, sk.category, len(sk.student_skills) if sk.student_skills else 0])
    elif table_key == "users":
        writer.writerow(["ID", "Email", "Role", "Active Status", "Created At"])
        for u in User.query.all():
            writer.writerow([u.id, u.email, u.role, "Active" if getattr(u, "is_active", True) else "Suspended", getattr(u, "created_at", "")])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=glint_{table_key}_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@admin_bp.route("/api/database/<table_name>/<int:record_id>/delete", methods=["POST"])
@admin_required
def api_delete_record(table_name, record_id):
    """Deletes an entity record safely with relational constraint protection."""
    table_key = table_name.lower()
    current_uid = session.get("user_id")

    # Safety: Cannot delete current admin user
    if table_key == "users" and record_id == current_uid:
        return jsonify({"error": "Cannot delete your own active administrator account."}), 400

    model_map = {
        "students": Student, "recruiters": Recruiter, "companies": Company,
        "jobs": Job, "applications": Application, "placements": Placement,
        "departments": Department, "skills": Skill, "users": User
    }

    model = model_map.get(table_key)
    if not model:
        return jsonify({"error": "Unrecognized table"}), 400

    record = db.session.get(model, record_id)
    if not record:
        return jsonify({"error": f"Record #{record_id} not found."}), 404

    try:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"success": True, "message": f"{table_key.capitalize()} record #{record_id} deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Cannot delete #{record_id}: Foreign key or active relation exists ({str(e)})."}), 400


@admin_bp.route("/api/database/<table_name>/<int:record_id>/toggle-status", methods=["POST"])
@admin_required
def api_toggle_status(table_name, record_id):
    """Toggles active/closed or suspended status for actionable records."""
    table_key = table_name.lower()
    current_uid = session.get("user_id")

    if table_key == "jobs":
        job = db.session.get(Job, record_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        job.status = "closed" if job.status == "active" else "active"
        db.session.commit()
        return jsonify({"success": True, "new_status": job.status})

    elif table_key == "users":
        if record_id == current_uid:
            return jsonify({"error": "Cannot suspend your own account."}), 400
        user = db.session.get(User, record_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.is_active = not getattr(user, "is_active", True)
        db.session.commit()
        return jsonify({"success": True, "new_status": "ACTIVE" if user.is_active else "SUSPENDED"})

    return jsonify({"error": "Status toggle not supported for this entity"}), 400


# ==============================================================================
# 3. EXISTING ANALYTICS API ENDPOINTS
# ==============================================================================

@admin_bp.route("/api/overview-kpis", methods=["GET"])
@admin_required
def api_overview_kpis():
    """API for dynamic administrative dashboard metrics."""
    return jsonify(AnalyticsService.get_summary_kpis())


@admin_bp.route("/api/placement-analytics", methods=["GET"])
@admin_required
def api_placement_analytics():
    """API returning detailed placement funnel and compensation metrics."""
    data = AnalyticsService.get_placement_analytics()
    serialized = dict(data)
    serialized["recent_placements"] = [
        {
            "id": p.id,
            "student_name": p.student.name if p.student else None,
            "student_roll": p.student.roll_number if p.student else None,
            "department": p.student.department.code if p.student and p.student.department else None,
            "company_name": p.company.name if p.company else None,
            "job_title": p.job.title if p.job else None,
            "package_lpa": p.package_lpa,
            "placed_date": p.placed_date.isoformat() if p.placed_date else None
        }
        for p in data["recent_placements"]
    ]
    return jsonify(serialized)


@admin_bp.route("/api/campus-skill-gaps", methods=["GET"])
@admin_required
def api_campus_skill_gaps():
    """API returning institutional skill gaps and demand-supply matrix."""
    return jsonify(AnalyticsService.get_campus_skill_gaps())
