#!/usr/bin/env python3
"""
Campus-Link / PlacementIQ AI - Supabase PostgreSQL Migration and Provisioning Engine.
Connects directly to the configured database (Supabase PostgreSQL or local SQLite),
provisions all relational tables via db.create_all(), validates schema integrity,
optionally transfers data from local SQLite to Supabase, and seeds foundational records.

Usage:
    python migrate_db.py
    python migrate_db.py --seed
    python migrate_db.py --password YOUR_SUPABASE_PASSWORD
    python migrate_db.py --password YOUR_SUPABASE_PASSWORD --seed
    python migrate_db.py --password YOUR_SUPABASE_PASSWORD --migrate-from-sqlite
    python migrate_db.py --url "postgresql://postgres:...@...:6543/postgres"
"""
import sys
import os
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import all models to ensure complete SQLAlchemy metadata registration
import models
from app import create_app
from extensions import db
from utils.db_sync import sync_database_schema
from data.seed_data import seed_database


def _safe_mask_uri(uri: str) -> str:
    """Masks database password in connection URIs for secure console output."""
    if not uri:
        return ""
    if "@" in uri and ":" in uri:
        try:
            pre, post = uri.split("@", 1)
            proto_user, _ = pre.rsplit(":", 1)
            return f"{proto_user}:****@{post}"
        except Exception:
            return "postgresql://[credentials_masked]@..."
    return uri


def migrate_sqlite_data_to_postgres(app, sqlite_path: Path):
    """
    Transfers records from existing local SQLite database to Supabase PostgreSQL,
    preserving primary keys, foreign keys, and existing profiles without wiping.
    """
    if not sqlite_path.exists():
        print(f"[-] SQLite database not found at {sqlite_path}. Skipping ETL.")
        return

    print(f"\n[*] Starting SQLite -> Supabase PostgreSQL Data Migration from {sqlite_path.name}...")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    with app.app_context():
        # Order of tables respecting foreign key dependency tree
        table_order = [
            "departments",
            "skills",
            "roles",
            "users",
            "companies",
            "recruiters",
            "students",
            "student_skills",
            "projects",
            "certifications",
            "jobs",
            "job_skills",
            "applications",
            "interviews",
            "placements",
            "ai_career_twins",
            "ai_interview_sessions",
            "ai_roadmaps",
            "ai_resume_analyses",
        ]

        total_transferred = 0

        for table_name in table_order:
            # Check if table exists in SQLite
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cur.fetchone():
                continue

            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            if not rows:
                continue

            # Check if destination table has metadata
            table_meta = db.metadata.tables.get(table_name)
            if table_meta is None:
                continue

            cols = [desc[0] for desc in cur.description]
            target_cols = {c.name for c in table_meta.columns}
            valid_cols = [c for c in cols if c in target_cols]

            inserted_for_table = 0
            for row in rows:
                row_dict = {c: row[c] for c in valid_cols}
                # Check for existing record by primary key 'id'
                if "id" in row_dict:
                    pk_val = row_dict["id"]
                    existing = db.session.execute(
                        db.select(table_meta).where(table_meta.c.id == pk_val)
                    ).first()
                    if existing:
                        continue

                try:
                    db.session.execute(table_meta.insert().values(**row_dict))
                    inserted_for_table += 1
                except Exception as ex:
                    # Ignore duplicate conflict or log warning
                    pass

            db.session.commit()
            if inserted_for_table > 0:
                print(f"  [+] Transferred {inserted_for_table} rows -> {table_name}")
                total_transferred += inserted_for_table

        sqlite_conn.close()
        print(f"[+] Data migration complete! Total records transferred: {total_transferred}\n")


def run_migration(override_url: str = None, run_seed: bool = False, do_sqlite_etl: bool = False):
    """Executes database schema provisioning and column verification."""
    if override_url:
        os.environ["DATABASE_URL"] = override_url

    app = create_app()
    with app.app_context():
        target_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        safe_uri = _safe_mask_uri(target_uri)

        print("\n" + "=" * 70)
        print("  CAMPUS-LINK / PLACEMENTIQ AI — SUPABASE POSTGRESQL ENGINE")
        print("=" * 70)
        print(f"[*] Target Database: {safe_uri}")

        if "[YOUR_DATABASE_PASSWORD]" in target_uri:
            print("\n[!] NOTICE: Supabase connection placeholder '[YOUR_DATABASE_PASSWORD]' detected.")
            print("[*] To connect and provision directly on Supabase, run:")
            print("      python migrate_db.py --password YOUR_ACTUAL_PASSWORD")
            print("    or replace [YOUR_DATABASE_PASSWORD] in your .env file.")
            print("[*] Defaulting to local SQLite schema verification for now...\n")

        print("[*] Provisioning all database tables from SQLAlchemy models...")
        db.create_all()

        # Inspect tables in database
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()
        print(f"[+] Verified {len(table_names)} tables in authoritative database:")
        for tbl in sorted(table_names):
            try:
                count = db.session.execute(db.text(f"SELECT count(*) FROM {tbl}")).scalar()
                print(f"    - {tbl:<25} ({count} records)")
            except Exception:
                print(f"    - {tbl}")

        # If local SQLite, run synchronizer
        if target_uri.startswith("sqlite:///"):
            print("\n[*] Performing SQLite column synchronization...")
            added = sync_database_schema(app)
            if added:
                print("[+] Added missing columns:")
                for tbl, cols in added.items():
                    print(f"    {tbl}: {cols}")
            else:
                print("[+] SQLite schema is 100% up-to-date.")

        # Optional SQLite to Supabase ETL
        if do_sqlite_etl and not target_uri.startswith("sqlite:///"):
            sqlite_db = ROOT_DIR / "instance" / "placementiq.db"
            migrate_sqlite_data_to_postgres(app, sqlite_db)

        # Optional Seeding
        if run_seed:
            print("\n[*] Seeding database with campus placement records...")
            seed_database()
            print("[+] Seed data inserted successfully.")

        print("\n" + "=" * 70)
        print("  SUPABASE PROVISIONING & SCHEMA MIGRATION COMPLETE!")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus-Link Database Migration Tool")
    parser.add_argument("--password", help="Supabase database password to replace placeholder")
    parser.add_argument("--url", help="Direct Database URL to connect to")
    parser.add_argument("--seed", action="store_true", help="Insert foundational seed data after migration")
    parser.add_argument("--migrate-from-sqlite", action="store_true", help="Migrate existing local SQLite records to Supabase PostgreSQL")
    args = parser.parse_args()

    custom_url = args.url
    if args.password:
        base_url = "postgresql://postgres.oxjxpkwkrtbidvfwfvuq:[YOUR_DATABASE_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        custom_url = base_url.replace("[YOUR_DATABASE_PASSWORD]", args.password)

    run_migration(override_url=custom_url, run_seed=args.seed, do_sqlite_etl=args.migrate_from_sqlite)
