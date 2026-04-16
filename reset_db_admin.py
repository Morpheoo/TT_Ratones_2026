from src.db.connection import get_db_engine
from sqlalchemy import text
import bcrypt

def hash_password(password: str) -> str:
    """Bcrypt hashing."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def reset_admin():
    engine = get_db_engine()
    if not engine:
        print("No DB connection.")
        return

    # Definimos a los dos únicos administradores del sistema
    admins = [
        {
            "name": "Dr. César Augusto Sandino Reyes López",
            "username": "careyes@ipn.mx", # Reemplazar si el correo es distinto
            "password": "Admin_TT2026_Seguro!"
        },
        {
            "name": "Habid Portocarrero Rodriguez",
            "username": "hportocarreror1700@alumno.ipn.mx",
            "password": "Admin_TT2026_Seguro!"
        }
    ]
    role = "admin"
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Eliminar administradores genéricos (como 'admin')
            conn.execute(text("DELETE FROM users WHERE username = 'admin'"))
            print("[-] Limpiado administrador genérico ('admin').")
            
            # 2. Insertar o Actualizar a los administradores sin romper sus Foreign Keys
            for admin in admins:
                pwd_hash = hash_password(admin["password"])
                upsert = text("""
                    INSERT INTO users (username, password_hash, role, is_active, is_verified) 
                    VALUES (:u, :p, :r, TRUE, TRUE)
                    ON CONFLICT (username) 
                    DO UPDATE SET 
                        password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        is_active = TRUE,
                        is_verified = TRUE;
                """)
                conn.execute(upsert, {"u": admin["username"], "p": pwd_hash, "r": role})
                print(f"[+] Administrador Configurado: {admin['name']}")
                print(f"    - Usuario (Correo): {admin['username']}")
                print(f"    - Pass Temporal:    {admin['password']}\n")

if __name__ == "__main__":
    reset_admin()
