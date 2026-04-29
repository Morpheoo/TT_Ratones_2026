"""
Migración: Actualizar constraint de role para permitir 'alumno'
Ejecutar: python src/db/migrations/update_role_constraint.py
"""

from sqlalchemy import text
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.db.connection import get_db_engine

def run_migration():
    """Actualiza el CHECK constraint para role para permitir 'alumno'."""
    engine = get_db_engine()
    if not engine:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return False
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Eliminar el constraint anterior
                conn.execute(text("""
                    ALTER TABLE users 
                    DROP CONSTRAINT IF EXISTS users_role_check
                """))
                print("[OK] Constraint anterior eliminado")
                
                # Crear nuevo constraint con 'alumno' incluido
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD CONSTRAINT users_role_check 
                    CHECK (role IN ('admin', 'investigador', 'Investigador', 'estudiante', 'Estudiante', 'alumno'))
                """))
                print("[OK] Nuevo constraint añadido con 'alumno' permitido")
                
        print("\n[OK] Migración completada exitosamente.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    print("=== Migración: Actualizar Constraint de Role ===\n")
    success = run_migration()
    sys.exit(0 if success else 1)
