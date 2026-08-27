"""Arranque local de TT Ratones 2026."""

from __future__ import annotations

import os
import subprocess
import sys

import streamlit.web.cli as stcli


def resolve_path(path: str) -> str:
    """Resuelve recursos desde la carpeta instalada."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


def ensure_services_ready() -> bool:
    """Inicializa SQLite antes de levantar la interfaz."""
    print("\n" + "=" * 70)
    print("PRE-CHECK: Preparando los servicios locales...")
    print("=" * 70)

    try:
        result = subprocess.run(
            [sys.executable, resolve_path("start_services.py")],
            capture_output=False,
            timeout=120,
        )
        if result.returncode != 0:
            print("\n[ERROR] No se pudo preparar la base de datos local.\n")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("\n[ERROR] La preparacion local excedio el tiempo limite.\n")
        return False
    except Exception as exc:
        print(f"\n[ERROR] No se pudo iniciar la aplicacion: {exc}\n")
        return False


if __name__ == "__main__":
    if not ensure_services_ready():
        raise SystemExit(1)

    print("\n" + "=" * 70)
    print("Iniciando TT Ratones 2026...")
    print("=" * 70 + "\n")
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("Home.py"),
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(stcli.main())
