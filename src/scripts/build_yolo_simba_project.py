"""
build_yolo_simba_project.py
Crea el proyecto SimBA grooming_thigmotaxis_yolo usando YOLO v4 como backend de pose.

Pasos automatizados:
  1. Crear estructura del nuevo proyecto SimBA
  2. Correr YOLO v4 en los 10 videos de entrenamiento
  3. Extraer features SimBA de los CSVs YOLO
  4. Fusionar features + etiquetas → targets_inserted del nuevo proyecto

Despues de este script ejecutar:
  venv_310\\Scripts\\python.exe src\\scripts\\retrain_simba_models.py

Uso:
    venv_311\\Scripts\\python.exe src\\scripts\\build_yolo_simba_project.py
    venv_311\\Scripts\\python.exe src\\scripts\\build_yolo_simba_project.py --dry-run
    venv_311\\Scripts\\python.exe src\\scripts\\build_yolo_simba_project.py --skip-yolo
"""
from __future__ import annotations

import argparse
import configparser
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Proyecto SimBA origen (DLC) ──────────────────────────────────────────────
OLD_SIMBA_BASE = PROJECT_ROOT / "data" / "simba_projects" / "New folder" / "thigmotaxis_optimizado"
OLD_PROJECT_DIR = OLD_SIMBA_BASE / "project_folder"
OLD_TARGETS_DIR = OLD_PROJECT_DIR / "csv" / "targets_inserted"
OLD_VIDEOS_DIR  = OLD_PROJECT_DIR / "videos"

# ── Proyecto SimBA destino (YOLO) ─────────────────────────────────────────────
NEW_SIMBA_BASE  = PROJECT_ROOT / "data" / "simba_projects" / "grooming_thigmotaxis_yolo"
NEW_PROJECT_DIR = NEW_SIMBA_BASE / "project_folder"
NEW_CONFIG_PATH = NEW_PROJECT_DIR / "project_config.ini"
NEW_VIDEOS_DIR  = NEW_PROJECT_DIR / "videos"
NEW_INPUT_DIR   = NEW_PROJECT_DIR / "csv" / "input_csv"
NEW_OUTLIER_DIR = NEW_PROJECT_DIR / "csv" / "outlier_corrected_movement_location"
NEW_FEATURES_DIR= NEW_PROJECT_DIR / "csv" / "features_extracted"
NEW_TARGETS_DIR = NEW_PROJECT_DIR / "csv" / "targets_inserted"
NEW_MODELS_DIR  = NEW_SIMBA_BASE  / "models" / "generated_models"

# ── Scripts y modelos ─────────────────────────────────────────────────────────
PY311 = PROJECT_ROOT / "venv_311" / "Scripts" / "python.exe"
PY310 = PROJECT_ROOT / "venv_310" / "Scripts" / "python.exe"
YOLO_SCRIPT    = PROJECT_ROOT / "src" / "scripts" / "yolo_pose_to_csv.py"
FEATURES_SCRIPT= PROJECT_ROOT / "src" / "scripts" / "compute_simba_features.py"
YOLO_MODEL     = PROJECT_ROOT / "runs" / "pose" / "yolo11s_pose_raton_v4" / "weights" / "best.pt"
KP_YOLO_DIR    = PROJECT_ROOT / "keypoints_yolo"

BEHAVIORS = ["Grooming", "Thigmotaxis"]


# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


def header(text: str) -> None:
    log(f"\n{'='*70}\n  {text}\n{'='*70}")


def run(cmd: list[str], label: str) -> None:
    log(f"\n[CMD] {label}")
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT),
        creationflags=no_window,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} fallo con codigo {result.returncode}")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: Estructura del proyecto
# ─────────────────────────────────────────────────────────────────────────────

def create_project_structure() -> None:
    header("PASO 1: Creando estructura del proyecto YOLO SimBA")

    for d in [
        NEW_PROJECT_DIR,
        NEW_VIDEOS_DIR,
        NEW_INPUT_DIR,
        NEW_OUTLIER_DIR,
        NEW_FEATURES_DIR,
        NEW_TARGETS_DIR,
        NEW_MODELS_DIR,
        NEW_PROJECT_DIR / "csv" / "machine_results",
        NEW_PROJECT_DIR / "csv" / "validation",
        NEW_PROJECT_DIR / "logs",
    ]:
        d.mkdir(parents=True, exist_ok=True)
        log(f"  [DIR] {d.relative_to(PROJECT_ROOT)}")

    # Copiar project_config.ini y actualizar rutas
    old_config_path = OLD_PROJECT_DIR / "project_config.ini"
    config = configparser.ConfigParser()
    config.read(old_config_path, encoding="utf-8")

    new_proj_path = str(NEW_PROJECT_DIR).replace("/", "\\")
    new_models_dir = str(NEW_SIMBA_BASE / "models").replace("/", "\\")

    config.set("General settings", "project_path", new_proj_path)
    config.set("General settings", "project_name", "grooming_thigmotaxis_yolo")
    config.set("SML settings", "model_dir", new_models_dir)
    config.set("SML settings", "model_path_1",
               str(NEW_MODELS_DIR / "Thigmotaxis.sav").replace("/", "\\"))
    config.set("SML settings", "model_path_2",
               str(NEW_MODELS_DIR / "Grooming.sav").replace("/", "\\"))

    with open(NEW_CONFIG_PATH, "w", encoding="utf-8") as f:
        config.write(f)
    log(f"  [CONFIG] {NEW_CONFIG_PATH.relative_to(PROJECT_ROOT)}")

    # Copiar archivos de configuracion de logs necesarios para SimBA
    logs_src = OLD_PROJECT_DIR / "logs" / "measures"
    bp_src = logs_src / "pose_configs" / "bp_names" / "project_bp_names.csv"
    if bp_src.exists():
        bp_dst_dir = NEW_PROJECT_DIR / "logs" / "measures" / "pose_configs" / "bp_names"
        bp_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bp_src, bp_dst_dir / "project_bp_names.csv")
        log(f"  [BP] project_bp_names.csv copiado")

    roi_src = logs_src / "ROI_definitions.h5"
    if roi_src.exists():
        roi_dst_dir = NEW_PROJECT_DIR / "logs" / "measures"
        roi_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(roi_src, roi_dst_dir / "ROI_definitions.h5")
        log(f"  [ROI] ROI_definitions.h5 copiado")

    log("\n  [OK] Estructura creada correctamente.")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: Correr YOLO en videos de entrenamiento
# ─────────────────────────────────────────────────────────────────────────────

def get_training_videos() -> list[tuple[str, Path]]:
    """Retorna lista de (video_stem, video_path) para los videos anotados."""
    mapping = []
    for video_file in sorted(OLD_VIDEOS_DIR.glob("*.mp4")):
        stem = video_file.stem
        # Buscar el video en el proyecto existente primero (fuente mas confiable)
        if video_file.exists():
            mapping.append((stem, video_file))
    return mapping


def run_yolo_on_training_videos(dry_run: bool, skip_yolo: bool) -> dict[str, Path]:
    """Corre YOLO v4 en cada video. Retorna {stem: csv_path}."""
    header("PASO 2: Extraccion YOLO v4 en videos de entrenamiento")

    videos = get_training_videos()
    log(f"  Videos a procesar: {len(videos)}")
    csv_map: dict[str, Path] = {}

    for stem, video_path in videos:
        out_dir = KP_YOLO_DIR / stem
        out_csv = out_dir / f"{stem}_yolo_pose.csv"
        out_vid = out_dir / f"{stem}_yolo_keypoints.mp4"

        log(f"\n  [{stem}]")
        log(f"    Video: {video_path}")
        log(f"    CSV:   {out_csv}")

        if out_csv.exists():
            log(f"    [SKIP] CSV ya existe, reutilizando.")
            csv_map[stem] = out_csv
            continue

        if dry_run or skip_yolo:
            log(f"    [DRY/SKIP] Omitiendo inferencia YOLO.")
            if out_csv.exists():
                csv_map[stem] = out_csv
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        run([
            str(PY311), str(YOLO_SCRIPT),
            "--video",     str(video_path),
            "--output",    str(out_csv),
            "--video-out", str(out_vid),
            "--model",     str(YOLO_MODEL),
            "--conf",      "0.25",
        ], f"YOLO {stem}")
        log(f"    [OK] {time.time()-t0:.1f}s")
        csv_map[stem] = out_csv

    log(f"\n  CSVs generados: {len(csv_map)}/{len(videos)}")
    return csv_map


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: Extraer features SimBA
# ─────────────────────────────────────────────────────────────────────────────

def extract_simba_features(csv_map: dict[str, Path], dry_run: bool) -> list[str]:
    """Extrae features SimBA de cada CSV YOLO. Retorna lista de stems exitosos."""
    header("PASO 3: Extraccion de features SimBA (YOLO -> bridge -> 8bp)")

    successful: list[str] = []

    for stem, csv_path in csv_map.items():
        out_feature = NEW_FEATURES_DIR / f"{stem}.csv"
        video_path  = OLD_VIDEOS_DIR / f"{stem}.mp4"

        log(f"\n  [{stem}]")

        if out_feature.exists():
            log(f"    [SKIP] Features ya existen.")
            successful.append(stem)
            continue

        if dry_run:
            log(f"    [DRY] Omitiendo extraccion.")
            continue

        if not csv_path.exists():
            log(f"    [SKIP] CSV YOLO no encontrado: {csv_path}")
            continue

        t0 = time.time()
        run([
            str(PY310), str(FEATURES_SCRIPT),
            "--input",      str(csv_path),
            "--output",     str(out_feature),
            "--project",    str(NEW_SIMBA_BASE),
            "--video",      str(video_path),
            "--video_name", stem,
        ], f"FEATURES {stem}")
        log(f"    [OK] {time.time()-t0:.1f}s")
        successful.append(stem)

    log(f"\n  Features generadas: {len(successful)}/{len(csv_map)}")
    return successful


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: Fusionar features + etiquetas
# ─────────────────────────────────────────────────────────────────────────────

def merge_labels(successful: list[str], dry_run: bool) -> None:
    """
    Para cada video exitoso: lee features (YOLO) + etiquetas (DLC) y
    produce targets_inserted en el nuevo proyecto.
    """
    header("PASO 4: Fusionando features YOLO con etiquetas de conducta")

    merged_count = 0

    for stem in successful:
        feat_path   = NEW_FEATURES_DIR / f"{stem}.csv"
        labels_path = OLD_TARGETS_DIR  / f"{stem}.csv"
        target_path = NEW_TARGETS_DIR  / f"{stem}.csv"

        log(f"\n  [{stem}]")

        if not labels_path.exists():
            log(f"    [SKIP] Sin etiquetas en proyecto anterior.")
            continue

        if target_path.exists():
            log(f"    [SKIP] targets_inserted ya existe.")
            merged_count += 1
            continue

        if dry_run:
            log(f"    [DRY] Omitiendo fusion.")
            continue

        # Leer features YOLO (sin columnas de conducta)
        df_feat = pd.read_csv(feat_path)

        # Leer etiquetas del proyecto DLC
        df_labels = pd.read_csv(labels_path)
        behavior_cols = [c for c in df_labels.columns if c in BEHAVIORS]

        if not behavior_cols:
            log(f"    [WARN] No se encontraron columnas de conducta en {stem}.")
            continue

        # Alinear por numero de filas (ambos deben tener el mismo video)
        n_feat   = len(df_feat)
        n_labels = len(df_labels)

        if n_feat != n_labels:
            log(f"    [WARN] Longitudes distintas: features={n_feat}, labels={n_labels}. Truncando al menor.")
            n_min = min(n_feat, n_labels)
            df_feat   = df_feat.iloc[:n_min].reset_index(drop=True)
            df_labels = df_labels.iloc[:n_min].reset_index(drop=True)

        # Agregar columnas de conducta al final
        for col in behavior_cols:
            df_feat[col] = df_labels[col].values

        df_feat.to_csv(target_path, index=False)

        frames_total = len(df_feat)
        for col in behavior_cols:
            n = int(df_feat[col].sum())
            log(f"    [OK] {col}: {n}/{frames_total} frames positivos ({n/frames_total*100:.1f}%)")

        merged_count += 1

    log(f"\n  targets_inserted generados: {merged_count}/{len(successful)}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Construir proyecto SimBA YOLO")
    p.add_argument("--dry-run",   action="store_true", help="Validar sin ejecutar")
    p.add_argument("--skip-yolo", action="store_true", help="Omitir YOLO si CSVs ya existen")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    header("BUILD YOLO SIMBA PROJECT — grooming_thigmotaxis_yolo")
    log(f"  Proyecto origen: {OLD_SIMBA_BASE.name}")
    log(f"  Proyecto destino: {NEW_SIMBA_BASE.name}")
    log(f"  Modelo YOLO: {YOLO_MODEL.name}")
    log(f"  Dry-run: {args.dry_run}")

    # Validaciones previas
    for path, label in [
        (OLD_SIMBA_BASE,   "Proyecto SimBA origen"),
        (OLD_TARGETS_DIR,  "targets_inserted origen"),
        (OLD_VIDEOS_DIR,   "videos SimBA origen"),
        (PY311,            "venv_311 python"),
        (PY310,            "venv_310 python"),
        (YOLO_MODEL,       "Modelo YOLO v4"),
    ]:
        if not path.exists():
            log(f"  [ERROR] No encontrado: {label} -> {path}")
            return 1

    videos = get_training_videos()
    log(f"\n  Videos de entrenamiento encontrados: {len(videos)}")
    for stem, vpath in videos:
        log(f"    * {stem}")

    if len(videos) == 0:
        log("\n  [ERROR] No se encontraron videos. Verifica la ruta del proyecto origen.")
        return 1

    t_total = time.time()

    create_project_structure()
    csv_map   = run_yolo_on_training_videos(args.dry_run, args.skip_yolo)
    successful = extract_simba_features(csv_map, args.dry_run)
    merge_labels(successful, args.dry_run)

    elapsed = time.time() - t_total
    header("COMPLETADO")
    log(f"  Videos procesados: {len(successful)}/{len(videos)}")
    log(f"  Tiempo total: {int(elapsed//60)}m {int(elapsed%60)}s")
    log(f"\n  Siguiente paso — reentrenar clasificadores:")
    log(f"  venv_310\\Scripts\\python.exe src\\scripts\\retrain_simba_models.py")
    log(f"\n  (Edita src/config.py para apuntar al nuevo proyecto si lo necesitas)")

    return 0 if len(successful) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
