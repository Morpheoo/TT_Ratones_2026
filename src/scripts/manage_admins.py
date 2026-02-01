from sqlalchemy import text
import sys
import os
import getpass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine
from src.auth import hash_password

import argparse

def create_or_promote_admin():
    parser = argparse.ArgumentParser(description="Gestión de Administradores")
    parser.add_argument("--create", action="store_true", help="Crear nuevo admin")
    parser.add_argument("--promote", action="store_true", help="Promover usuario existente")
    parser.add_argument("--email", type=str, help="Correo del usuario")
    parser.add_argument("--password", type=str, help="Contraseña (solo para crear)")
    
    args = parser.parse_args()
    
    print("=== Gestion de Administradores - TT Ratones 2026 ===")
    
    # Modo Interactivo vs Modo CLI
    if not args.email:
        email = input("Ingrese el correo del usuario a gestionar: ").strip()
    else:
        email = args.email

    engine = get_db_engine()
    if not engine:
        return

    with engine.connect() as conn:
        # 1. Buscar si existe
        query = text("SELECT id, role FROM users WHERE username = :email")
        user = conn.execute(query, {"email": email}).fetchone()
        
        if user:
            print(f"[*] El usuario {email} existe con rol '{user[1]}'.")
            if args.promote or input(f"¿Promover a {email} a ADMIN? (s/n): ").lower() == 's':
                update = text("UPDATE users SET role = 'admin' WHERE username = :email")
                conn.execute(update, {"email": email})
                conn.commit()
                print(f"[+] ¡Éxito! {email} ahora es Administrador.")
        else:
            print(f"[*] El usuario no existe.")
            if args.create or input("¿Crear NUEVO usuario ADMIN? (s/n): ").lower() == 's':
                if args.password:
                    pwd = args.password
                else:
                    pwd = getpass.getpass("Ingrese contraseña para el nuevo admin: ")
                    
                # Crear admin verificado directamente
                insert = text("""
                    INSERT INTO users (username, password_hash, role, is_verified)
                    VALUES (:email, :pwd, 'admin', TRUE)
                """)
                conn.execute(insert, {"email": email, "pwd": hash_password(pwd)})
                conn.commit()
                print(f"[+] ¡Éxito! Usuario Admin {email} creado.")

if __name__ == "__main__":
    create_or_promote_admin()
