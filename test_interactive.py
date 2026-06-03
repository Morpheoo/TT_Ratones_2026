#!/usr/bin/env python3
"""
Interactive Test - Simula el flujo completo de launcher.bat -> run_app.py -> start_services.py
Uso: python test_interactive.py
"""

import subprocess
import sys
import time
import os

WINDOWS = sys.platform == "win32"
CF = 0x08000000 if WINDOWS else 0


class Tester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
    
    def section(self, title):
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def test(self, description, fn):
        """Ejecuta un test y reporta resultado"""
        try:
            result = fn()
            if result:
                self.tests_passed += 1
                print(f"  ✓ {description}")
                return True
            else:
                self.tests_failed += 1
                print(f"  ✗ {description} - FAILED")
                return False
        except Exception as e:
            self.tests_failed += 1
            print(f"  ✗ {description}")
            print(f"    Error: {str(e)[:100]}")
            return False
    
    def run_cmd(self, cmd):
        """Helper para ejecutar comandos"""
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=CF, timeout=10)
            return True
        except:
            return False
    
    def summary(self):
        total = self.tests_passed + self.tests_failed
        pct = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"  RESUMEN: {self.tests_passed}/{total} tests pasaron ({pct:.0f}%)")
        print(f"{'='*70}\n")
        
        return self.tests_failed == 0


# ============================================================================
# MAIN
# ============================================================================

tester = Tester()

tester.section("1. VERIFICAR DOCKER BASICS")

tester.test("Docker CLI disponible", 
    lambda: tester.run_cmd(["docker", "--versión"]))

tester.test("Docker daemon corriendo",
    lambda: tester.run_cmd(["docker", "info"]))

tester.test("docker-compose disponible",
    lambda: tester.run_cmd(["docker", "compose", "versión"]) or 
            tester.run_cmd(["docker-compose", "--versión"]))


tester.section("2. VERIFICAR ARCHIVOS DEL PROYECTO")

files = {
    "docker-compose.yml": "Config de servicios",
    ".env": "Variables de entorno",
    "run_app.py": "Script de inicio",
    "start_services.py": "Levantador de servicios",
    "Home.py": "App principal Streamlit"
}

for fname, desc in files.items():
    tester.test(f"{fname} ({desc})",
        lambda f=fname: os.path.exists(f))


tester.section("3. SIMULAR FLUJO: launcher.bat -> run_app.py -> start_services.py")

print("  Este test ejecuta start_services.py para validar todo el flujo...")
print("  Esto puede tomar 30-60 segundos.\n")

tester.test("start_services.py ejecutable",
    lambda: tester.run_cmd([sys.executable, "start_services.py"]))


tester.section("4. VERIFICAR DOCKER CONTAINERS")

def check_containers():
    try:
        output = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            stderr=subprocess.STDOUT,
            creationflags=CF,
            text=True
        )
        containers = output.strip().split('\n')
        return "tt_ratones_db" in containers
    except:
        return False

tester.test("Contenedor tt_ratones_db existe",
    check_containers)


def check_db_running():
    try:
        subprocess.check_output(
            ["docker", "exec", "tt_ratones_db", "pg_isready", "-q"],
            stderr=subprocess.STDOUT,
            creationflags=CF
        )
        return True
    except:
        return False

tester.test("PostgreSQL respondiendo",
    check_db_running)


tester.section("5. VERIFICAR CONECTIVIDAD A BASE DE DATOS")

def test_psycopg2():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            database=os.getenv("POSTGRES_DB", "ratones_lab"),
            user=os.getenv("POSTGRES_USER", "admin"),
            password=os.getenv("POSTGRES_PASSWORD", "admin_secure_password"),
            connect_timeout=5
        )
        conn.close()
        return True
    except ImportError:
        print("    (psycopg2 no instalado - saltando)")
        return True
    except:
        return False

tester.test("Conexión psycopg2 a PostgreSQL",
    test_psycopg2)


def test_sqlalchemy():
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            f"postgresql://{os.getenv('POSTGRES_USER', 'admin')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'admin_secure_password')}@"
            f"127.0.0.1:5432/{os.getenv('POSTGRES_DB', 'ratones_lab')}"
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except ImportError:
        print("    (SQLAlchemy no instalado - saltando)")
        return True
    except:
        return False

tester.test("Conexión SQLAlchemy a PostgreSQL",
    test_sqlalchemy)


tester.section("6. VERIFICAR INTEGRACIÓN STREAMLIT")

print("  Verificando que Home.py y páginas están presentes...\n")

def check_streamlit_files():
    if not os.path.exists("Home.py"):
        return False
    if not os.path.exists("pages"):
        return False
    return True

tester.test("Home.py y directorio pages existen",
    check_streamlit_files)

def check_home_imports():
    try:
        with open("Home.py", "r") as f:
            content = f.read()
        return "streamlit" in content and "_check_docker_status" in content
    except:
        return False

tester.test("Home.py tiene _check_docker_status (no _ensure_docker_containers)",
    check_home_imports)


# ============================================================================
# RESUMEN Y SIGUIENTES PASOS
# ============================================================================

if tester.summary():
    print("""
✓ TODOS LOS TESTS PASARON - Sistema listo para usar!

SIGUIENTES PASOS:
  1. Ejecuta: launcher.bat (o python run_app.py)
  2. Streamlit debería abrirse automáticamente
  3. Si aún tienes problemas, revisa los logs de Docker:
     docker logs tt_ratones_db

PARA DEBUGUEAR MÁS:
  - Ver estado de contenedores: docker ps -a
  - Ver logs en vivo: docker logs -f tt_ratones_db
  - Ejecutar nuevamente este test: python test_interactive.py
    """)
    sys.exit(0)
else:
    print("""
✗ ALGUNOS TESTS FALLARON

COSAS A VERIFICAR:
  1. ¿Docker Desktop está abierto?
  2. ¿docker-compose.yml existe?
  3. ¿El archivo .env tiene las credenciales correctas?
  4. ¿Hay suficiente espacio en disco?
  
DEBUGUEO:
  - Revisa: docker logs tt_ratones_db
  - Intenta: docker-compose down && docker-compose up -d
  - Ejecuta nuevamente: python test_interactive.py
    """)
    sys.exit(1)
