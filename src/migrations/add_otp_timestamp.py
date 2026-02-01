from sqlalchemy import text
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine

def run_migration():
    print("[*] Agregando timestamp para OTP...")
    engine = get_db_engine()
    if not engine:
        return

    with engine.connect() as conn:
        try:
            # Check if column exists
            check = text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='verification_code_created_at'")
            if not conn.execute(check).fetchone():
                print("[*] Creando columna verification_code_created_at...")
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_code_created_at TIMESTAMP"))
                conn.commit()
                print("[+] Columna creada.")
            else:
                print("[*] La columna ya existe.")
        except Exception as e:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    run_migration()
