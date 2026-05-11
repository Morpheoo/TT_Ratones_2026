import os
import sys
from sqlalchemy import text

sys.path.append(os.getcwd())

from src.db.connection import get_db_engine


def migrate():
    print("Running migration: Add behavior_edits audit table...")
    engine = get_db_engine()
    if not engine:
        print("[ERROR] Could not connect to database.")
        return

    with engine.connect() as conn:
        try:
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS behavior_edits (
                    id              SERIAL PRIMARY KEY,
                    experiment_id   INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
                    edited_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    edited_by_email TEXT,
                    edited_role     TEXT,
                    edited_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    before_open     FLOAT,
                    before_closed   FLOAT,
                    before_grooming FLOAT,
                    before_thigmo   FLOAT,
                    after_open      FLOAT,
                    after_closed    FLOAT,
                    after_grooming  FLOAT,
                    after_thigmo    FLOAT,
                    note            TEXT
                );
                """
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_behavior_edits_exp "
                "ON behavior_edits(experiment_id, edited_at DESC);"
            ))
            conn.commit()
            print("[OK] behavior_edits table ready.")
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            conn.rollback()


if __name__ == "__main__":
    migrate()
