from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify, render_template
from flask_login import current_user
from extensions import db
from models.user import User


def get_current_user():
    """Retrieve the currently authenticated user object from Flask-Login or session."""
    if current_user and current_user.is_authenticated:
        return current_user
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def is_authenticated():
    """Helper checking if current user has an active authenticated session."""
    if current_user and current_user.is_authenticated:
        return True
    return bool(session.get("user_id"))


def login_required(f):
    """Decorator ensuring user is authenticated via Flask-Login or session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or "/api/" in request.path or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "status": 401}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator ensuring user has one of the specified roles (e.g. 'STUDENT', 'RECRUITER', 'ADMIN').
    Case-insensitive comparison supports both 'STUDENT' and 'student'.
    """
    normalized_expected_roles = {str(r).upper() for r in roles}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                if request.is_json or "/api/" in request.path or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required", "status": 401}), 401
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))

            user = get_current_user()
            user_role = (getattr(user, "role", "") or session.get("user_role", "")).upper()

            if user_role not in normalized_expected_roles:
                if request.is_json or "/api/" in request.path or request.path.startswith("/api/"):
                    return jsonify({
                        "error": "Forbidden: You do not have permission for this resource.",
                        "status": 403,
                        "required_roles": list(roles),
                        "current_role": user_role
                    }), 403

                # Attempt rendering custom 403 or redirect
                try:
                    return render_template("403.html", required_roles=roles, current_role=user_role), 403
                except Exception:
                    flash("Access denied: You do not have authorization for this section.", "danger")
                    if user_role == "STUDENT":
                        return redirect(url_for("student.dashboard"))
                    elif user_role == "RECRUITER":
                        return redirect(url_for("recruiter.dashboard"))
                    elif user_role == "ADMIN":
                        return redirect(url_for("admin.dashboard"))
                    return redirect(url_for("auth.login"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


student_required = role_required("STUDENT", "student")
recruiter_required = role_required("RECRUITER", "recruiter")
admin_required = role_required("ADMIN", "admin")
