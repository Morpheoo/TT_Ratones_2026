import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Configuración de Conexión (Coincide con docker-compose.yml)
# En Docker, el host es el nombre del servicio 'db'. 
# Desde fuera (Streamlit local), usamos 'localhost' si mapeamos puertos, 
# pero Docker networking es preferible si la app también corre en Docker.
# Asumiremos localhost para desarrollo híbrido.

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB")

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("❌ Faltan variables de entorno críticas de Base de Datos (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB).")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_engine = None
SessionLocal = None

def get_db_engine():
    global _engine, SessionLocal
    if _engine is None:
        try:
            print(f"[*] Conectando a Base de Datos: {DB_HOST}:{DB_PORT}/{DB_NAME}...")
            _engine = create_engine(DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
            print("[+] Motor SQL creado satisfactoriamente.")
        except Exception as e:
            print(f"[-] Error creando motor SQL: {e}")
            return None
    return _engine

def init_db():
    """Ejecuta el script schema.sql para inicializar tablas."""
    engine = get_db_engine()
    if not engine:
        return False
    
    schema_path = os.path.join(os.getcwd(), "schema.sql")
    if os.path.exists(schema_path):
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            
            with engine.connect() as conn:
                # SQLAlchemy no ejecuta múltiples sentencias por defecto fácilmente con text(),
                # pero para setup simple partimos por ';'.
                statements = sql_script.split(';')
                for statement in statements:
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()
            print("[+] Tablas inicializadas o verificadas.")
            return True
        except Exception as e:
            print(f"[-] Error ejecutando schema.sql: {e}")
            return False
    else:
        print("[!] No se encontró schema.sql")
        return False

def get_db_session():
    """Generator para dependencia de sesión (si se usara FastAPI) o uso directo."""
    if SessionLocal is None:
        get_db_engine()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
