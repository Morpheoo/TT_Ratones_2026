
from src.db.connection import get_db_engine
from sqlalchemy import text

def check_admin_user():
    engine = get_db_engine()
    if not engine:
        print("No DB connection.")
        return

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, username, role, is_active, is_verified, password_hash FROM users WHERE username = 'admin'")).fetchone()
        
        if result:
            print(f"User found: ID={result[0]}, Username={result[1]}, Role={result[2]}, Active={result[3]}, Verified={result[4]}")
            print(f"Password Hash prefix: {result[5][:10]}...")
        else:
            print("User 'admin' NOT found in database.")

if __name__ == "__main__":
    check_admin_user()
