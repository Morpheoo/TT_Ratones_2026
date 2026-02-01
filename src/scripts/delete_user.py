from sqlalchemy import text
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_engine

def delete_user(email):
    print(f"[*] Intentando eliminar usuario: {email}")
    engine = get_db_engine()
    if not engine:
        print("[-] No hay conexión a BD.")
        return

    with engine.connect() as conn:
        try:
            # Verificar si existe primero
            check = text("SELECT id FROM users WHERE username = :email")
            res = conn.execute(check, {"email": email}).fetchone()
            
            if res:
                delete_q = text("DELETE FROM users WHERE username = :email")
                conn.execute(delete_q, {"email": email})
                conn.commit()
                print(f"[+] Usuario {email} eliminado exitosamente.")
            else:
                print(f"[*] El usuario {email} no existe en la BD.")

        except Exception as e:
            print(f"[-] Error eliminando usuario: {e}")

if __name__ == "__main__":
    email_to_delete = "hportocarreror1700@alumno.ipn.mx"
    delete_user(email_to_delete)
