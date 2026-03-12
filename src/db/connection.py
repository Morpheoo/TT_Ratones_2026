import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Configuración de Conexión (Coincide con docker-compose.yml)
DB_USER     = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("POSTGRES_DB")

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError(
        "❌ Faltan variables de entorno críticas de Base de Datos "
        "(POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)."
    )

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# ────────────────────────────────────────────────────────────────────
# @st.cache_resource: el engine se crea UNA SOLA VEZ por proceso
# Streamlit, sin importar cuántas páginas lo importen o cuántos
# reruns ocurran.  Elimina el overhead de reconexión en cada página.
# ────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_db_engine():
    """
    Retorna el engine SQLAlchemy cacheado a nivel de proceso.
    Solo se crea la primera vez; los siguientes llamados devuelven
    la misma instancia sin tocar la red ni el pool de conexiones.
    """
    try:
        print(f"[*] Conectando a Base de Datos: {DB_HOST}:{DB_PORT}/{DB_NAME}...")
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,          # Verifica la conexión antes de usarla
            pool_size=5,                  # Máximo 5 conexiones simultáneas
            max_overflow=10,
            connect_args={"connect_timeout": 5},
        )
        # Verificar que la conexión funciona realmente
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[+] Motor SQL creado satisfactoriamente.")
        return engine
    except Exception as e:
        print(f"[-] Error creando motor SQL: {e}")
        return None


def get_session_maker():
    """Retorna un SessionLocal ligado al engine cacheado."""
    engine = get_db_engine()
    if engine is None:
        return None
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Ejecuta el script schema.sql para inicializar tablas."""
    engine = get_db_engine()
    if not engine:
        return False

    schema_path = os.path.join(os.getcwd(), "schema.sql")
    if not os.path.exists(schema_path):
        print("[!] No se encontró schema.sql")
        return False

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        with engine.connect() as conn:
            statements = sql_script.split(";")
            for statement in statements:
                if statement.strip():
                    conn.execute(text(statement))
            conn.commit()
        print("[+] Tablas inicializadas o verificadas.")
        return True
    except Exception as e:
        print(f"[-] Error ejecutando schema.sql: {e}")
        return False


def get_db_session():
    """Generator para uso directo del ORM."""
    SessionLocal = get_session_maker()
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
