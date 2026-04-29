"""
Script de diagnóstico para verificar roles de usuarios en la base de datos
"""
from src.db.connection import get_db_engine
from sqlalchemy import text

def check_roles():
    engine = get_db_engine()
    if not engine:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return

    with engine.connect() as conn:
        # Consultar todos los usuarios y sus roles
        result = conn.execute(text("""
            SELECT username, role, is_active, is_verified 
            FROM users 
            ORDER BY role, username
        """))
        
        users = result.fetchall()
        
        if not users:
            print("[INFO] No hay usuarios en la base de datos.")
            return
        
        print("\n" + "="*80)
        print("USUARIOS REGISTRADOS EN EL SISTEMA")
        print("="*80)
        
        roles_count = {}
        for user in users:
            username, role, is_active, is_verified = user
            
            # Contar roles
            roles_count[role] = roles_count.get(role, 0) + 1
            
            status = []
            if not is_active:
                status.append("INACTIVO")
            if not is_verified:
                status.append("NO VERIFICADO")
            
            status_str = f" [{', '.join(status)}]" if status else ""
            
            print(f"\n  Usuario: {username}")
            print(f"  Rol:     {role}{status_str}")
        
        print("\n" + "="*80)
        print("RESUMEN DE ROLES")
        print("="*80)
        for role, count in sorted(roles_count.items()):
            print(f"  {role}: {count} usuario(s)")
        
        print("\n" + "="*80)
        print("VERIFICACIÓN DE ROLES VÁLIDOS")
        print("="*80)
        
        valid_roles = ["admin", "investigador", "estudiante"]
        invalid_roles = [role for role in roles_count.keys() if role not in valid_roles]
        
        if invalid_roles:
            print(f"\n  [ADVERTENCIA] Se encontraron roles no válidos: {', '.join(invalid_roles)}")
            print(f"  Los roles válidos son: {', '.join(valid_roles)}")
            print(f"\n  Usuarios con roles inválidos podrían tener acceso no controlado al sistema.")
        else:
            print(f"\n  [OK] Todos los roles son válidos.")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    check_roles()
