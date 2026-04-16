#!/usr/bin/env python3
"""
Start services script - Levanta Docker y verifica que la BD esté lista ANTES de Streamlit.
Uso: python start_services.py
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Configuración
MAX_RETRIES = 5
WAIT_BETWEEN_RETRIES = 2
PG_STARTUP_TIMEOUT = 60  # segundos
WINDOWS = sys.platform == "win32"
CF = 0x08000000 if WINDOWS else 0  # CREATE_NO_WINDOW en Windows


class ServiceStartError(Exception):
    """Error al iniciar servicios"""
    pass


def log(msg: str, level: str = "INFO"):
    """Simple logging"""
    prefix = {
        "INFO": "ℹ️ ",
        "OK": "✅ ",
        "WARN": "⚠️ ",
        "ERROR": "❌ ",
    }.get(level, "➜ ")
    print(f"{prefix} [{level}] {msg}")


def run_cmd(cmd: list, description: str = "", cwd=None) -> bool:
    """Ejecuta comando y retorna True si tuvo éxito"""
    try:
        subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            creationflags=CF,
            timeout=30
        )
        return True
    except subprocess.TimeoutExpired:
        log(f"{description} - TIMEOUT", "ERROR")
        return False
    except subprocess.CalledProcessError as e:
        log(f"{description} - {e.output.decode()[:100]}", "WARN")
        return False
    except FileNotFoundError:
        log(f"{description} - Comando no encontrado en PATH", "ERROR")
        return False
    except Exception as e:
        log(f"{description} - {str(e)[:100]}", "ERROR")
        return False


def check_env_file() -> bool:
    """Verifica y autogenera .env si no existe"""
    log("Verificando archivo .env...", "INFO")
    env_path = os.path.join(os.getcwd(), ".env")
    example_path = os.path.join(os.getcwd(), ".env.example")
    
    if os.path.exists(env_path):
        log("Archivo .env encontrado y listo", "OK")
        return True
        
    log("No se encontró .env. Intentando autogenerar...", "WARN")
    if os.path.exists(example_path):
        try:
            import shutil
            shutil.copy(example_path, env_path)
            log("Archivo .env autogenerado exitosamente desde .env.example", "OK")
            return True
        except Exception as e:
            log(f"Fallo al copiar .env.example: {e}", "ERROR")
            return False
            
    # Fallback si no hay .env.example
    try:
        with open(env_path, "w") as f:
            f.write("POSTGRES_USER=admin\n")
            f.write("POSTGRES_PASSWORD=admin_secure_password\n")
            f.write("POSTGRES_DB=ratones_lab\n")
            f.write("DB_HOST=127.0.0.1\n")
            f.write("DB_PORT=5432\n")
        log("Archivo .env autogenerado con valores por defecto de la BD", "OK")
        return True
    except Exception as e:
        log(f"No se pudo crear archivo .env por defecto: {e}", "ERROR")
        return False


def check_docker_installed() -> bool:
    """Verifica que Docker esté disponible en PATH"""
    log("Verificando Docker CLI...", "INFO")
    if run_cmd(["docker", "--version"], "docker --version"):
        log("Docker CLI encontrado", "OK")
        return True
    log("Docker CLI NO encontrado. Instala Docker Desktop o docker-ce", "ERROR")
    return False


def check_docker_daemon() -> bool:
    """Verifica que Docker daemon esté corriendo"""
    log("Verificando Docker daemon...", "INFO")
    for attempt in range(MAX_RETRIES):
        if run_cmd(["docker", "info"], "docker info"):
            log("Docker daemon activo", "OK")
            return True
        if attempt < MAX_RETRIES - 1:
            log(f"Docker daemon no disponible. Reintentando ({attempt+1}/{MAX_RETRIES})...", "WARN")
            time.sleep(WAIT_BETWEEN_RETRIES)
    log("Docker daemon NO disponible. Abre Docker Desktop o inicia el daemon", "ERROR")
    return False


def check_docker_compose() -> bool:
    """Verifica que docker-compose esté disponible"""
    log("Verificando docker-compose...", "INFO")
    # Intenta primero "docker compose" (versión integrada en Docker 20.10+)
    if run_cmd(["docker", "compose", "version"], "docker compose version"):
        log("docker compose (integrado) encontrado", "OK")
        return True
    # Fallback a "docker-compose" (versión standalone)
    if run_cmd(["docker-compose", "--version"], "docker-compose --version"):
        log("docker-compose (standalone) encontrado", "OK")
        return True
    log("docker-compose NO encontrado. Instala Docker Compose", "ERROR")
    return False


def start_containers() -> bool:
    """Levanta los contenedores con docker-compose up -d"""
    log("Levantando contenedores...", "INFO")
    
    # Detecta si usar "docker compose" o "docker-compose"
    compose_cmd = None
    if run_cmd(["docker", "compose", "version"], ""):
        compose_cmd = ["docker", "compose"]
    elif run_cmd(["docker-compose", "--version"], ""):
        compose_cmd = ["docker-compose"]
    else:
        log("No se encontró docker-compose", "ERROR")
        return False
    
    cmd = compose_cmd + ["up", "-d"]
    if run_cmd(cmd, f"Ejecutando: {' '.join(cmd)}", cwd=os.getcwd()):
        log("Contenedores levantados", "OK")
        return True
    log("Fallo al levantar contenedores", "ERROR")
    return False


def wait_for_postgres() -> bool:
    """Espera a que PostgreSQL esté listo para conexiones"""
    log("Esperando a que PostgreSQL esté listo...", "INFO")
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < PG_STARTUP_TIMEOUT:
        attempt += 1
        if run_cmd(
            ["docker", "exec", "tt_ratones_db", "pg_isready", "-q"],
            ""
        ):
            elapsed = time.time() - start_time
            log(f"PostgreSQL listo en {elapsed:.1f}s", "OK")
            return True
        
        log(f"PostgreSQL no está listo... reintentando ({attempt})...", "WARN")
        time.sleep(3)
    
    log(f"PostgreSQL NO estuvo listo en {PG_STARTUP_TIMEOUT}s", "ERROR")
    return False


def verify_db_connection() -> bool:
    """Verifica que pueda conectar a la BD desde Python"""
    log("Verificando conexión a la BD desde Python...", "INFO")
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "ratones_lab"),
            user=os.getenv("POSTGRES_USER", "admin"),
            password=os.getenv("POSTGRES_PASSWORD", "admin_secure_password"),
            connect_timeout=5
        )
        conn.close()
        log("Conexión a BD exitosa", "OK")
        return True
    except ImportError:
        log("psycopg2 no está instalado - saltando verificación Python", "WARN")
        return True  # No es crítico
    except Exception as e:
        log(f"No se pudo conectar a BD: {str(e)[:80]}", "ERROR")
        return False


def main():
    """Orquesta el inicio de servicios"""
    print("\n" + "="*60)
    print("🚀 INICIANDO SERVICIOS...")
    print("="*60 + "\n")
    
    try:
        # 0. Verificar y autogenerar .env si es necesario
        if not check_env_file():
            raise ServiceStartError("No se pudo configurar el archivo de entorno (.env)")
            
        # 1. Verificar que Docker está disponible
        if not check_docker_installed():
            raise ServiceStartError("Docker no está instalado")
        
        # 2. Verificar que Docker daemon corre
        if not check_docker_daemon():
            raise ServiceStartError("Docker daemon no está activo")
        
        # 3. Verificar que docker-compose existe
        if not check_docker_compose():
            raise ServiceStartError("docker-compose no está disponible")
        
        # 4. Levantar contenedores
        if not start_containers():
            raise ServiceStartError("Fallo al levantar contenedores")
        
        # 5. Esperar a que PostgreSQL esté listo
        if not wait_for_postgres():
            raise ServiceStartError("PostgreSQL no respondió a tiempo")
        
        # 6. Verificar conexión desde Python
        if not verify_db_connection():
            raise ServiceStartError("No se pudo conectar a la BD")
        
        print("\n" + "="*60)
        log("✨ TODOS LOS SERVICIOS ESTÁN LISTOS ✨", "OK")
        print("="*60 + "\n")
        return 0
    
    except ServiceStartError as e:
        print("\n" + "="*60)
        log(f"FALLO: {str(e)}", "ERROR")
        print("="*60 + "\n")
        log("Sugerencias:", "WARN")
        log("1. Verifica que Docker Desktop está abierto y corriendo", "WARN")
        log("2. Verifica que docker-compose.yml existe en el directorio", "WARN")
        log("3. Revisa el archivo .env para las credenciales", "WARN")
        log("4. Si todo falla, inicia manualmente: docker-compose up -d", "WARN")
        print()
        return 1
    
    except Exception as e:
        print("\n" + "="*60)
        log(f"ERROR INESPERADO: {str(e)}", "ERROR")
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
