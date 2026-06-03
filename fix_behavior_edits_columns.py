"""
Script para agregar las columnas faltantes 'before_center' y 'after_center' 
a la tabla behavior_edits.

Este script es seguro ejecutarlo múltiples veces (usa ADD COLUMN IF NOT EXISTS).
"""
import os
import sys
from sqlalchemy import text

sys.path.append(os.getcwd())

from src.db.connection import get_db_engine


def fix_behavior_edits_table():
    print("🔧 Actualizando tabla behavior_edits...")
    print("=" * 60)
    
    engine = get_db_engine()
    if not engine:
        print("❌ [ERROR] No se pudo conectar a la base de datos.")
        print("   Verifica que Docker esté corriendo y la BD esté disponible.")
        return False

    with engine.connect() as conn:
        try:
            # Agregar columna before_center
            print("📝 Agregando columna 'before_center'...")
            conn.execute(text(
                "ALTER TABLE behavior_edits ADD COLUMN IF NOT EXISTS before_center FLOAT;"
            ))
            
            # Agregar columna after_center
            print("📝 Agregando columna 'after_center'...")
            conn.execute(text(
                "ALTER TABLE behavior_edits ADD COLUMN IF NOT EXISTS after_center FLOAT;"
            ))
            
            conn.commit()
            print("=" * 60)
            print("✅ [OK] Tabla behavior_edits actualizada correctamente.")
            print("\nAhora puedes editar tiempos de experimentos sin errores.")
            return True
            
        except Exception as e:
            print("=" * 60)
            print(f"❌ [ERROR] Actualización fallida: {e}")
            conn.rollback()
            return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FIX: Agregar columnas center a behavior_edits")
    print("=" * 60 + "\n")
    
    success = fix_behavior_edits_table()
    
    if success:
        print("\n✨ Proceso completado exitosamente.")
    else:
        print("\n⚠️  Proceso terminó con errores.")
    
    print()
