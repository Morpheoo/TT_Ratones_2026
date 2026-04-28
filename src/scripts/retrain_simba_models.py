"""
retrain_simba_models.py - Reentrenamiento de modelos SimBA (Grooming + Thigmotaxis)
TT Ratones 2026 | ESCOM - IPN

Entrena ambos clasificadores Random Forest usando todos los videos anotados
en targets_inserted/. Hace backup de los modelos anteriores antes de sobreescribir.

Uso:
    .\\venv_310\\Scripts\\python.exe src\\scripts\\retrain_simba_models.py

Opciones:
    --dry-run       Solo valida el dataset sin entrenar
    --behavior X    Entrena solo un clasificador (Grooming o Thigmotaxis)
    --no-backup     No hacer backup de modelos anteriores
"""

from __future__ import annotations

import argparse
import configparser
import io
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# -- Fix Windows console encoding --
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# -- Paths --
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    SIMBA_BASE,
    SIMBA_PROJECT_DIR,
    SIMBA_GENERATED_MODELS_DIR,
    SIMBA_YOLO_BASE,
    SIMBA_YOLO_PROJECT_DIR,
    SIMBA_YOLO_GENERATED_MODELS_DIR,
)

# -- Seleccion de proyecto via argumento (se resuelve antes de parse_args completo) --
_use_yolo = "--yolo" in sys.argv

if _use_yolo:
    _base = SIMBA_YOLO_BASE
    _proj = SIMBA_YOLO_PROJECT_DIR
    _models = SIMBA_YOLO_GENERATED_MODELS_DIR
else:
    _base = SIMBA_BASE
    _proj = SIMBA_PROJECT_DIR
    _models = SIMBA_GENERATED_MODELS_DIR

CONFIG_PATH = str((_base / "project_folder" / "project_config.ini").resolve())
TARGETS_DIR = _proj / "csv" / "targets_inserted"
FEATURES_DIR = _proj / "csv" / "features_extracted"
VIDEOS_DIR = _proj / "videos"
BACKUP_DIR = _models / "backups"

BEHAVIORS = ["Thigmotaxis", "Grooming"]


# -- Helpers --

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def header(text: str) -> None:
    width = 70
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def validate_dataset() -> dict:
    """
    Verifica que todos los archivos necesarios existan y sean consistentes.
    Retorna un diccionario con el resumen.
    """
    header("VALIDACION DEL DATASET")

    # Videos en el proyecto
    videos = sorted([f.stem for f in VIDEOS_DIR.glob("*.mp4")])
    print(f"\n[VIDEO] Videos en proyecto SimBA ({len(videos)}):")
    for v in videos:
        print(f"   * {v}")

    # Features extraidas
    features = sorted([f.stem for f in FEATURES_DIR.glob("*.csv")])
    print(f"\n[FEATURES] Features extraidas ({len(features)}):")
    for f in features:
        print(f"   * {f}")

    # Targets insertados (anotaciones)
    targets = sorted([f.stem for f in TARGETS_DIR.glob("*.csv")])
    print(f"\n[LABELS] Anotaciones en targets_inserted ({len(targets)}):")
    for t in targets:
        print(f"   * {t}")

    # Verificar consistencia
    videos_set = set(videos)
    features_set = set(features)
    targets_set = set(targets)

    # Videos sin features
    missing_features = videos_set - features_set
    if missing_features:
        print(f"\n[WARN] Videos SIN features extraidas:")
        for m in sorted(missing_features):
            print(f"   X {m}")

    # Videos sin anotaciones
    missing_targets = features_set - targets_set
    if missing_targets:
        print(f"\n[WARN] Videos con features PERO sin anotaciones (no se usaran):")
        for m in sorted(missing_targets):
            print(f"   ! {m}")

    # Anotaciones huerfanas (sin features)
    orphan_targets = targets_set - features_set
    if orphan_targets:
        print(f"\n[ERROR] Anotaciones SIN features (error potencial):")
        for o in sorted(orphan_targets):
            print(f"   X {o}")

    # Dataset efectivo (interseccion de features y targets)
    effective = sorted(features_set & targets_set)
    print(f"\n[OK] Dataset efectivo para entrenamiento: {len(effective)} videos")
    for e in effective:
        print(f"   + {e}")

    # Verificar columnas de targets en un archivo de ejemplo
    if effective:
        import pandas as pd
        sample_path = TARGETS_DIR / f"{effective[0]}.csv"
        try:
            df = pd.read_csv(sample_path, nrows=5)
            cols = list(df.columns)
            print(f"\n[INFO] Columnas del primer target ({effective[0]}):")
            behavior_cols = [c for c in cols if c in BEHAVIORS]
            print(f"   Columnas de conducta encontradas: {behavior_cols}")
            if not behavior_cols:
                print("   [WARN] No se encontraron columnas de conducta en el CSV")
                print(f"   Ultimas 5 columnas: {cols[-5:]}")
        except Exception as e:
            print(f"   [WARN] No se pudo leer sample: {e}")

    result = {
        "videos": videos,
        "features": features,
        "targets": targets,
        "effective": effective,
        "missing_features": sorted(missing_features),
        "missing_targets": sorted(missing_targets),
    }

    return result


def backup_models(behaviors: list[str]) -> None:
    """Hace backup de los modelos actuales antes de sobreescribir."""
    header("BACKUP DE MODELOS ANTERIORES")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = timestamp()

    for behavior in behaviors:
        model_path = SIMBA_GENERATED_MODELS_DIR / f"{behavior}.sav"
        if model_path.exists():
            backup_name = f"{behavior}_{ts}.sav"
            backup_path = BACKUP_DIR / backup_name
            shutil.copy2(model_path, backup_path)
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"   [BACKUP] {behavior}.sav ({size_mb:.1f} MB) -> backups/{backup_name}")
        else:
            print(f"   [INFO] {behavior}.sav no existe (se creara nuevo)")

    existing_backups = sorted(BACKUP_DIR.glob("*.sav"))
    if existing_backups:
        print(f"\n   [INFO] Total backups en carpeta: {len(existing_backups)}")


def train_classifier(behavior: str) -> bool:
    """
    Entrena un clasificador de SimBA para una conducta especifica.
    Retorna True si fue exitoso.
    """
    header(f"ENTRENANDO: {behavior}")

    # 1. Actualizar config para apuntar al clasificador correcto
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    config.set("create ensemble settings", "classifier", behavior)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        config.write(f)

    print(f"   [CONFIG] classifier = {behavior}")
    print(f"   [CONFIG] path: {CONFIG_PATH}")

    print(f"\n   Hiperparametros:")
    print(f"   * n_estimators:    {config.get('create ensemble settings', 'rf_n_estimators')}")
    print(f"   * min_sample_leaf: {config.get('create ensemble settings', 'rf_min_sample_leaf')}")
    print(f"   * max_features:    {config.get('create ensemble settings', 'rf_max_features')}")
    print(f"   * criterion:       {config.get('create ensemble settings', 'rf_criterion')}")
    print(f"   * train/test split:{config.get('create ensemble settings', 'train_test_size')}")
    print(f"   * undersampling:   {config.get('create ensemble settings', 'under_sample_setting')} (ratio {config.get('create ensemble settings', 'under_sample_ratio')})")
    print(f"   * n_jobs:          {config.get('create ensemble settings', 'rf_n_jobs')}")

    # 2. Entrenar
    print(f"\n   [START] Iniciando entrenamiento... ({datetime.now().strftime('%H:%M:%S')})")
    start_time = time.time()

    try:
        from simba.model.train_rf import TrainRandomForestClassifier

        trainer = TrainRandomForestClassifier(config_path=CONFIG_PATH)
        trainer.run()
        trainer.save()

        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        print(f"\n   [TIME] Tiempo de entrenamiento: {minutes}m {seconds}s")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n   [ERROR] durante entrenamiento de {behavior}:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print(f"   [TIME] Fallo despues de {elapsed:.1f}s")
        return False

    # 3. Verificar que el modelo se guardo
    model_path = SIMBA_GENERATED_MODELS_DIR / f"{behavior}.sav"
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(model_path.stat().st_mtime)
        print(f"   [OK] Modelo guardado: {model_path.name} ({size_mb:.1f} MB)")
        print(f"   [OK] Ultima modificacion: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        print(f"   [ERROR] Modelo NO fue creado: {model_path}")
        return False


# -- Main --

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reentrenar modelos SimBA (Grooming + Thigmotaxis)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo validar dataset sin entrenar"
    )
    parser.add_argument(
        "--behavior",
        choices=["Grooming", "Thigmotaxis"],
        help="Entrenar solo un clasificador"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No hacer backup de modelos anteriores"
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Usar proyecto grooming_thigmotaxis_yolo en lugar del proyecto DLC"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    header("REENTRENAMIENTO DE MODELOS SimBA")
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Proyecto: {SIMBA_BASE.name}")
    print(f"   Config: {CONFIG_PATH}")

    behaviors_to_train = [args.behavior] if args.behavior else BEHAVIORS

    print(f"   Modelos a entrenar: {', '.join(behaviors_to_train)}")

    # 1. Validar dataset
    dataset = validate_dataset()

    if len(dataset["effective"]) == 0:
        print("\n[ERROR] No hay videos con features + anotaciones. No se puede entrenar.")
        return 1

    if len(dataset["effective"]) < 3:
        print(f"\n[WARN] Solo hay {len(dataset['effective'])} videos. El entrenamiento puede no ser confiable.")

    if args.dry_run:
        header("DRY RUN COMPLETADO")
        print("   No se entreno nada. Usa sin --dry-run para entrenar.")
        return 0

    # 2. Backup
    if not args.no_backup:
        backup_models(behaviors_to_train)

    # 3. Entrenar
    results = {}
    total_start = time.time()

    for behavior in behaviors_to_train:
        success = train_classifier(behavior)
        results[behavior] = success

    total_elapsed = time.time() - total_start

    # 4. Resumen final
    header("RESUMEN FINAL")
    print(f"   Videos usados: {len(dataset['effective'])}")
    print(f"   Tiempo total: {int(total_elapsed // 60)}m {int(total_elapsed % 60)}s")
    print()

    all_ok = True
    for behavior, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        model_path = SIMBA_GENERATED_MODELS_DIR / f"{behavior}.sav"
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"   {status} {behavior}.sav ({size_mb:.1f} MB)")
        else:
            print(f"   {status} {behavior}.sav")
            all_ok = False

    if all_ok:
        print(f"\n   >>> TODOS LOS MODELOS ENTRENADOS EXITOSAMENTE! <<<")
    else:
        print(f"\n   [WARN] Algunos modelos fallaron. Revisa los logs arriba.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
