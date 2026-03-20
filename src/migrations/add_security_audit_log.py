"""
Migración: add_security_audit_log
TT Ratones 2026 | ESCOM - IPN

Crea la tabla `security_audit_log` para almacenar eventos de seguridad
(logins, OTPs, registros, errores de BD) con fines de auditoría institucional.

Ejecución:
    python src/migrations/add_security_audit_log.py
"""

import sys
import os

# Asegurar que la raíz del proyecto esté en el path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text
from src.db.connection import get_db_engine


MIGRATION_SQL = """
-- Tabla de Auditoría de Seguridad
CREATE TABLE IF NOT EXISTS security_audit_log (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    event_type  VARCHAR(50)  NOT NULL,
    username    VARCHAR(100),
    ip_address  VARCHAR(45),
    success     BOOLEAN DEFAULT TRUE,
    message     TEXT,
    level       VARCHAR(10)  DEFAULT 'INFO'
);

-- Índices para consultas eficientes de auditoría
CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON security_audit_log (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_username
    ON security_audit_log (username);

CREATE INDEX IF NOT EXISTS idx_audit_event
    ON security_audit_log (event_type);
"""


def run_migration():
    print("[*] Ejecutando migración: add_security_audit_log...")
    engine = get_db_engine()
    if not engine:
        print("[-] Error: No se pudo obtener conexión a la BD.")
        sys.exit(1)

    try:
        with engine.begin() as conn:
            # Ejecutar cada sentencia por separado para mayor compatibilidad
            for statement in MIGRATION_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))

        print("[+] Migración completada exitosamente.")
        print("    → Tabla 'security_audit_log' creada (o ya existía).")
        print("    → Índices de auditoría creados (o ya existían).")

    except Exception as e:
        print(f"[-] Error durante la migración: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
