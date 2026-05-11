"""Crea un sandbox SimBA paralelo al proyecto productivo.

Un sandbox sirve para procesar videos de escenarios experimentales sin
contaminar las ROIs, features ni video_info del proyecto principal
(`grooming_thigmotaxis_yolo`). Los modelos productivos se referencian
via paths absolutos en `project_config.ini` (NO se copian, ahorra ~580 MB
por sandbox).

Uso:
    python src/scripts/bootstrap_sandbox.py --name nuevoescenario
    python src/scripts/bootstrap_sandbox.py --name otro --force

Por convencion el sandbox queda en
`data/simba_projects/sandbox_<nombre>/`. Si pasas `--name sandbox_X`,
el prefijo no se duplica.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Repo root para importar src.config sin importar desde donde se invoque.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


SUBDIRS = [
    Path("project_folder/csv/features_extracted"),
    Path("project_folder/csv/input_csv"),
    Path("project_folder/csv/machine_results"),
    Path("project_folder/csv/outlier_corrected_movement_location"),
    Path("project_folder/csv/targets_inserted"),
    Path("project_folder/csv/validation"),
    Path("project_folder/videos"),
    Path("project_folder/logs/measures/pose_configs/bp_names"),
    Path("models/generated_models"),
]

VIDEO_INFO_REL = Path("project_folder/logs/video_info.csv")
BP_NAMES_REL = Path("project_folder/logs/measures/pose_configs/bp_names/project_bp_names.csv")
CONFIG_REL = Path("project_folder/project_config.ini")
ROI_H5_REL = Path("project_folder/logs/measures/ROI_definitions.h5")

RECT_COLS = [
    "Video", "Shape_type", "Name", "Color name", "Color BGR", "Thickness",
    "Center_X", "Center_Y", "topLeftX", "topLeftY",
    "Bottom_right_X", "Bottom_right_Y", "width", "height",
    "width_cm", "height_cm", "area_cm", "Tags", "Ear_tag_size",
]
CIRCLE_COLS = [
    "Video", "Shape_type", "Name", "Color name", "Color BGR", "Thickness",
    "centerX", "centerY", "radius", "radius_cm", "area_cm",
    "Tags", "Ear_tag_size",
]
POLYGON_COLS = [
    "Video", "Shape_type", "Name", "Color name", "Color BGR", "Thickness",
    "Center_X", "Center_Y", "vertices", "center", "area",
    "max_vertice_distance", "area_cm", "Tags", "Ear_tag_size",
]


def normalize_sandbox_name(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("--name no puede estar vacio.")
    return raw if raw.startswith("sandbox_") else f"sandbox_{raw}"


def rewrite_project_config(
    config_path: Path,
    sandbox_project_folder: Path,
    sandbox_models_dir: Path,
    productivo_models_dir: Path,
) -> None:
    """Reescribe los 4 paths absolutos del project_config.ini para que
    el sandbox apunte a si mismo (project_path, model_dir) pero use los
    modelos productivos (model_path_1=Thigmo, model_path_2=Grooming)."""
    text = config_path.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines(keepends=True):
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key == "project_path":
                new_lines.append(f"project_path = {sandbox_project_folder.resolve()}\n")
                continue
            if key == "model_dir":
                new_lines.append(f"model_dir = {sandbox_models_dir.resolve()}\n")
                continue
            if key == "model_path_1":
                new_lines.append(
                    f"model_path_1 = {(productivo_models_dir / 'Thigmotaxis.sav').resolve()}\n"
                )
                continue
            if key == "model_path_2":
                new_lines.append(
                    f"model_path_2 = {(productivo_models_dir / 'Grooming.sav').resolve()}\n"
                )
                continue
        new_lines.append(line)
    config_path.write_text("".join(new_lines), encoding="utf-8")


def create_empty_roi_h5(path: Path) -> bool:
    """Crea un h5 con los 3 dataframes vacios que SimBA espera. Devuelve
    True si lo creo, False si pandas/tables no estan instalados."""
    try:
        import pandas as pd
    except ImportError:
        return False
    with pd.HDFStore(str(path), mode="w") as store:
        store["rectangles"] = pd.DataFrame(columns=RECT_COLS)
        store["circleDf"] = pd.DataFrame(columns=CIRCLE_COLS)
        store["polygons"] = pd.DataFrame(columns=POLYGON_COLS)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True,
                        help="Nombre del sandbox (sin prefijo sandbox_).")
    parser.add_argument("--force", action="store_true",
                        help="Sobrescribir si ya existe.")
    args = parser.parse_args()

    try:
        sandbox_name = normalize_sandbox_name(args.name)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        from src.config import SIMBA_YOLO_BASE, DATA_DIR
    except ImportError:
        from config import SIMBA_YOLO_BASE, DATA_DIR  # type: ignore

    sandbox_base = (DATA_DIR / "simba_projects" / sandbox_name).resolve()
    productivo_base = SIMBA_YOLO_BASE.resolve()

    if sandbox_base.exists():
        if not args.force:
            print(f"[ERROR] Sandbox ya existe: {sandbox_base}", file=sys.stderr)
            print("        Usa --force para sobrescribirlo.", file=sys.stderr)
            return 1
        print(f"[WARN] Removiendo sandbox existente: {sandbox_base}")
        shutil.rmtree(sandbox_base)

    print(f"[INFO] Creando sandbox: {sandbox_base}")

    # 1. Estructura de directorios
    for sub in SUBDIRS:
        (sandbox_base / sub).mkdir(parents=True, exist_ok=True)

    # 2. project_config.ini con paths reescritos
    src_config = productivo_base / CONFIG_REL
    dst_config = sandbox_base / CONFIG_REL
    if not src_config.exists():
        print(f"[ERROR] No existe project_config.ini en productivo: {src_config}",
              file=sys.stderr)
        return 1
    shutil.copy2(src_config, dst_config)
    rewrite_project_config(
        dst_config,
        sandbox_project_folder=sandbox_base / "project_folder",
        sandbox_models_dir=sandbox_base / "models",
        productivo_models_dir=productivo_base / "models" / "generated_models",
    )
    print(f"[OK]   project_config.ini configurado (paths del sandbox + modelos productivos referenciados)")

    # 3. video_info.csv vacio (solo header, importante para SimBA)
    src_vinfo = productivo_base / VIDEO_INFO_REL
    dst_vinfo = sandbox_base / VIDEO_INFO_REL
    if src_vinfo.exists():
        with open(src_vinfo, "r", encoding="utf-8") as f:
            header = f.readline()
        with open(dst_vinfo, "w", encoding="utf-8") as f:
            f.write(header)
        print(f"[OK]   video_info.csv creado vacio (con header)")
    else:
        print(f"[WARN] No se encontro video_info.csv en productivo; saltado")

    # 4. project_bp_names.csv copiado tal cual (define los 8 keypoints)
    src_bp = productivo_base / BP_NAMES_REL
    dst_bp = sandbox_base / BP_NAMES_REL
    if src_bp.exists():
        shutil.copy2(src_bp, dst_bp)
        print(f"[OK]   project_bp_names.csv copiado")
    else:
        print(f"[WARN] No se encontro project_bp_names.csv; saltado")

    # 5. ROI_definitions.h5 vacio con la estructura SimBA esperada
    roi_path = sandbox_base / ROI_H5_REL
    if create_empty_roi_h5(roi_path):
        print(f"[OK]   ROI_definitions.h5 creado vacio")
    else:
        print(f"[WARN] No se creo ROI_definitions.h5 (pandas no disponible).")
        print(f"       SimBA o la UI lo creara cuando se agregue la primera ROI.")

    print()
    print(f"[OK] Sandbox listo en: {sandbox_base}")
    print(f"     Productivo intacto en: {productivo_base}")
    print()
    print("Proximos pasos:")
    print("  1. Recarga la app Streamlit (Ctrl+Shift+R en la pestaña).")
    print(f"  2. En la pagina Keypoints, selecciona '{sandbox_name}' en")
    print("     el selector 'Proyecto SimBA'.")
    print("  3. Procesa el video; las zonas, features y video_info iran")
    print("     al sandbox sin tocar el productivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
