
from src.db.connection import get_db_engine
from sqlalchemy import text

def fix_admin_user():
    engine = get_db_engine()
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("UPDATE users SET is_verified = TRUE, role = 'admin' WHERE username = 'admin'"))
            print("Admin user manually verified and role set to admin.")

if __name__ == "__main__":
    fix_admin_user()
