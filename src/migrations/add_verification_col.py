from sqlalchemy import text
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine

def run_migration():
    print("[*] Iniciando migración de base de datos...")
    engine = get_db_engine()
    if not engine:
        print("[-] Error: No se pudo conectar a la base de datos.")
        return

    columns_to_add = [
        ("is_verified", "BOOLEAN DEFAULT FALSE"),
        ("verification_code", "VARCHAR(6)")
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists
                check_query = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='{col_name}';
                """)
                res = conn.execute(check_query).fetchone()
                
                if not res:
                    print(f"[*] Agregando columna '{col_name}'...")
                    alter_query = text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
                    conn.execute(alter_query)
                    conn.commit()
                    print(f"[+] Columna '{col_name}' agregada.")
                else:
                    print(f"[*] La columna '{col_name}' ya existe.")
                    
            except Exception as e:
                print(f"[-] Error migrando '{col_name}': {e}")

    print("[+] Migración completada.")

if __name__ == "__main__":
    run_migration()
