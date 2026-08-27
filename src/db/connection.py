"""Conexion de base de datos para los modos offline y servidor.

El instalador Windows usa SQLite y no necesita Docker ni un servicio de BD.
El entorno de desarrollo existente puede seguir usando PostgreSQL.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


_db_logger = logging.getLogger("tt_ratones.db")
if not _db_logger.handlers:
    _db_logger.setLevel(logging.WARNING)

load_dotenv(override=True)

DB_BACKEND = os.getenv("DB_BACKEND", "postgresql").strip().lower()
if DB_BACKEND in {"postgres", "postgresql", "pg"}:
    DB_BACKEND = "postgresql"
elif DB_BACKEND in {"sqlite", "offline", "local"}:
    DB_BACKEND = "sqlite"
else:
    raise ValueError(f"DB_BACKEND no soportado: {DB_BACKEND!r}")


def _bundle_root() -> Path:
    """Directorio de recursos tanto en fuente como dentro de PyInstaller."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[2]


def get_app_data_dir() -> Path:
    """Carpeta escribible y estable para datos locales del usuario."""
    configured = os.getenv("TT_APP_DATA_DIR", "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        root = base / "TT_Ratones_2026"
    root.mkdir(parents=True, exist_ok=True)
    return root


def is_sqlite_mode() -> bool:
    return DB_BACKEND == "sqlite"


def is_offline_mode() -> bool:
    return is_sqlite_mode()


if is_sqlite_mode():
    configured_db = os.getenv("SQLITE_DB_PATH", "").strip()
    sqlite_path = (
        Path(configured_db).expanduser().resolve()
        if configured_db
        else get_app_data_dir() / "data" / "tt_ratones.db"
    )
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{sqlite_path.as_posix()}"
else:
    DB_USER = os.getenv("POSTGRES_USER")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB")
    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        raise ValueError(
            "[ERROR] Faltan variables de entorno criticas de PostgreSQL "
            "(POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)."
        )
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def _enable_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


@st.cache_resource(show_spinner=False)
def _create_engine_cached():
    if is_sqlite_mode():
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        event.listen(engine, "connect", _enable_sqlite_pragmas)
    else:
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
    """Retorna el engine o None sin cachear intentos fallidos."""
    try:
        return _create_engine_cached()
    except Exception as exc:
        _db_logger.error("Error creando motor SQL: %s", exc)
        return None


def get_session_maker():
    engine = get_db_engine()
    if engine is None:
        return None
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _schema_path() -> Path:
    filename = "schema_sqlite.sql" if is_sqlite_mode() else "schema.sql"
    return _bundle_root() / filename


def init_db() -> bool:
    """Inicializa el esquema correspondiente de forma idempotente."""
    engine = get_db_engine()
    if engine is None:
        return False

    schema_path = _schema_path()
    if not schema_path.exists():
        _db_logger.warning("No se encontro %s", schema_path)
        return False

    try:
        sql_script = schema_path.read_text(encoding="utf-8")
        raw_connection = engine.raw_connection()
        try:
            raw_connection.executescript(sql_script) if is_sqlite_mode() else None
            if is_sqlite_mode():
                raw_connection.commit()
                return True
        finally:
            raw_connection.close()

        def has_executable_sql(statement: str) -> bool:
            return any(
                line.strip() and not line.strip().startswith("--")
                for line in statement.splitlines()
            )

        applied = 0
        failed = 0
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for statement in sql_script.split(";"):
                if not has_executable_sql(statement):
                    continue
                try:
                    conn.execute(text(statement))
                    applied += 1
                except Exception as exc:
                    failed += 1
                    _db_logger.warning("Statement de schema fallo: %s", exc)
        _db_logger.info("schema aplicado: %s OK, %s con error", applied, failed)
        return True
    except Exception as exc:
        _db_logger.error("Error ejecutando schema: %s", exc)
        return False


def get_db_session():
    SessionLocal = get_session_maker()
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
