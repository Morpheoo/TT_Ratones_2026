"""
Script: Ejecutar Schema en Base de Datos Remota
Este script carga el archivo schema.sql y lo ejecuta en la base de datos configurada.
Ejecutar: python setup_remote_db.py
"""

from src.db.connection import get_db_engine
from sqlalchemy import text
import os

def setup_database():
    print("\n" + "="*70)
    print("CONFIGURACIÓN DE BASE DE DATOS REMOTA")
    print("="*70 + "\n")
    
    # Verificar que schema.sql existe
    if not os.path.exists("schema.sql"):
        print("[ERROR] Archivo schema.sql no encontrado")
        print("        Asegúrate de ejecutar este script desde el directorio raíz del proyecto")
        return False
    
    print("[1/4] Conectando a la base de datos...")
    engine = get_db_engine()
    
    if not engine:
        print("[ERROR] No se pudo conectar a la base de datos")
        print("        Verifica tu archivo .env y ejecuta test_remote_db.py primero")
        return False
    
    print("[OK] Conexión establecida\n")
    
    print("[2/4] Leyendo schema.sql...")
    try:
        with open("schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()
        print(f"[OK] Schema cargado ({len(schema_sql)} caracteres)\n")
    except Exception as e:
        print(f"[ERROR] Error leyendo schema.sql: {e}")
        return False
    
    print("[3/4] Ejecutando schema en la base de datos...")
    try:
        with engine.connect() as conn:
            # Dividir en statements individuales (separados por ;)
            statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    try:
                        conn.execute(text(statement))
                        print(f"[OK] Statement {i}/{len(statements)} ejecutado")
                    except Exception as e:
                        # Algunos errores son normales (ej: tabla ya existe)
                        if "already exists" in str(e).lower():
                            print(f"[INFO] Statement {i}/{len(statements)}: {str(e).split('DETAIL')[0].strip()}")
                        else:
                            print(f"[WARN] Statement {i}/{len(statements)}: {str(e)[:100]}...")
            
            conn.commit()
        
        print("\n[OK] Schema ejecutado correctamente\n")
    except Exception as e:
        print(f"[ERROR] Error ejecutando schema: {e}")
        return False
    
    print("[4/4] Verificando tablas creadas...")
    try:
        with engine.connect() as conn:
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = conn.execute(tables_query).fetchall()
            
            expected_tables = ['users', 'experiments', 'roi_configurations', 
                             'analysis_results', 'security_audit_log']
            
            print(f"[OK] Tablas encontradas: {len(tables)}")
            for table in tables:
                status = "✓" if table[0] in expected_tables else "?"
                print(f"     [{status}] {table[0]}")
            
            missing = [t for t in expected_tables if t not in [table[0] for table in tables]]
            if missing:
                print(f"\n[ADVERTENCIA] Tablas faltantes: {', '.join(missing)}")
            else:
                print(f"\n[OK] Todas las tablas principales están creadas")
    except Exception as e:
        print(f"[ERROR] Error verificando tablas: {e}")
        return False
    
    print("\n" + "="*70)
    print("CONFIGURACIÓN COMPLETADA ✓")
    print("="*70)
    print("\nPróximos pasos:")
    print("  1. Ejecutar migraciones:")
    print("     python src/db/migrations/add_user_profile_fields.py")
    print("  2. Crear usuario administrador:")
    print("     python reset_db_admin.py")
    print("  3. Probar la aplicación:")
    print("     streamlit run Home.py")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = setup_database()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCELADO] Configuración interrumpida por el usuario")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
