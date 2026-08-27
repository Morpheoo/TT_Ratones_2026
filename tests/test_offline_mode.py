"""Pruebas de regresion del instalador local sin Docker/PostgreSQL."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestOfflineMode(unittest.TestCase):
    def test_sqlite_auth_and_treatments_in_clean_process(self):
        scenario = textwrap.dedent(
            """
            import re
            import sys
            from pathlib import Path

            root = Path.cwd()
            sys.path.insert(0, str(root))
            sys.path.insert(0, str(root / "src"))

            from sqlalchemy import text
            from auth import authenticate, register_user, request_password_reset, reset_password
            from db.connection import get_db_engine, init_db, is_offline_mode
            from treatments import get_all_treatments, initialize_treatments_table

            assert is_offline_mode()
            assert init_db()
            assert initialize_treatments_table()
            assert len(get_all_treatments()) >= 5

            email = "primero@ipn.mx"
            ok, message = register_user(
                email,
                "ClaveLocal9",
                role="investigador",
                full_name="Usuario Local",
                num_empleado="12345",
                area="Laboratorio",
                centro="ESCOM",
                accepted_terms=True,
            )
            assert ok, message
            user = authenticate(email, "ClaveLocal9")
            assert user and user["status"] == "ACTIVE"
            assert user["role"] == "admin"

            ok, reset_message = request_password_reset(email)
            assert ok, reset_message
            code = re.search(r"(\\d{6})", reset_message).group(1)
            ok, reset_message = reset_password(email, code, "NuevaClave8")
            assert ok, reset_message
            assert authenticate(email, "NuevaClave8")["role"] == "admin"

            engine = get_db_engine()
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT is_verified, is_active FROM users WHERE username=:email"),
                    {"email": email},
                ).one()
                assert bool(row[0]) and bool(row[1])
            """
        )

        with tempfile.TemporaryDirectory(prefix="tt_ratones_test_") as temp_dir:
            environment = os.environ.copy()
            environment.update(
                DB_BACKEND="sqlite",
                TT_OFFLINE_INSTALL="1",
                TT_APP_DATA_DIR=temp_dir,
                PYTHONIOENCODING="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-c", scenario],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
