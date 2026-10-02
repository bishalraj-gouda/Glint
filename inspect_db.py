#!/usr/bin/env python3
"""
Campus-Link / PlacementIQ AI - Database Inspector Utility.
Allows quick CLI viewing of tables, row counts, schema, and sample records.

Usage:
    python inspect_db.py                    # Summarizes all tables and row counts
    python inspect_db.py --table users      # Shows first 10 rows of 'users'
    python inspect_db.py --table jobs --limit 5
    python inspect_db.py --tables           # Lists all table names
"""
import sys
import argparse
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "instance" / "placementiq.db"


def get_connection():
    if not DB_PATH.exists():
        print(f"[-] Database not found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def list_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall() if not row[0].startswith("sqlite_")]
    return tables


def show_summary(conn):
    tables = list_tables(conn)
    cur = conn.cursor()
    print("=" * 60)
    print(f"  PlacementIQ Database Overview ({DB_PATH.name})")
    print(f"  Path: {DB_PATH}")
    print(f"  Size: {DB_PATH.stat().st_size / 1024:.1f} KB")
    print("=" * 60)
    print(f"{'Table Name':<35} | {'Row Count':<10}")
    print("-" * 60)
    total_rows = 0
    for tbl in tables:
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\"").fetchone()[0]
            total_rows += count
            print(f"{tbl:<35} | {count:<10}")
        except Exception as e:
            print(f"{tbl:<35} | ERROR: {e}")
    print("-" * 60)
    print(f"{'TOTAL TABLES: ' + str(len(tables)):<35} | {total_rows:<10} total rows")
    print("=" * 60)
    print("\nTip: View specific table records with: python inspect_db.py --table <table_name>")


def show_table(conn, table_name: str, limit: int = 10):
    cur = conn.cursor()
    tables = list_tables(conn)
    if table_name not in tables:
        print(f"[-] Table '{table_name}' does not exist.")
        print(f"[*] Available tables: {', '.join(tables)}")
        return

    cur.execute(f"PRAGMA table_info(\"{table_name}\");")
    columns = [col[1] for col in cur.fetchall()]

    cur.execute(f"SELECT * FROM \"{table_name}\" LIMIT ?", (limit,))
    rows = cur.fetchall()

    print("\n" + "=" * 70)
    print(f"  Table: {table_name} (Showing up to {limit} rows)")
    print("=" * 70)
    if not rows:
        print("  (Table is currently empty)")
        return

    print(" | ".join(columns[:8]) + ("..." if len(columns) > 8 else ""))
    print("-" * 70)
    for r in rows:
        formatted_row = [str(val)[:25] if val is not None else "NULL" for val in r[:8]]
        print(" | ".join(formatted_row) + ("..." if len(r) > 8 else ""))
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="PlacementIQ Database Inspector")
    parser.add_argument("--table", type=str, help="Name of table to inspect")
    parser.add_argument("--limit", type=int, default=10, help="Max rows to display (default: 10)")
    parser.add_argument("--tables", action="store_true", help="List all table names only")

    args = parser.parse_args()
    conn = get_connection()

    try:
        if args.tables:
            for t in list_tables(conn):
                print(t)
        elif args.table:
            show_table(conn, args.table, args.limit)
        else:
            show_summary(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
