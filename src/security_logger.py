"""
security_logger.py — Módulo Centralizado de Logging de Seguridad
TT Ratones 2026 | ESCOM - IPN

Implementa logging dual:
  1. Archivo rotativo: logs/security.log (5 MB, 3 backups)
  2. Tabla PostgreSQL: security_audit_log (para trazabilidad institucional)

Uso:
    from src.security_logger import log_security_event

    log_security_event("LOGIN_SUCCESS", user="admin@ipn.mx", message="Login exitoso")
    log_security_event("LOGIN_FAILED",  user="x@ipn.mx",    message="Credenciales incorrectas", level="WARNING")
"""

import logging
import logging.handlers
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  1. Configuración del logger de archivo
# ─────────────────────────────────────────────

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "security.log")

_log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
_date_format = "%Y-%m-%d %H:%M:%S"

_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_handler.setFormatter(logging.Formatter(_log_format, datefmt=_date_format))

# Logger independiente para no interferir con el root logger de Streamlit
security_logger = logging.getLogger("tt_ratones.security")
security_logger.setLevel(logging.DEBUG)
security_logger.propagate = False  # No escalar al root logger

if not security_logger.handlers:
    security_logger.addHandler(_handler)

# ─────────────────────────────────────────────
#  2. Función principal de logging
# ─────────────────────────────────────────────

_LEVEL_MAP = {
    "DEBUG":    logging.DEBUG,
    "INFO":     logging.INFO,
    "WARNING":  logging.WARNING,
    "ERROR":    logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def log_security_event(
    event: str,
    user: str = "ANONIMO",
    message: str = "",
    level: str = "INFO",
    ip: str = "N/A",
    success: bool = True,
) -> None:
    """
    Registra un evento de seguridad en archivo y (opcionalmente) en BD.

    Args:
        event:   Código del evento (ej. "LOGIN_SUCCESS", "OTP_FAILED").
        user:    Identificador del usuario involucrado (email).
        message: Descripción libre del evento.
        level:   Nivel de severidad: DEBUG, INFO, WARNING, ERROR, CRITICAL.
        ip:      Dirección IP del cliente (si está disponible).
        success: Si la operación fue exitosa (para la columna `success` en BD).
    """
    numeric_level = _LEVEL_MAP.get(level.upper(), logging.INFO)
    log_message = f"[{event}] usuario={user} ip={ip} | {message}"
    security_logger.log(numeric_level, log_message)

    # Intentar persistir en BD de forma no bloqueante
    _log_to_db(event=event, user=user, message=message, ip=ip,
                success=success, level=level.upper())


# ─────────────────────────────────────────────
#  3. Persistencia en PostgreSQL (fallback silencioso)
# ─────────────────────────────────────────────

def _log_to_db(
    event: str,
    user: str,
    message: str,
    ip: str = "N/A",
    success: bool = True,
    level: str = "INFO",
) -> None:
    """
    Inserta el evento en la tabla `security_audit_log`.
    Si la BD no está disponible, registra el fallo en el archivo de log
    y continúa sin interrumpir el flujo de la aplicación.
    """
    try:
        # Import diferido para evitar circular imports y errores de inicio
        from db.connection import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()
        if not engine:
            return  # BD no disponible, fallback silencioso

        insert_sql = text("""
            INSERT INTO security_audit_log
                (event_type, username, ip_address, success, message, level)
            VALUES
                (:event, :user, :ip, :success, :message, :level)
        """)

        with engine.begin() as conn:
            # Aseguramos que los campos tengan longitud válida para la BD
            safe_user = (str(user)[:100]) if user else "ANONIMO"
            safe_ip = (str(ip)[:45]) if ip else "N/A"
            safe_msg = (str(message)[:1000]) if message else ""
            safe_lvl = (str(level)[:10]) if level else "INFO"

            conn.execute(insert_sql, {
                "event":   event,
                "user":    safe_user,
                "ip":      safe_ip,
                "success": success,
                "message": safe_msg,
                "level":   safe_lvl,
            })

    except Exception as exc:
        # Fallo silencioso: sólo lo registra en archivo, NO propaga la excepción
        security_logger.warning(
            f"[DB_LOG_FAILED] No se pudo persistir evento '{event}' en BD: {exc}"
        )
