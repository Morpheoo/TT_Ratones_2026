from sqlalchemy import text
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine

def run_migration():
    print("[*] Iniciando actualización de constraint de roles...")
    engine = get_db_engine()
    if not engine:
        print("[-] Error: No se pudo conectar a la base de datos.")
        return

    with engine.connect() as conn:
        try:
            # 1. Eliminar constraint anterior
            print("[*] Eliminando constraint 'users_role_check'...")
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;"))
            
            # 2. Agregar nuevo constraint más flexible
            print("[*] Agregando nuevo constraint...")
            # Permitimos: admin, investigador, Investigador, Estudiante
            new_constraint = """
            ALTER TABLE users 
            ADD CONSTRAINT users_role_check 
            CHECK (role IN ('admin', 'investigador', 'Investigador', 'estudiante', 'Estudiante'));
            """
            conn.execute(text(new_constraint))
            
            conn.commit()
            print("[+] Roles actualizados correctamente.")
            
        except Exception as e:
            print(f"[-] Error actualizando roles: {e}")

if __name__ == "__main__":
    run_migration()
