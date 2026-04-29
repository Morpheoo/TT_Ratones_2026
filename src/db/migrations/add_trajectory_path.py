import os
import sys
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

from src.db.connection import get_db_engine

def migrate():
    print("Running migration: Add trajectory_path to analysis_results...")
    engine = get_db_engine()
    if not engine:
        print("[ERROR] Could not connect to database.")
        return

    with engine.connect() as conn:
        try:
            # Check if column exists to avoid error or do IF NOT EXISTS logic
            # Postgres 9.6+ supports IF NOT EXISTS in ALTER TABLE but standard is often robust manually
            conn.execute(text("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS trajectory_path TEXT;"))
            conn.commit()
            print("Migration successful: 'trajectory_path' column added.")
        except Exception as e:
            print(f"Migration failed: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
