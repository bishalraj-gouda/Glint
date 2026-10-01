from flask import Flask
from routes.auth import auth_bp
from routes.student import student_bp
from routes.recruiter import recruiter_bp
from routes.admin import admin_bp
from routes.jobs import jobs_bp
from routes.applications import applications_bp
from routes.interviews import interviews_bp
from routes.analytics import analytics_bp
from routes.ai import student_ai_bp, recruiter_ai_bp, admin_ai_bp


def register_blueprints(app: Flask):
    """Register all modular application blueprints."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(student_ai_bp)
    app.register_blueprint(recruiter_ai_bp)
    app.register_blueprint(admin_ai_bp)
