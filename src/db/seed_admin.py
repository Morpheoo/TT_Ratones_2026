"""Seed del admin inicial al primer arranque.

Resuelve el catch-22 del flujo de auth: el sistema requiere que un admin
exista para entrar, pero el registro requiere SMTP funcional. Al primer
boot, si la tabla `users` no tiene ningun admin Y el .env tiene
INITIAL_ADMIN_EMAIL/INITIAL_ADMIN_PASSWORD, creamos un admin ya
verificado. El usuario hace login directo sin OTP.

Idempotente: si ya hay al menos un admin, no toca nada.
"""
from __future__ import annotations

import os
from typing import Tuple

from sqlalchemy import text


PLACEHOLDERS = {
    "tu_email@ipn.mx",
    "tu_email@alumno.ipn.mx",
    "your_email@gmail.com",
    "cambiar_despues_del_primer_login",
    "your_app_password",
    "tu_app_password",
}


def seed_initial_admin() -> Tuple[bool, str]:
    """Crea un admin inicial si:
      - la tabla `users` no tiene admins, y
      - INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD estan seteados en .env
        con valores no-placeholder.

    Devuelve (ok, mensaje). ok=True solo si efectivamente se creo el admin
    o si ya existia uno (no es bloqueador). ok=False si la BD fallo.
    """
    admin_email = (os.environ.get("INITIAL_ADMIN_EMAIL", "") or "").strip().lower()
    admin_password = (os.environ.get("INITIAL_ADMIN_PASSWORD", "") or "").strip()

    if not admin_email or not admin_password:
        return True, "INITIAL_ADMIN_EMAIL/PASSWORD no configurados; saltado."
    if admin_email in PLACEHOLDERS or admin_password in PLACEHOLDERS:
        return True, "INITIAL_ADMIN_* tiene placeholders del .env.example; saltado."

    try:
        from db.connection import get_db_engine
    except ImportError:
        from src.db.connection import get_db_engine

    engine = get_db_engine()
    if engine is None:
        return False, "No se pudo conectar a la BD para sembrar el admin."

    try:
        import bcrypt
    except ImportError:
        return False, "bcrypt no esta instalado en el venv actual."

    try:
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            ).scalar() or 0
            if existing > 0:
                return True, f"Ya existen {existing} admin(s); seed saltado."

            password_hash = bcrypt.hashpw(
                admin_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            display_name = admin_email.split("@", 1)[0]

            conn.execute(
                text(
                    """
                    INSERT INTO users (
                        username, password_hash, role, is_verified,
                        full_name, accepted_terms
                    )
                    VALUES (
                        :email, :pwd, 'admin', TRUE,
                        :name, TRUE
                    )
                    ON CONFLICT (username) DO NOTHING
                    """
                ),
                {"email": admin_email, "pwd": password_hash, "name": display_name},
            )
            conn.commit()
            return True, f"Admin inicial creado: {admin_email}"
    except Exception as exc:
        return False, f"Error sembrando admin inicial: {exc}"


if __name__ == "__main__":
    ok, msg = seed_initial_admin()
    prefix = "[OK]" if ok else "[ERROR]"
    print(f"{prefix} {msg}")
    raise SystemExit(0 if ok else 1)
