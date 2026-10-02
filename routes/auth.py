from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_user, logout_user, current_user
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from models.company import Company
from models.department import Department
from utils.auth import get_current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login view. Automatically cleans up and destroys any previous session when loading the login screen."""
    # When user visits the login screen, delete any previous session so old modules cannot be accessed
    if request.method == "GET":
        logout_user()
        flashes = session.get("_flashes")
        session.clear()
        if flashes:
            session["_flashes"] = flashes
        return render_template("login.html")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template("login.html", email=email)

        if not user.is_active:
            flash("This account has been deactivated. Please contact administrator.", "danger")
            return render_template("login.html", email=email)

        # Ensure previous session is completely wiped before establishing new identity
        logout_user()
        session.clear()

        # Authenticate via Flask-Login
        login_user(user, remember=remember)

        role_lower = (user.role or "").lower()

        # Set session details
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_role"] = role_lower
        session.permanent = remember

        # Attach display name to session for instant header render
        if role_lower == "student" and user.student_profile:
            session["display_name"] = user.student_profile.name
            session["profile_id"] = user.student_profile.id
        elif role_lower == "recruiter" and user.recruiter_profile:
            session["display_name"] = user.recruiter_profile.name
            session["profile_id"] = user.recruiter_profile.id
        elif role_lower == "admin":
            session["display_name"] = "College Administrator"
        else:
            session["display_name"] = user.email.split("@")[0].replace(".", " ").title()

        session["show_release_notes"] = True
        flash(f"Welcome back, {session['display_name']}!", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("/login"):
            # Ensure destination URL role matches user's authenticated role to avoid 403 Forbidden
            is_mismatched = (
                (role_lower == "student" and (next_page.startswith("/recruiter") or next_page.startswith("/admin"))) or
                (role_lower == "recruiter" and (next_page.startswith("/student") or next_page.startswith("/admin"))) or
                (role_lower == "admin" and (next_page.startswith("/student") or next_page.startswith("/recruiter")))
            )
            if not is_mismatched:
                return redirect(next_page)

        if role_lower == "student":
            return redirect(url_for("student.dashboard"))
        elif role_lower == "recruiter":
            return redirect(url_for("recruiter.dashboard"))
        elif role_lower == "admin":
            return redirect(url_for("admin.dashboard"))
        else:
            return redirect(url_for("student.dashboard"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Public registration has been decommissioned. Accounts are provisioned and managed by administrators."""
    flash("Public account registration is disabled. Please contact your campus placement administrator or sign in using your verified credentials.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear session and log user out with Flask-Login."""
    logout_user()
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/switch-role/<target_role>")
def switch_role(target_role):
    """Intuitive 1-click role switcher for evaluating different portals."""
    role_map = {
        "student": "student@demo.com",
        "recruiter": "recruiter@demo.com",
        "admin": "admin@placementiq.ai",
    }
    email = role_map.get(target_role.lower())
    if not email:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()
    if user:
        logout_user()
        session.clear()
        login_user(user)
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_role"] = user.role.lower()
        if user.role.lower() == "student" and user.student_profile:
            session["display_name"] = user.student_profile.name
            session["profile_id"] = user.student_profile.id
            flash("Switched to Student Demo Workspace", "success")
            return redirect(url_for("student.dashboard"))
        elif user.role.lower() == "recruiter" and user.recruiter_profile:
            session["display_name"] = user.recruiter_profile.name
            session["profile_id"] = user.recruiter_profile.id
            session["company_name"] = user.recruiter_profile.company.name if user.recruiter_profile.company else ""
            flash("Switched to Recruiter Demo Studio", "success")
            return redirect(url_for("recruiter.dashboard"))
        elif user.role.lower() == "admin":
            session["display_name"] = "College Administrator"
            flash("Switched to Institutional Command", "success")
            return redirect(url_for("admin.dashboard"))

    return redirect(url_for("auth.login"))


# --- REST API Endpoints ---

@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """REST API endpoint for authentication."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    login_user(user)
    session["user_id"] = user.id
    session["user_email"] = user.email
    session["user_role"] = user.role.lower()

    display_name = user.email
    if user.role.lower() == "student" and user.student_profile:
        display_name = user.student_profile.name
    elif user.role.lower() == "recruiter" and user.recruiter_profile:
        display_name = user.recruiter_profile.name

    session["display_name"] = display_name

    return jsonify({
        "success": True,
        "user": user.to_dict(),
        "display_name": display_name,
        "redirect_url": f"/{user.role.lower()}/dashboard"
    })


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    """Return currently authenticated user profile."""
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False}), 200
    
    payload = user.to_dict()
    if user.role.lower() == "student" and user.student_profile:
        payload["profile"] = user.student_profile.to_dict()
    elif user.role.lower() == "recruiter" and user.recruiter_profile:
        payload["profile"] = user.recruiter_profile.to_dict()
    
    return jsonify({"authenticated": True, "user": payload})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """REST API endpoint to clear session and logout."""
    logout_user()
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})
