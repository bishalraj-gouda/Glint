import os
from app import create_app
from extensions import db
from models.user import User

app = create_app()

with app.app_context():
    # Ensure all tables exist on startup
    db.create_all()
    # If fresh database, automatically populate baseline demo dataset
    try:
        if not User.query.first():
            from data.seed_data import seed_database
            seed_database()
    except Exception as e:
        app.logger.warning(f"Database bootstrap initialization note: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
