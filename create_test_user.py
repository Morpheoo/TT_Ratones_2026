
from src.db.connection import get_db_engine
from sqlalchemy import text
import bcrypt

def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def create_test_user():
    engine = get_db_engine()
    if not engine:
        return

    username = "test"
    password = "test"
    role = "investigador"
    
    with engine.connect() as conn:
        with conn.begin():
            # Delete if exists
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
            
            # Create verified investigator
            pwd_hash = hash_password(password)
            insert = text("""
                INSERT INTO users (username, password_hash, role, is_active, is_verified) 
                VALUES (:u, :p, :r, TRUE, TRUE)
            """)
            conn.execute(insert, {"u": username, "p": pwd_hash, "r": role})
            print(f"[+] Created user '{username}' (pass: '{password}') with role '{role}'")

if __name__ == "__main__":
    create_test_user()
