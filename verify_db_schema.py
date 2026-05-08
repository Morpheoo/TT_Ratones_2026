"""Script temporal para verificar estructura de la tabla users"""
from src.db.connection import get_db_engine
from sqlalchemy import text

engine = get_db_engine()
if engine:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """))
        
        print("\n=== ESTRUCTURA TABLA USERS ===\n")
        print(f"{'Campo':<25} {'Tipo':<20} {'Null':<10}")
        print("-" * 60)
        for row in result:
            print(f"{row[0]:<25} {row[1]:<20} {row[2]:<10}")
        print("\n" + "="*60)
else:
    print("[ERROR] No hay conexión a la base de datos")
