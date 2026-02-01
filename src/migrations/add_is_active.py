from sqlalchemy import text
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine

def run_migration():
    print("[*] Agregando columna is_active para suspensión de cuentas...")
    engine = get_db_engine()
    if not engine:
        return

    with engine.connect() as conn:
        try:
            # Check if column exists
            check = text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_active'")
            if not conn.execute(check).fetchone():
                print("[*] Creando columna is_active...")
                # Por defecto TRUE (activos)
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.commit()
                # Asegurar que los existentes sean TRUE
                conn.execute(text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
                conn.commit()
                print("[+] Columna creada y usuarios existentes activados.")
            else:
                print("[*] La columna ya existe.")
        except Exception as e:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    run_migration()
