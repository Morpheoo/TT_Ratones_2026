#!/usr/bin/env python3
"""
Quick Diagnostic - Chequeo rápido de 10 segundos del estado actual
Uso: python quick_diag.py
"""

import subprocess
import sys
import os

WINDOWS = sys.platform == "win32"
CF = 0x08000000 if WINDOWS else 0

def run(cmd):
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=CF, timeout=5)
        return True
    except:
        return False

# Iconos
OK = "✓"
ERR = "✗"

print("\n" + "="*60)
print("  QUICK DIAGNOSTIC - Estado actual del sistema")
print("="*60 + "\n")

# 1. Docker
status = OK if run(["docker", "info"]) else ERR
print(f"{status} Docker daemon: ", end="")
print("RUNNING" if status == OK else "NOT RUNNING - Abre Docker Desktop")

# 2. Containers
containers = []
try:
    output = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"],
        stderr=subprocess.STDOUT, creationflags=CF, text=True
    )
    containers = [c for c in output.strip().split('\n') if c]
except:
    pass

db_running = "tt_ratones_db" in containers
status = OK if db_running else ERR
print(f"{status} tt_ratones_db: ", end="")
print("UP" if db_running else "DOWN")

pgadmin_running = "pgadmin_ratones" in containers
status = OK if pgadmin_running else ERR
print(f"{status} pgadmin_ratones: ", end="")
print("UP" if pgadmin_running else "DOWN")

# 3. PostgreSQL
if db_running:
    pg_ready = run(["docker", "exec", "tt_ratones_db", "pg_isready", "-q"])
    status = OK if pg_ready else ERR
    print(f"{status} PostgreSQL accepting connections: ", end="")
    print("YES" if pg_ready else "NO")

# 4. Python packages
print("\nPython packages:")
pkgs = ["streamlit", "psycopg2", "sqlalchemy"]
for pkg in pkgs:
    try:
        __import__(pkg)
        print(f"  {OK} {pkg}")
    except ImportError:
        print(f"  {ERR} {pkg} (install with: pip install {pkg})")

# 5. Files
print("\nProject files:")
files = ["docker-compose.yml", ".env", "Home.py", "run_app.py", "start_services.py"]
for f in files:
    status = OK if os.path.exists(f) else ERR
    print(f"  {status} {f}")

print("\n" + "="*60)
print("  Para llevantar los servicios, ejecuta: launcher.bat")
print("="*60 + "\n")
