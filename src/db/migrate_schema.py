import os
import sys
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.append(os.getcwd())

from src.db.connection import get_db_engine

def run_migration():
    print("Starting schema migration (ASCII mode)...")
    engine = get_db_engine()
    if not engine:
        print("Could not connect to database.")
        return

    with engine.connect() as conn:
        columns_to_add = [
            ("grooming_duration", "FLOAT DEFAULT 0.0"),
            ("thigmotaxis_duration", "FLOAT DEFAULT 0.0")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                print(f"Attempting to add column {col_name}...")
                conn.execute(text(f"ALTER TABLE analysis_results ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[OK] Added column {col_name}")
            except Exception as e:
                # If column exists, it throws a ProgrammingError usually. 
                # We interpret this as "already exists" for now or just log it safely.
                print(f"[INFO] Failed to add {col_name} (might exist): {e}")
                conn.rollback()

if __name__ == "__main__":
    run_migration()
