import os
import logging
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Logger dedicado para la capa de base de datos
_db_logger = logging.getLogger("tt_ratones.db")
if not _db_logger.handlers:
    _db_logger.setLevel(logging.WARNING)

# Cargar variables de entorno desde .env (si existe)
load_dotenv(override=True)

# Configuración de Conexión (Coincide con docker-compose.yml)
DB_USER     = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("POSTGRES_DB")

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError(
        "[ERROR] Faltan variables de entorno críticas de Base de Datos "
        "(POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)."
    )

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# ────────────────────────────────────────────────────────────────────
# @st.cache_resource: el engine se crea UNA SOLA VEZ por proceso
# Streamlit, sin importar cuántas páginas lo importen o cuántos
# reruns ocurran.  Elimina el overhead de reconexión en cada página.
# ────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _create_engine_cached():
    """
    Crea el engine UNA SOLA VEZ. Si falla, lanza excepción
    para que @st.cache_resource NO guarde el resultado fallido.
    """
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 5},
    )
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


def get_db_engine():
    """Wrapper seguro: retorna engine o None, sin cachear fallos."""
    try:
        return _create_engine_cached()
    except Exception as e:
        _db_logger.error(f"Error creando motor SQL: {e}")
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
        _db_logger.warning("No se encontró schema.sql")
        return False

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        def _has_executable_sql(statement):
            """True si el statement tiene SQL real, no solo comentarios/whitespace."""
            for raw_line in statement.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("--"):
                    continue
                return True
            return False

        with engine.connect() as conn:
            statements = sql_script.split(";")
            for statement in statements:
                if _has_executable_sql(statement):
                    conn.execute(text(statement))
            conn.commit()
        _db_logger.info("Tablas inicializadas o verificadas.")
        return True
    except Exception as e:
        _db_logger.error(f"Error ejecutando schema.sql: {e}")
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
