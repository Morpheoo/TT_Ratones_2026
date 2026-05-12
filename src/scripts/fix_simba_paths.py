"""Sincroniza los paths absolutos del project_config.ini de SimBA al path
local del repo.

SimBA guarda rutas absolutas en su config. Cuando alguien clona o mueve
el proyecto, esas rutas apuntan a la maquina anterior y la extraccion
de features falla con "SIMBA NOT A DIRECTORY ERROR".

Este script reescribe las 4 keys que SimBA usa al ejecutar
ExtractFeaturesFrom8bps:

    [General settings] project_path
    [SML settings]     model_dir
    [SML settings]     model_path_1   (Thigmotaxis.sav)
    [SML settings]     model_path_2   (Grooming.sav)

Idempotente: si los valores ya coinciden con el repo local, no escribe.

Uso:
    python src/scripts/fix_simba_paths.py
    python src/scripts/fix_simba_paths.py --dry-run
    python src/scripts/fix_simba_paths.py --project-root C:\\otra\\copia
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CONFIG_REL = Path(
    "data/simba_projects/grooming_thigmotaxis_yolo/project_folder/project_config.ini"
)

# Mapeo key -> ruta relativa al root del repo. Todas son las rutas que
# SimBA realmente abre en disco al hacer feature extraction o predict.
RELATIVE_PATHS = {
    "project_path": Path(
        "data/simba_projects/grooming_thigmotaxis_yolo/project_folder"
    ),
    "model_dir": Path("data/simba_projects/grooming_thigmotaxis_yolo/models"),
    "model_path_1": Path(
        "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav"
    ),
    "model_path_2": Path(
        "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav"
    ),
}


def to_simba_path(path: Path) -> str:
    return str(path.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Raiz del repo TT_Ratones_2026. Por defecto se detecta desde la ubicacion del script.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reporta cambios pero no escribe nada.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.project_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = args.project_root.resolve()

    config_path = repo_root / CONFIG_REL
    if not config_path.exists():
        print(
            f"[ERROR] project_config.ini no existe en: {config_path}",
            file=sys.stderr,
        )
        print(
            "        Verifica que --project-root apunta a la raiz del repo.",
            file=sys.stderr,
        )
        return 2

    expected = {
        key: to_simba_path(repo_root / rel)
        for key, rel in RELATIVE_PATHS.items()
    }

    original = config_path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    changes: list[tuple[str, str, str]] = []
    new_lines: list[str] = []
    seen_keys: set[str] = set()

    for raw in lines:
        line = raw
        if "=" in raw:
            left, _, right = raw.partition("=")
            key = left.strip()
            if key in expected and key not in seen_keys:
                seen_keys.add(key)
                current = right.strip().rstrip("\r\n")
                target = expected[key]
                if current != target:
                    changes.append((key, current, target))
                    eol = "\r\n" if raw.endswith("\r\n") else "\n"
                    line = f"{left}= {target}{eol}"
        new_lines.append(line)

    missing = set(expected) - seen_keys
    if missing:
        print(
            f"[WARN] Las siguientes keys no aparecen en el ini: {sorted(missing)}",
            file=sys.stderr,
        )

    if not changes:
        print(f"[OK] {config_path.name}: paths ya estan sincronizados.")
        return 0

    print(f"[INFO] Reescribiendo {len(changes)} ruta(s) en {config_path}:")
    for key, old, new in changes:
        print(f"  {key}")
        print(f"    antes : {old}")
        print(f"    ahora : {new}")

    if args.dry_run:
        print("[DRY-RUN] No se escribio nada.")
        return 0

    config_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"[OK] {config_path.name} actualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
