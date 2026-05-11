"""
validar_instalacion.py
Verifica que la instalacion del proyecto TT_Ratones_2026 este completa.
Se ejecuta desde install.bat al final, o manualmente con:
    venv_311\Scripts\python.exe validar_instalacion.py

Salida:
    exit code 0 si todo OK
    exit code 1 si hay fallas criticas (modelos faltantes, imports rotos)
    exit code 0 con [WARN] si hay solo problemas opcionales (Docker, B-SOiD)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Codigos de retorno
EXIT_OK = 0
EXIT_FAIL = 1

# Acumuladores
fallas: list[str] = []
warnings: list[str] = []

ENV_PLACEHOLDERS = {
    "",
    "tu_email@ipn.mx",
    "tu_email@alumno.ipn.mx",
    "your_email@gmail.com",
    "your_app_password",
    "tu_app_password",
    "cambiar_despues_del_primer_login",
    "secure_password_here",
}


def header(msg: str) -> None:
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    fallas.append(msg)


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")
    warnings.append(msg)


# ============================================================
# 1. Python y venvs
# ============================================================
def check_python() -> None:
    header("1. Python y entornos virtuales")
    print(f"  Python actual: {sys.version.split()[0]} ({sys.executable})")

    venv_310 = ROOT / "venv_310" / "Scripts" / "python.exe"
    venv_311 = ROOT / "venv_311" / "Scripts" / "python.exe"

    if venv_310.exists():
        try:
            ver = subprocess.check_output(
                [str(venv_310), "--version"], text=True, stderr=subprocess.STDOUT
            ).strip()
            ok(f"venv_310 -> {ver}")
        except Exception as exc:
            fail(f"venv_310 existe pero no responde: {exc}")
    else:
        fail("venv_310 no existe (correr install.bat)")

    if venv_311.exists():
        try:
            ver = subprocess.check_output(
                [str(venv_311), "--version"], text=True, stderr=subprocess.STDOUT
            ).strip()
            ok(f"venv_311 -> {ver}")
        except Exception as exc:
            fail(f"venv_311 existe pero no responde: {exc}")
    else:
        fail("venv_311 no existe (correr install.bat)")


# ============================================================
# 2. Modelos pesados (rutas exactas y tamanos esperados)
# ============================================================
MODELOS_REQUERIDOS = [
    # (path relativo, tamano esperado en bytes, opcional?)
    ("yolo_tracker.pt", 5_471_706, False),
    ("runs/pose/yolo11s_pose_raton_v4/weights/best.pt", 19_950_472, False),
    ("data/models/lstm_grooming_yolo/grooming_lstm.keras", 2_600_296, False),
    ("data/models/lstm_grooming_yolo/scaler.pkl", 15_788, False),
    ("data/models/lstm_grooming_yolo/metadata.json", 11_506, False),
    (
        "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav",
        281_877_693,
        False,
    ),
    (
        "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav",
        299_868_733,
        False,
    ),
    (
        "data/bsoid_models/bsoid_artifacts_all26_fine.pkl",
        2_723_200_287,
        True,  # opcional: solo si se usa --grooming-source ensemble_conditional
    ),
]


def check_modelos() -> None:
    header("2. Modelos pesados (verifica tamano byte-a-byte)")
    for rel, esperado, opcional in MODELOS_REQUERIDOS:
        path = ROOT / rel
        if not path.exists():
            if opcional:
                warn(f"{rel} no existe (OPCIONAL, solo si usas ensemble_conditional)")
            else:
                fail(f"{rel} no existe (copialo del USB)")
            continue
        actual = path.stat().st_size
        if actual != esperado:
            msg = f"{rel}: tamano {actual:,} != esperado {esperado:,} (transferencia incompleta?)"
            if opcional:
                warn(msg)
            else:
                fail(msg)
        else:
            ok(f"{rel} ({actual:,} B)")


# ============================================================
# 3. Imports criticos en cada venv
# ============================================================
PAQUETES_VENV310 = [
    ("simba", "SimBA"),
    ("tensorflow", "TensorFlow 2"),
    ("keras", "Keras 2"),
    ("sklearn", "scikit-learn"),
    ("torch", "PyTorch CPU"),
]

PAQUETES_VENV311 = [
    ("streamlit", "Streamlit"),
    ("ultralytics", "Ultralytics YOLO"),
    ("torch", "PyTorch CUDA o CPU"),
    ("cv2", "OpenCV"),
    ("pandas", "Pandas"),
    ("sklearn", "scikit-learn"),
    ("sqlalchemy", "SQLAlchemy"),
    ("psycopg2", "psycopg2 (Postgres)"),
]


def check_imports_en_venv(venv_python: Path, paquetes: list[tuple[str, str]], label: str) -> None:
    if not venv_python.exists():
        warn(f"{label}: venv no existe, salteando imports")
        return
    for modulo, nombre in paquetes:
        try:
            cmd = [
                str(venv_python),
                "-c",
                f"import {modulo}; v = getattr({modulo}, '__version__', '?'); print('VER=' + str(v))",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            if result.returncode == 0:
                ver_line = next(
                    (ln for ln in stdout.splitlines() if ln.startswith("VER=")),
                    "VER=?",
                )
                ok(f"{label} :: {nombre} {ver_line[4:]}")
            else:
                err_lines = [
                    ln for ln in stderr.splitlines()
                    if ln.strip() and not ln.startswith(("Loading DLC", "DLC loaded", "20"))
                ]
                err_msg = err_lines[-1] if err_lines else f"exit {result.returncode}"
                fail(f"{label} :: {nombre} no importa | {err_msg}")
        except Exception as exc:
            fail(f"{label} :: {nombre} fallo ({exc})")


def check_imports() -> None:
    header("3. Imports criticos")
    check_imports_en_venv(
        ROOT / "venv_310" / "Scripts" / "python.exe",
        PAQUETES_VENV310,
        "venv_310",
    )
    check_imports_en_venv(
        ROOT / "venv_311" / "Scripts" / "python.exe",
        PAQUETES_VENV311,
        "venv_311",
    )


# ============================================================
# 4. CUDA disponible (solo informativo)
# ============================================================
def check_cuda() -> None:
    header("4. PyTorch CUDA en venv_311")
    venv_311 = ROOT / "venv_311" / "Scripts" / "python.exe"
    if not venv_311.exists():
        warn("venv_311 no existe, salteando")
        return
    try:
        cmd = [
            str(venv_311),
            "-c",
            "import torch; print(torch.__version__); "
            "print('cuda_available=' + str(torch.cuda.is_available())); "
            "print('cuda_version=' + str(torch.version.cuda)); "
            "print('gpu=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=60)
        for line in out.strip().splitlines():
            ok(f"venv_311 :: {line}")
        if "cuda_available=False" in out:
            warn("PyTorch CPU-only en venv_311. YOLO procesara videos ~5x mas lento.")
    except Exception as exc:
        fail(f"No se pudo consultar PyTorch en venv_311: {exc}")


# ============================================================
# 5. Docker (opcional, para historial Postgres)
# ============================================================
def check_docker() -> None:
    header("5. Docker Desktop (opcional, historial de analisis)")
    if not shutil.which("docker"):
        warn("docker no esta en PATH (la UI funciona, pero sin historial Postgres)")
        return
    try:
        subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, timeout=10)
        ok("docker daemon corriendo")
    except subprocess.CalledProcessError:
        warn("docker instalado pero daemon no corre (abrir Docker Desktop)")
    except Exception as exc:
        warn(f"docker no responde: {exc}")


# ============================================================
# 6. .env y docker-compose.yml
# ============================================================
def parse_env_file(path: Path) -> dict[str, str]:
    """Parser simple de .env para validar onboarding sin imprimir secretos."""
    values: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    except Exception as exc:
        warn(f"No se pudo leer .env para validar credenciales: {exc}")
    return values


def check_auth_env(values: dict[str, str]) -> None:
    """Valida lo necesario para no arrancar con BD vacia y registro bloqueado."""
    required_db = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DB_HOST", "DB_PORT"]
    missing_db = [key for key in required_db if not values.get(key)]
    if missing_db:
        fail(".env incompleto para Postgres: faltan " + ", ".join(missing_db))
    else:
        ok(".env tiene variables de Postgres")

    admin_email = values.get("INITIAL_ADMIN_EMAIL", "")
    admin_password = values.get("INITIAL_ADMIN_PASSWORD", "")
    if admin_email in ENV_PLACEHOLDERS or admin_password in ENV_PLACEHOLDERS:
        warn(
            "INITIAL_ADMIN_EMAIL/PASSWORD siguen en placeholder. "
            "En una BD vacia no se creara admin inicial."
        )
    else:
        ok("admin inicial configurado para primer arranque")

    smtp_email = values.get("GMAIL_SENDER_EMAIL", "")
    smtp_password = values.get("GMAIL_APP_PASSWORD", "")
    if smtp_email in ENV_PLACEHOLDERS or smtp_password in ENV_PLACEHOLDERS:
        warn(
            "SMTP de Gmail no configurado. El registro usara modo DEV: "
            "el OTP aparece en la consola de launcher.bat."
        )
    else:
        ok("SMTP Gmail configurado para enviar OTP reales")

    if not values.get("PGADMIN_DEFAULT_EMAIL") or not values.get("PGADMIN_DEFAULT_PASSWORD"):
        warn("PGADMIN_DEFAULT_EMAIL/PASSWORD no configurados; pgAdmin puede no iniciar.")
    else:
        ok("pgAdmin local configurado")


def check_config() -> None:
    header("6. Archivos de configuracion")
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if env_file.exists():
        ok(".env existe")
        check_auth_env(parse_env_file(env_file))
    elif env_example.exists():
        warn(".env no existe, pero hay .env.example. Copialo: copy .env.example .env")
    else:
        fail("No hay ni .env ni .env.example")
    if (ROOT / "docker-compose.yml").exists():
        ok("docker-compose.yml presente")
    else:
        warn("docker-compose.yml no existe (Postgres no disponible)")


# ============================================================
# 7. Proyecto SimBA YOLO (estructura + paths sincronizados)
# ============================================================
SIMBA_YOLO_FOLDER = (
    ROOT / "data" / "simba_projects" / "grooming_thigmotaxis_yolo" / "project_folder"
)


def check_simba_yolo_project() -> None:
    header("7. Proyecto SimBA YOLO (estructura + paths)")

    if not SIMBA_YOLO_FOLDER.exists():
        fail(
            f"No existe {SIMBA_YOLO_FOLDER.relative_to(ROOT)} "
            "(copialo del USB o regenera el proyecto)"
        )
        return

    config_ini = SIMBA_YOLO_FOLDER / "project_config.ini"
    subdirs_requeridos = [
        SIMBA_YOLO_FOLDER / "csv" / "features_extracted",
        SIMBA_YOLO_FOLDER / "csv" / "targets_inserted",
        SIMBA_YOLO_FOLDER / "logs" / "measures",
    ]

    if not config_ini.exists():
        fail(f"{config_ini.relative_to(ROOT)} no existe")
    else:
        ok(f"{config_ini.relative_to(ROOT)} presente")

    for sd in subdirs_requeridos:
        if not sd.exists():
            fail(f"Falta subdirectorio SimBA: {sd.relative_to(ROOT)}")
        else:
            ok(f"{sd.relative_to(ROOT)} presente")

    # Verificar que project_config.ini tenga paths apuntando a este equipo.
    # Si no, el usuario debe correr src/scripts/fix_simba_paths.py.
    if config_ini.exists():
        try:
            content = config_ini.read_text(encoding="utf-8")
        except Exception as exc:
            fail(f"No se pudo leer {config_ini.relative_to(ROOT)}: {exc}")
            return

        keys_a_chequear = {
            "project_path": SIMBA_YOLO_FOLDER,
            "model_dir": SIMBA_YOLO_FOLDER.parent / "models",
            "model_path_1": (
                SIMBA_YOLO_FOLDER.parent / "models" / "generated_models" / "Thigmotaxis.sav"
            ),
            "model_path_2": (
                SIMBA_YOLO_FOLDER.parent / "models" / "generated_models" / "Grooming.sav"
            ),
        }
        desincronizados: list[str] = []
        for line in content.splitlines():
            if "=" not in line:
                continue
            left, _, right = line.partition("=")
            key = left.strip()
            if key in keys_a_chequear:
                actual = right.strip()
                esperado = str(keys_a_chequear[key].resolve())
                if actual.lower() != esperado.lower():
                    desincronizados.append(f"{key} = {actual}")

        if desincronizados:
            fail(
                "project_config.ini tiene paths absolutos de otro equipo. "
                "Correr: py -3.11 src\\scripts\\fix_simba_paths.py"
            )
            for entry in desincronizados:
                print(f"           {entry}")
        else:
            ok("project_config.ini tiene paths sincronizados a este equipo")


# ============================================================
# Main
# ============================================================
def main() -> int:
    print()
    print("============================================================")
    print("  VALIDACION DE INSTALACION TT_Ratones_2026")
    print("============================================================")
    check_python()
    check_modelos()
    check_imports()
    check_cuda()
    check_docker()
    check_config()
    check_simba_yolo_project()

    header("RESUMEN")
    print(f"  Fallas criticas : {len(fallas)}")
    print(f"  Advertencias    : {len(warnings)}")
    if fallas:
        print()
        print("  FALLAS:")
        for f in fallas:
            print(f"    - {f}")
    if warnings:
        print()
        print("  ADVERTENCIAS (no criticas):")
        for w in warnings:
            print(f"    - {w}")
    print()
    if fallas:
        print("  [RESULTADO] Hay fallas criticas. Resolverlas antes de usar la app.")
        return EXIT_FAIL
    if warnings:
        print("  [RESULTADO] Instalacion utilizable, con advertencias menores.")
    else:
        print("  [RESULTADO] Instalacion 100% completa y validada.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
