#!/usr/bin/env python3
"""Asistente local para preparar .env en una laptop nueva.

No sube secretos a git: .env ya esta ignorado por .gitignore.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import shutil
import string
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"

PLACEHOLDERS = {
    "",
    "tu_email@ipn.mx",
    "tu_email@alumno.ipn.mx",
    "your_email@gmail.com",
    "tu_email@gmail.com",
    "your_app_password",
    "tu_app_password",
    "cambiar_despues_del_primer_login",
    "secure_password_here",
}

DEFAULTS = {
    "POSTGRES_USER": "admin",
    "POSTGRES_PASSWORD": "secure_password_here",
    "POSTGRES_DB": "ratones_lab",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "PGADMIN_DEFAULT_EMAIL": "admin@local.test",
    "PGADMIN_DEFAULT_PASSWORD": "admin_pgadmin_local",
    "GMAIL_SENDER_EMAIL": "your_email@gmail.com",
    "GMAIL_APP_PASSWORD": "your_app_password",
    "INITIAL_ADMIN_EMAIL": "tu_email@ipn.mx",
    "INITIAL_ADMIN_PASSWORD": "cambiar_despues_del_primer_login",
}


def parse_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return lines, values


def write_env(lines: list[str], updates: dict[str, str]) -> None:
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output.append(line)
            continue
        key, _, _ = stripped.partition("=")
        key = key.strip()
        if key in updates:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output.append(line)

    missing = [key for key in DEFAULTS if key not in seen and key in updates]
    if missing:
        if output and output[-1].strip():
            output.append("")
        output.append("# Valores agregados por setup_colaborador_env.py")
        for key in missing:
            output.append(f"{key}={updates[key]}")

    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")


def ensure_env_exists() -> None:
    if ENV_PATH.exists():
        return
    if ENV_EXAMPLE_PATH.exists():
        shutil.copyfile(ENV_EXAMPLE_PATH, ENV_PATH)
        print("[OK] .env creado desde .env.example")
        return
    lines = [f"{key}={value}" for key, value in DEFAULTS.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] .env creado con defaults minimos")


def random_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%+-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    label = "S/n" if default else "s/N"
    value = input(f"{prompt} [{label}]: ").strip().lower()
    if not value:
        return default
    return value in {"s", "si", "y", "yes"}


def configure_admin(values: dict[str, str], force: bool) -> dict[str, str]:
    updates: dict[str, str] = {}
    current_email = values.get("INITIAL_ADMIN_EMAIL", "")
    current_password = values.get("INITIAL_ADMIN_PASSWORD", "")
    needs_admin = force or current_email in PLACEHOLDERS or current_password in PLACEHOLDERS

    if not needs_admin:
        print("[OK] Admin inicial ya configurado.")
        return updates

    print()
    print("Admin inicial")
    print("Este usuario se crea automaticamente si la BD esta vacia.")
    while True:
        email = ask("Correo IPN del admin inicial").lower()
        if email.endswith("@ipn.mx") or email.endswith("@alumno.ipn.mx"):
            break
        print("[WARN] Usa un correo institucional @ipn.mx o @alumno.ipn.mx.")

    if ask_yes_no("Generar password temporal automaticamente", default=True):
        password = random_password()
        print()
        print("[IMPORTANTE] Password temporal generado para el admin inicial:")
        print(f"  {password}")
        print("Guardalo en el gestor del equipo y cambialo despues del primer login.")
    else:
        while True:
            password = getpass.getpass("Password temporal del admin inicial: ").strip()
            confirm = getpass.getpass("Confirmar password temporal: ").strip()
            if password and password == confirm:
                break
            print("[WARN] Los passwords no coinciden o estan vacios.")

    updates["INITIAL_ADMIN_EMAIL"] = email
    updates["INITIAL_ADMIN_PASSWORD"] = password
    return updates


def configure_smtp(values: dict[str, str], force: bool) -> dict[str, str]:
    updates: dict[str, str] = {}
    current_email = values.get("GMAIL_SENDER_EMAIL", "")
    current_password = values.get("GMAIL_APP_PASSWORD", "")
    has_smtp = current_email not in PLACEHOLDERS and current_password not in PLACEHOLDERS

    print()
    if has_smtp and not force:
        print("[OK] SMTP Gmail ya configurado.")
        return updates

    print("Correo OTP")
    print("Gmail es opcional: sin SMTP, los OTP salen en la consola de launcher.bat.")
    if not ask_yes_no("Configurar Gmail real ahora", default=False):
        updates["GMAIL_SENDER_EMAIL"] = current_email or DEFAULTS["GMAIL_SENDER_EMAIL"]
        updates["GMAIL_APP_PASSWORD"] = current_password or DEFAULTS["GMAIL_APP_PASSWORD"]
        print("[OK] Se usara modo DEV para OTP por consola.")
        return updates

    updates["GMAIL_SENDER_EMAIL"] = ask("Gmail emisor")
    updates["GMAIL_APP_PASSWORD"] = getpass.getpass(
        "Password de aplicacion Gmail (16 caracteres, sin espacios): "
    ).strip()
    return updates


def configure_pgadmin(values: dict[str, str]) -> dict[str, str]:
    updates: dict[str, str] = {}
    for key in ("PGADMIN_DEFAULT_EMAIL", "PGADMIN_DEFAULT_PASSWORD"):
        if not values.get(key):
            updates[key] = DEFAULTS[key]
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara .env para colaborador.")
    parser.add_argument("--force", action="store_true", help="Preguntar de nuevo aunque ya haya valores.")
    args = parser.parse_args()

    ensure_env_exists()
    lines, values = parse_env(ENV_PATH)

    updates: dict[str, str] = {}
    updates.update(configure_pgadmin(values))
    updates.update(configure_admin(values, args.force))
    merged = {**values, **updates}
    updates.update(configure_smtp(merged, args.force))

    if updates:
        write_env(lines, updates)
        print()
        print("[OK] .env actualizado. No se imprimieron secretos salvo password generado.")
    else:
        print()
        print("[OK] .env ya estaba listo.")

    print()
    print("Siguiente paso recomendado:")
    print("  venv_311\\Scripts\\python.exe validar_instalacion.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
