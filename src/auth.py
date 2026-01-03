import json
import os
import hashlib

# Path to the users database
USERS_DB = os.path.join("data", "users.json")

def hash_password(password: str) -> str:
    """Simple SHA-256 hashing for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_db_exists():
    """Ensure the data directory and users.json exist."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USERS_DB):
        # Default users
        default_users = {
            "investigador@escom.ipn.mx": {
                "password": hash_password("tt2026"),
                "role": "Investigador",
                "name": "Investigador Principal"
            },
            "admin": {
                "password": hash_password("admin"),
                "role": "Administrador",
                "name": "Administrador del Sistema"
            }
        }
        with open(USERS_DB, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4)

def authenticate(email, password):
    """Authenticate a user against the JSON database."""
    ensure_db_exists()
    try:
        with open(USERS_DB, "r", encoding="utf-8") as f:
            users = json.load(f)
        
        user_info = users.get(email)
        if user_info and user_info["password"] == hash_password(password):
            return user_info
    except Exception as e:
        print(f"Error during authentication: {e}")
    return None

def register_user(email, password, role, name):
    """Register a new user in the system."""
    ensure_db_exists()
    try:
        with open(USERS_DB, "r", encoding="utf-8") as f:
            users = json.load(f)
        
        if email in users:
            return False, "El usuario ya existe."
        
        users[email] = {
            "password": hash_password(password),
            "role": role,
            "name": name
        }
        
        with open(USERS_DB, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        return True, "Usuario registrado exitosamente."
    except Exception as e:
        return False, f"Error al registrar usuario: {e}"
