import os
from flask import Flask, render_template, session, redirect, url_for
from config import config_by_name
from extensions import db, login_manager, migrate
from routes import register_blueprints
from utils.auth import get_current_user
from utils.db_sync import sync_database_schema


def create_app(config_name: str = None) -> Flask:
    """Application factory for PlacementIQ AI."""
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Register all modular blueprints
    register_blueprints(app)

    # Automatically ensure SQLite schema and all model columns exist
    sync_database_schema(app)

    # Landing page route
    @app.route("/")
    def index():
        if "user_id" in session:
            role = (session.get("user_role") or "").lower()
            if role == "student":
                return redirect(url_for("student.dashboard"))
            elif role == "recruiter":
                return redirect(url_for("recruiter.dashboard"))
            elif role == "admin":
                return redirect(url_for("admin.dashboard"))
        return render_template("landing.html")

    # Direct API route alias for skill gap analyze
    @app.route("/api/skill-gap/analyze", methods=["GET", "POST"])
    @app.route("/api/skill_gap/analyze", methods=["GET", "POST"])
    def root_api_skill_gap_analyze():
        from routes.ai.student_ai import api_analyze_skill_gap
        return api_analyze_skill_gap()

    # Global template context processor
    @app.context_processor
    def inject_global_template_vars():
        user = get_current_user()
        return {
            "current_user": user,
            "session_user_role": (user.role.lower() if user and user.role else session.get("user_role", "")),
            "session_display_name": session.get("display_name", user.email if user else "User"),
            "session_company_name": session.get("company_name", "")
        }

    # Error handling
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    # Custom CLI command to seed the database
    @app.cli.command("seed-db")
    def seed_db_command():
        """Seed the database with realistic demo records."""
        from data.seed_data import seed_database
        with app.app_context():
            db.create_all()
            seed_database()
            print("Database successfully seeded with realistic campus placement records!")

    # Custom CLI command to non-destructively patch missing columns (Option 1)
    @app.cli.command("migrate-db")
    def migrate_db_command():
        """Inspect and add any missing columns in SQLite without wiping data."""
        added = sync_database_schema(app)
        if added:
            print("Added missing columns:")
            for tbl, cols in added.items():
                print(f"  {tbl}: {cols}")
        else:
            print("All tables and columns are already fully synchronized.")
        print("Schema sync complete!")

    # Custom CLI command to drop, recreate, and re-seed (Option 2)
    @app.cli.command("reset-db")
    def reset_db_command():
        """Drop all tables, recreate them, and re-seed with fresh data."""
        from data.seed_data import seed_database
        with app.app_context():
            db.drop_all()
            db.create_all()
            seed_database()
            print("Database has been completely recreated and freshly seeded!")

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    # Run locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
