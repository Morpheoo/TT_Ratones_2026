"""
Script de Prueba: Verificar Conexión a Base de Datos Remota
Ejecutar: python test_remote_db.py
"""

from src.db.connection import get_db_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    print("\n" + "="*70)
    print("PRUEBA DE CONEXIÓN A BASE DE DATOS REMOTA")
    print("="*70 + "\n")
    
    # Mostrar configuración (sin mostrar contraseña completa)
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "unknown")
    db_user = os.getenv("POSTGRES_USER", "unknown")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    
    print("Configuración actual:")
    print(f"  - Host: {db_host}")
    print(f"  - Port: {db_port}")
    print(f"  - Database: {db_name}")
    print(f"  - User: {db_user}")
    print(f"  - Password: {'*' * min(len(db_password), 8)}...")
    print()
    
    # Verificar que no sea localhost
    if db_host == "localhost":
        print("[ADVERTENCIA] Estás usando 'localhost'. Esto es local, no remoto.")
        print("             Para usar BD remota, actualiza DB_HOST en .env\n")
    
    print("Intentando conexión...")
    engine = get_db_engine()
    
    if not engine:
        print("\n[ERROR] No se pudo obtener el engine de base de datos")
        print("\nPosibles causas:")
        print("  1. Credenciales incorrectas en .env")
        print("  2. Host/puerto incorrectos")
        print("  3. Base de datos no existe")
        print("  4. Firewall bloqueando conexión")
        print("  5. Servicio de BD no está activo")
        return False
    
    try:
        with engine.connect() as conn:
            # Test 1: Conexión básica
            print("[OK] Conexión establecida exitosamente\n")
            
            result = conn.execute(text("SELECT versión()")).scalar()
            print(f"[OK] PostgreSQL Versión:")
            print(f"     {result[:80]}...\n")
            
            # Test 2: Verificar tablas
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = conn.execute(tables_query).fetchall()
            
            if tables:
                print(f"[OK] Tablas encontradas en la base de datos: {len(tables)}")
                for table in tables:
                    print(f"     - {table[0]}")
                print()
            else:
                print("[ADVERTENCIA] No se encontraron tablas en 'public' schema")
                print("              Necesitas ejecutar schema.sql primero\n")
            
            # Test 3: Verificar tabla users
            try:
                user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                print(f"[OK] Tabla 'users' existe con {user_count} registro(s)")
                
                # Verificar si hay admin
                admin_count = conn.execute(text(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin'"
                )).scalar()
                print(f"[OK] Usuarios administradores: {admin_count}")
                
                if admin_count == 0:
                    print("[ADVERTENCIA] No hay usuarios admin. Ejecuta reset_db_admin.py")
                
            except Exception as e:
                print(f"[ADVERTENCIA] Tabla 'users' no existe o tiene problemas: {e}")
                print("              Ejecuta las migraciones correspondientes")
            
            print()
            
            # Test 4: Verificar otras tablas importantes
            important_tables = ['experiments', 'analysis_results', 'security_audit_log']
            for table in important_tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"[OK] Tabla '{table}': {count} registro(s)")
                except:
                    print(f"[ADVERTENCIA] Tabla '{table}' no existe")
            
            print("\n" + "="*70)
            print("RESULTADO: Conexión EXITOSA ✓")
            print("="*70 + "\n")
            
            if db_host != "localhost":
                print("Tu aplicación está lista para funcionar desde cualquier lugar.")
                print("Cualquier persona con acceso a la app puede registrarse y usar el sistema.\n")
            
            return True
            
    except Exception as e:
        print("\n" + "="*70)
        print("RESULTADO: Conexión FALLIDA ✗")
        print("="*70)
        print(f"\nError: {e}\n")
        print("Soluciones sugeridas:")
        print("  1. Verifica que las credenciales en .env sean correctas")
        print("  2. Asegúrate de que el servicio de BD esté activo")
        print("  3. Verifica tu conexión a internet")
        print("  4. Revisa que el firewall no bloquee el puerto 5432")
        print("  5. Consulta la documentación de tu proveedor de BD")
        print()
        return False

if __name__ == "__main__":
    try:
        success = test_connection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCELADO] Prueba interrumpida por el usuario")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] {e}")
        exit(1)
