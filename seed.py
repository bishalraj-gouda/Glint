#!/usr/bin/env python3
"""
Campus-Link / PlacementIQ AI - Root Database Seeding Script.
Initializes database schema, seeds foundational data, taxonomy, companies, jobs,
and creates realistic test accounts:
  - Student: student@demo.com / Student@123
  - Recruiter: recruiter@demo.com / Recruiter@123
  - Admin: admin@placementiq.ai / Admin@123

Usage:
    python seed.py
    python seed.py --password YOUR_SUPABASE_PASSWORD
    python seed.py --url "postgresql://postgres:...@.../postgres"
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure all models are registered in metadata
import models
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from models.company import Company
from models.job import Job
from models.role import Role, ROLE_STUDENT, ROLE_RECRUITER, ROLE_ADMIN
from data.seed_data import seed_database


def seed(override_url: str = None):
    """Runs database initialization and verifies demo accounts."""
    if override_url:
        os.environ["DATABASE_URL"] = override_url

    app = create_app()
    with app.app_context():
        target_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        safe_uri = target_uri
        if "@" in safe_uri and ":" in safe_uri:
            try:
                pre, post = safe_uri.split("@", 1)
                proto_user, _ = pre.rsplit(":", 1)
                safe_uri = f"{proto_user}:****@{post}"
            except Exception:
                safe_uri = target_uri

        print("\n" + "=" * 65)
        print("  CAMPUS-LINK DATABASE SEEDING ENGINE")
        print("=" * 65)
        print(f"[*] Target Database: {safe_uri}")

        if "[YOUR_DATABASE_PASSWORD]" in target_uri:
            print("\n[!] NOTICE: Supabase connection placeholder '[YOUR_DATABASE_PASSWORD]' detected.")
            print("[*] To seed directly on Supabase, run:")
            print("      python seed.py --password YOUR_ACTUAL_PASSWORD")
            print("    or replace [YOUR_DATABASE_PASSWORD] in your .env file.")
            print("[*] Defaulting to local SQLite database for now...\n")

        print("[*] Ensuring all database tables exist...")
        db.create_all()

        print("[*] Seeding foundational placement data (departments, skills, jobs, applications)...")
        # Ensure default roles exist
        for role_name in (ROLE_STUDENT, ROLE_RECRUITER, ROLE_ADMIN):
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name, description=f"{role_name.capitalize()} account role"))
        db.session.commit()

        seed_database()

        # Ensure demo accounts exist even if seed_database was already run
        print("[*] Verifying demo accounts...")

        # 1. Student Demo Account
        student_user = User.query.filter_by(email="student@demo.com").first()
        if not student_user:
            student_user = User(email="student@demo.com", role=ROLE_STUDENT)
            student_user.set_password("Student@123")
            db.session.add(student_user)
            db.session.flush()

            student_profile = Student(
                user_id=student_user.id,
                name="Demo Student",
                roll_number="DEMO-2026",
                department_id=1,
                year=4,
                cgpa=8.75,
                target_role="Full Stack Developer",
                headline="Full Stack Engineer & AI Systems Developer",
                github_url="https://github.com/octocat",
                linkedin_url="https://linkedin.com/in/demostudent",
                portfolio_url="https://demostudent.dev",
                bio="Passionate computer science student building production full-stack web applications and AI tools.",
                readiness_score=90.0,
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=DEMO-2026"
            )
            db.session.add(student_profile)
            db.session.commit()
            print("  [+] Created demo student account: student@demo.com")
        else:
            student_user.set_password("Student@123")
            student_user.role = ROLE_STUDENT
            db.session.commit()
            print("  [+] Verified demo student account: student@demo.com")

        # 2. Recruiter Demo Account
        recruiter_user = User.query.filter_by(email="recruiter@demo.com").first()
        if not recruiter_user:
            recruiter_user = User(email="recruiter@demo.com", role=ROLE_RECRUITER)
            recruiter_user.set_password("Recruiter@123")
            db.session.add(recruiter_user)
            db.session.flush()

            company = Company.query.first()
            recruiter_profile = Recruiter(
                user_id=recruiter_user.id,
                company_id=company.id if company else 1,
                name="Demo Recruiter",
                designation="Lead Technical Talent Partner",
                phone="+91 99999 88888"
            )
            db.session.add(recruiter_profile)
            db.session.commit()
            print("  [+] Created demo recruiter account: recruiter@demo.com")
        else:
            recruiter_user.set_password("Recruiter@123")
            recruiter_user.role = ROLE_RECRUITER
            db.session.commit()
            print("  [+] Verified demo recruiter account: recruiter@demo.com")

        print("\n" + "=" * 65)
        print("  DATABASE INITIALIZATION & SEEDING COMPLETE!")
        print("=" * 65)
        print("Available Test Accounts:")
        print("  - Student:   student@demo.com   / Student@123")
        print("  - Recruiter: recruiter@demo.com / Recruiter@123")
        print("  - Admin:     admin@placementiq.ai / Admin@123")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus-Link Database Seeder")
    parser.add_argument("--password", help="Supabase database password to replace placeholder")
    parser.add_argument("--url", help="Direct Database URL to connect to")
    args = parser.parse_args()

    custom_url = args.url
    if args.password:
        base_url = "postgresql://postgres.oxjxpkwkrtbidvfwfvuq:[YOUR_DATABASE_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        custom_url = base_url.replace("[YOUR_DATABASE_PASSWORD]", args.password)

    seed(override_url=custom_url)
