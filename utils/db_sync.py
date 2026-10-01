"""
Database Schema Synchronizer and Column Migration Utility for PlacementIQ AI.
Ensures SQLite database tables match SQLAlchemy models non-destructively by
automatically appending any missing columns with safe defaults.
"""
import os
import sqlite3
from typing import Dict, List, Tuple
from flask import Flask
from extensions import db


# Safe default SQL definitions for specific model columns that may be missing in legacy SQLite files
COLUMN_DEFAULTS: Dict[str, Dict[str, str]] = {
    "jobs": {
        "eligible_departments": "VARCHAR(255) DEFAULT 'CSE, IT, DS, ECE'"
    },
    "ai_career_twins": {
        "academic_score": "FLOAT DEFAULT 50.0",
        "skill_score": "FLOAT DEFAULT 50.0",
        "project_score": "FLOAT DEFAULT 50.0",
        "interview_score": "FLOAT DEFAULT 50.0",
        "market_competitiveness": "VARCHAR(100) DEFAULT 'Premium Product Companies'",
        "metadata_json_str": "TEXT DEFAULT '{}'"
    },
    "ai_interview_sessions": {
        "feedback_json": "TEXT DEFAULT '{}'"
    },
    "ai_roadmaps": {
        "progress_percentage": "INTEGER DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT 1"
    },
    "ai_resume_analyses": {
        "job_id": "INTEGER DEFAULT NULL",
        "raw_text_snippet": "TEXT DEFAULT NULL"
    },
    "students": {
        "target_role": "VARCHAR(100) DEFAULT 'Software Engineer'",
        "preferred_locations": "VARCHAR(255) DEFAULT 'Bangalore, Hyderabad, Remote'",
        "preferred_industries": "VARCHAR(255) DEFAULT 'Technology, AI, Fintech'",
        "resume_filename": "VARCHAR(255) DEFAULT NULL",
        "bio": "TEXT DEFAULT NULL",
        "headline": "VARCHAR(255) DEFAULT NULL",
        "github_url": "VARCHAR(255) DEFAULT NULL",
        "linkedin_url": "VARCHAR(255) DEFAULT NULL",
        "portfolio_url": "VARCHAR(255) DEFAULT NULL",
        "github_data_json": "TEXT DEFAULT '{}'",
        "avatar_url": "VARCHAR(255) DEFAULT NULL",
        "readiness_score": "FLOAT DEFAULT 70.0"
    },
    "skills": {
        "category": "VARCHAR(50) DEFAULT 'technical'"
    },
    "applications": {
        "match_score": "FLOAT DEFAULT 0.0",
        "match_breakdown_json": "TEXT DEFAULT NULL"
    },
    "users": {
        "raw_password": "VARCHAR(255) DEFAULT 'Recruiter@123'"
    }
}


def sync_database_schema(app: Flask) -> Dict[str, List[str]]:
    """
    Inspects SQLite database and adds any missing columns to match SQLAlchemy models.
    Guarantees no OperationalError is thrown when querying new or updated models.
    """
    with app.app_context():
        # First ensure all tables exist
        db.create_all()

        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if not db_uri.startswith("sqlite:///"):
            return {}

        db_path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.instance_path, os.path.basename(db_path))

        if not os.path.exists(db_path):
            return {}

        added_columns: Dict[str, List[str]] = {}

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Retrieve existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = {row[0] for row in cursor.fetchall()}

            for table_name, table in db.Model.metadata.tables.items():
                if table_name not in existing_tables:
                    continue

                cursor.execute(f"PRAGMA table_info({table_name});")
                existing_cols = {row[1] for row in cursor.fetchall()}

                table_overrides = COLUMN_DEFAULTS.get(table_name, {})

                for col in table.columns:
                    if col.name not in existing_cols:
                        if col.name in table_overrides:
                            col_def = table_overrides[col.name]
                        else:
                            # Generate generic fallback definition based on column type
                            col_type_str = str(col.type).upper()
                            default_clause = "DEFAULT NULL"
                            if not col.nullable:
                                if "INT" in col_type_str:
                                    default_clause = "DEFAULT 0"
                                elif "FLOAT" in col_type_str or "NUMERIC" in col_type_str:
                                    default_clause = "DEFAULT 0.0"
                                elif "BOOL" in col_type_str:
                                    default_clause = "DEFAULT 0"
                                elif "TIME" in col_type_str or "DATE" in col_type_str:
                                    default_clause = "DEFAULT CURRENT_TIMESTAMP"
                                else:
                                    default_clause = "DEFAULT ''"
                            else:
                                if "TIME" in col_type_str or "DATE" in col_type_str:
                                    default_clause = "DEFAULT CURRENT_TIMESTAMP"
                            col_def = f"{col_type_str} {default_clause}"

                        alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_def}"
                        try:
                            cursor.execute(alter_stmt)
                            added_columns.setdefault(table_name, []).append(col.name)
                        except sqlite3.OperationalError as e:
                            # Column might have been added concurrently or SQLite syntax limitation
                            pass

            # Sanitize any empty string date/time fields to prevent 'Invalid isoformat string: empty string' ValueError
            for table_name in existing_tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                for col_info in cursor.fetchall():
                    c_name = col_info[1]
                    c_type = col_info[2].upper()
                    if "TIME" in c_type or "DATE" in c_type:
                        try:
                            cursor.execute(f"UPDATE {table_name} SET {c_name} = CURRENT_TIMESTAMP WHERE {c_name} = ''")
                        except Exception:
                            pass

            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[SchemaSync Warning] Could not sync SQLite schema: {ex}")

        return added_columns
