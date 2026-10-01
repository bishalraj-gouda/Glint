"""
AI Routes Package for Campus-Link.
Registers student, recruiter, and admin AI interfaces and API services.
"""
from routes.ai.student_ai import student_ai_bp
from routes.ai.recruiter_ai import recruiter_ai_bp
from routes.ai.admin_ai import admin_ai_bp

__all__ = [
    "student_ai_bp",
    "recruiter_ai_bp",
    "admin_ai_bp",
]
