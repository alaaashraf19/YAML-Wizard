"""
migrate_add_new_columns.py
==========================
Run this ONCE to add the new columns to the existing repo_context table.

Usage:
    cd Backend
    python migrate_add_new_columns.py

Safe to run multiple times — uses IF NOT EXISTS internally (PostgreSQL).
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set in .env")

NEW_COLUMNS = [
    # (column_name, sql_type, default)
    ("default_branch",   "VARCHAR",  "'main'"),
    ("test_commands",    "JSONB",    "'[]'::jsonb"),
    ("build_commands",   "JSONB",    "'[]'::jsonb"),
    ("env_vars",         "JSONB",    "'[]'::jsonb"),
    ("services",         "JSONB",    "'[]'::jsonb"),
    ("test_runner_details", "JSONB", "'[]'::jsonb"),
    ("test_reports",     "JSONB",    "'[]'::jsonb"),
    ("created_at",       "TIMESTAMPTZ", "NOW()"),
]

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

for col_name, col_type, col_default in NEW_COLUMNS:
    try:
        cur.execute(f"""
            ALTER TABLE repo_context
            ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {col_default};
        """)
        print(f"  ✓ {col_name} ({col_type})")
    except Exception as e:
        print(f"  ✗ {col_name}: {e}")

cur.close()
conn.close()
print("\nMigration complete.")
