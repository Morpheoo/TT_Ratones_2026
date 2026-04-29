"""
Migración: Añadir campos de perfil extendidos a la tabla users
Soporta dos tipos de perfil: Estudiante e Investigador/Docente
Ejecutar: python src/db/migrations/add_user_profile_fields.py
"""

from sqlalchemy import text
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.db.connection import get_db_engine

def run_migration():
    """Añade campos de perfil para estudiantes e investigadores."""
    engine = get_db_engine()
    if not engine:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return False
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Campos comunes
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS full_name VARCHAR(200),
                    ADD COLUMN IF NOT EXISTS accepted_terms BOOLEAN DEFAULT FALSE
                """))
                print("[OK] Campos comunes añadidos (full_name, accepted_terms)")
                
                # Campos específicos de ESTUDIANTE
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS boleta VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS carrera VARCHAR(150),
                    ADD COLUMN IF NOT EXISTS escuela VARCHAR(100)
                """))
                print("[OK] Campos de estudiante añadidos (boleta, carrera, escuela)")
                
                # Campos específicos de INVESTIGADOR/DOCENTE
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS num_empleado VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS area VARCHAR(150),
                    ADD COLUMN IF NOT EXISTS centro VARCHAR(100)
                """))
                print("[OK] Campos de investigador añadidos (num_empleado, area, centro)")
                
        print("\n[OK] Migración completada exitosamente.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    print("=== Migración: Campos de Perfil de Usuario ===\n")
    success = run_migration()
    sys.exit(0 if success else 1)
