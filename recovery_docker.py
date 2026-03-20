#!/usr/bin/env python3
"""
Recovery Tool - Levanta Docker manualmente si es necesario
Uso: python recovery_docker.py
"""

import subprocess
import sys
import time
import os

WINDOWS = sys.platform == "win32"
CF = 0x08000000 if WINDOWS else 0

print("\n" + "="*70)
print("  DOCKER RECOVERY TOOL")
print("="*70 + "\n")

# 1. Check Docker daemon
print("[1/4] Verificando Docker daemon...")
try:
    subprocess.check_output(
        ["docker", "info"],
        stderr=subprocess.STDOUT,
        creationflags=CF,
        timeout=5
    )
    print("  ✓ Docker daemon ya está corriendo\n")
except Exception as e:
    print(f"  ✗ Docker daemon NO está corriendo")
    print(f"  Error: {str(e)[:50]}\n")
    
    if WINDOWS:
        print("  Intentando abrir Docker Desktop...")
        try:
            subprocess.Popen("C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe")
            print("  Docker Desktop iniciado. Esperando...")
            for i in range(15):
                time.sleep(2)
                try:
                    subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, creationflags=CF, timeout=3)
                    print("  ✓ Docker daemon activo!\n")
                    break
                except:
                    print(f"  ... esperando ({i+1}/15)")
        except Exception as e2:
            print(f"  ✗ No se pudo abrir Docker Desktop: {e2}")
            sys.exit(1)
    else:
        print("  Inicia Docker manualmente con: sudo systemctl start docker")
        sys.exit(1)

# 2. Check containers
print("[2/4] Verificando contenedores...")
try:
    output = subprocess.check_output(
        ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
        stderr=subprocess.STDOUT,
        creationflags=CF,
        text=True
    )
    containers = output.strip().split('\n')
    db_status = "no existe"
    for line in containers:
        if "tt_ratones_db" in line:
            db_status = line.split('\t')[1] if '\t' in line else line
            print(f"  tt_ratones_db: {db_status}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 3. Check docker-compose
print("\n[3/4] Verificando docker-compose...")
compose_cmd = None
try:
    subprocess.check_output(["docker", "compose", "version"], stderr=subprocess.STDOUT, creationflags=CF, timeout=5)
    compose_cmd = ["docker", "compose"]
    print("  ✓ docker compose (integrado) encontrado")
except:
    try:
        subprocess.check_output(["docker-compose", "--version"], stderr=subprocess.STDOUT, creationflags=CF, timeout=5)
        compose_cmd = ["docker-compose"]
        print("  ✓ docker-compose (standalone) encontrado")
    except Exception as e:
        print(f"  ✗ docker-compose no disponible: {e}")

# 4. Bring up containers
print("\n[4/4] Levantando contenedores...")
if compose_cmd:
    try:
        subprocess.check_output(
            compose_cmd + ["up", "-d"],
            stderr=subprocess.STDOUT,
            creationflags=CF,
            timeout=60
        )
        print("  ✓ docker-compose up -d ejecutado")
        print("\n  Esperando a que PostgreSQL esté listo...")
        
        for i in range(20):
            try:
                subprocess.check_output(
                    ["docker", "exec", "tt_ratones_db", "pg_isready", "-q"],
                    stderr=subprocess.STDOUT,
                    creationflags=CF,
                    timeout=5
                )
                print("  ✓ PostgreSQL está listo!\n")
                break
            except:
                print(f"  ... ({i+1}/20)")
                time.sleep(3)
    except Exception as e:
        print(f"  ✗ Error: {e}")
else:
    print("  ✗ No se puede levantar: docker-compose no disponible")

print("="*70)
print("  RECOVERY COMPLETADO")
print("="*70)
print("\nAhora puedes:")
print("  1. Abrir Streamlit: launcher.bat")
print("  2. O verificar estado: python quick_diag.py")
print()
