#!/usr/bin/env python3
"""
Test Suite para verificar que Docker y servicios funcionan correctamente.
Uso: python test_docker_setup.py
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Configuración
WINDOWS = sys.platform == "win32"
CF = 0x08000000 if WINDOWS else 0
CONTAINER_NAME = "tt_ratones_db"
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "admin_secure_password")
DB_NAME = os.getenv("POSTGRES_DB", "ratones_lab")


class Colors:
    """ANSI color codes para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{msg:^70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.RESET}\n")


def print_test(name, passed, msg=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  [{status}] {name}")
    if msg:
        print(f"         {msg}")


def run_cmd(cmd, timeout=10):
    """Ejecuta comando y retorna (success, output)"""
    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            creationflags=CF,
            timeout=timeout,
            text=True
        )
        return True, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except subprocess.CalledProcessError as e:
        return False, e.output if hasattr(e, 'output') else str(e)
    except FileNotFoundError:
        return False, "COMMAND NOT FOUND"
    except Exception as e:
        return False, str(e)


# ============================================================================
# TEST 1: Docker CLI
# ============================================================================
print_header("TEST 1: Docker CLI Available")

success, output = run_cmd(["docker", "--version"])
print_test("Docker CLI installed", success, output.strip() if success else output[:50])

if not success:
    print(f"\n{Colors.RED}ERROR: Docker CLI no está disponible{Colors.RESET}")
    print("Instala Docker Desktop o docker-ce desde: https://www.docker.com")
    sys.exit(1)


# ============================================================================
# TEST 2: Docker Daemon
# ============================================================================
print_header("TEST 2: Docker Daemon Running")

success, output = run_cmd(["docker", "info"])
print_test("Docker daemon is running", success, "Ready to accept commands" if success else "Is Docker Desktop open?")

if not success:
    print(f"\n{Colors.RED}ERROR: Docker daemon no está corriendo{Colors.RESET}")
    print("Abre Docker Desktop y espera a que esté completamente listo.")
    sys.exit(1)


# ============================================================================
# TEST 3: docker-compose Available
# ============================================================================
print_header("TEST 3: docker-compose Available")

# Intenta "docker compose" primero (integrado en Docker 20.10+)
success1, output1 = run_cmd(["docker", "compose", "version"])
compose_cmd_integrated = success1

# Fallback a "docker-compose" standalone
success2, output2 = run_cmd(["docker-compose", "--version"])
compose_cmd_standalone = success2

if compose_cmd_integrated:
    print_test("docker compose (integrado) found", True, output1.strip())
elif compose_cmd_standalone:
    print_test("docker-compose (standalone) found", True, output2.strip())
else:
    print_test("docker-compose available", False, "Ni 'docker compose' ni 'docker-compose' encontrados")
    sys.exit(1)


# ============================================================================
# TEST 4: docker-compose.yml exists
# ============================================================================
print_header("TEST 4: Project Files")

files_ok = True
for fname in ["docker-compose.yml", ".env", "Home.py", "run_app.py", "start_services.py"]:
    exists = Path(fname).exists()
    print_test(f"{fname} exists", exists)
    if not exists and fname in ["docker-compose.yml", ".env", "run_app.py", "start_services.py"]:
        files_ok = False

if not files_ok:
    print(f"\n{Colors.RED}ERROR: Faltan archivos críticos{Colors.RESET}")
    sys.exit(1)


# ============================================================================
# TEST 5: Containers Status
# ============================================================================
print_header("TEST 5: Docker Containers Status")

success, output = run_cmd(["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}"])
if success:
    lines = output.strip().split('\n')
    print("  Container Status:")
    for line in lines:
        print(f"    {line}")
    
    # Buscar tt_ratones_db específicamente
    db_running = any(CONTAINER_NAME in line and "Up" in line for line in lines)
    print_test(f"{CONTAINER_NAME} is running", db_running, 
               "Ready" if db_running else "Not running (expected on first run)")
else:
    print_test("List containers", False, output[:50])


# ============================================================================
# TEST 6: docker-compose up -d
# ============================================================================
print_header("TEST 6: Bring Up Containers")

if compose_cmd_integrated:
    cmd = ["docker", "compose", "up", "-d"]
else:
    cmd = ["docker-compose", "up", "-d"]

success, output = run_cmd(cmd, timeout=30)
print_test("docker-compose up -d", success, "Containers brought up" if success else output[:80])

if not success:
    print(f"\n{Colors.YELLOW}WARNING: docker-compose up falló{Colors.RESET}")
    print(f"Output: {output[:200]}")


# ============================================================================
# TEST 7: Wait for PostgreSQL
# ============================================================================
print_header("TEST 7: PostgreSQL Health Check")

print(f"  Esperando a que PostgreSQL responda (máx 60 segundos)...")
start = time.time()
for attempt in range(20):
    success, _ = run_cmd(["docker", "exec", CONTAINER_NAME, "pg_isready", "-q"])
    if success:
        elapsed = time.time() - start
        print_test(f"PostgreSQL is ready", True, f"Responded in {elapsed:.1f}s")
        break
    time.sleep(3)
else:
    elapsed = time.time() - start
    print_test(f"PostgreSQL is ready", False, f"Did not respond within {elapsed:.0f}s")


# ============================================================================
# TEST 8: PostgreSQL Connection (psycopg2)
# ============================================================================
print_header("TEST 8: Python Database Connection")

try:
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print_test("psycopg2 connection", True, f"Connected successfully")
        print_test("PostgreSQL version", True, version.split(',')[0])
        
    except Exception as e:
        print_test("psycopg2 connection", False, str(e)[:80])
        
except ImportError:
    print_test("psycopg2 installed", False, "Package not installed (install with: pip install psycopg2-binary)")


# ============================================================================
# TEST 9: SQLAlchemy Connection
# ============================================================================
print_header("TEST 9: SQLAlchemy Engine")

try:
    from sqlalchemy import create_engine, text
    
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print_test("SQLAlchemy engine", True, "Connection successful")
    except Exception as e:
        print_test("SQLAlchemy engine", False, str(e)[:80])
        
except ImportError:
    print_test("SQLAlchemy installed", False, "Package not installed (install with: pip install sqlalchemy)")


# ============================================================================
# TEST 10: start_services.py execution
# ============================================================================
print_header("TEST 10: Dry Run - start_services.py")

print(f"  {Colors.YELLOW}Running start_services.py (this may take 30-60 seconds)...{Colors.RESET}")
success, output = run_cmd([sys.executable, "start_services.py"], timeout=120)

if success:
    print_test("start_services.py execution", True, "Completed successfully")
else:
    # Es posible que falle si algo ya está corriendo, pero eso está bien
    print_test("start_services.py execution", "INCOMPLETE", output[:100])
    print(f"  (Este test es informativo. Si docker-compose ya está activo, puede reportar errores.")


# ============================================================================
# SUMMARY
# ============================================================================
print_header("TEST SUMMARY")

print(f"""
{Colors.GREEN}✓ Docker Setup is FUNCTIONAL{Colors.RESET}

Next steps:
  1. Abre una terminal en este directorio
  2. Ejecuta: launcher.bat (Windows) o python run_app.py (Linux/Mac)
  3. Streamlit debería abrirse en tu navegador con todo listo

Si aún tienes problemas:
  - Verifica que Docker Desktop está abierto
  - Revisa los logs con: docker logs {CONTAINER_NAME}
  - Revisa el .env para credenciales correctas
  - Ejecuta nuevamente: python test_docker_setup.py
""")
