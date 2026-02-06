
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

    password = "admin"
    username = "admin"
    role = "admin"
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Delete existing
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
            print(f"[-] Deleted old '{username}' user if existed.")
            
            # 2. Create fresh
            pwd_hash = hash_password(password)
            insert = text("""
                INSERT INTO users (username, password_hash, role, is_active, is_verified) 
                VALUES (:u, :p, :r, TRUE, TRUE)
            """)
            conn.execute(insert, {"u": username, "p": pwd_hash, "r": role})
            print(f"[+] Created new '{username}' user with password '{password}'")
            print("[+] Flags set: is_active=TRUE, is_verified=TRUE, role='admin'")

if __name__ == "__main__":
    reset_admin()
