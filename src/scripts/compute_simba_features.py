import argparse
import json
import os
import shutil
import sys
import warnings
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
from simba.feature_extractors.feature_extractor_8bp import ExtractFeaturesFrom8bps
from simba.roi_tools.ROI_feature_analyzer import ROIFeatureCreator
from simba.roi_tools.roi_utils import (
    get_circle_df_headers,
    get_polygon_df_headers,
    get_rectangle_df_headers,
)

SCRIPT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from simba_roi_bridge import sync_streamlit_rois_to_simba, sync_video_to_simba_project

warnings.filterwarnings("ignore", category=FutureWarning)

print("\n" + "=" * 40)
print("SIMBA FEATURE BRIDGE v3.0 [PROJECT_SYNC]")
print("=" * 40)

RECTANGLE_HEADERS = get_rectangle_df_headers()
CIRCLE_HEADERS = get_circle_df_headers()
POLYGON_HEADERS = get_polygon_df_headers()

ROI_STYLE = {
    "pared1": ("coral", (120, 120, 240)),
    "pared2": ("coral", (120, 120, 240)),
    "pared3": ("cyan", (255, 250, 0)),
    "pared4": ("cyan", (255, 250, 0)),
    "pared5": ("orange", (0, 165, 255)),
    "pared6": ("yellow", (0, 255, 255)),
}

REQUIRED_ROI_COLUMNS = [
    f"{roi_name} Animal_1 Center distance"
    for roi_name in ("pared1", "pared2", "pared3", "pared4", "pared5", "pared6", "pared23")
]
REQUIRED_ROI_COLUMNS.extend(
    [
        f"{roi_name} Animal_1 Center in zone"
        for roi_name in ("pared1", "pared2", "pared3", "pared4", "pared5", "pared6", "pared23")
    ]
)
REQUIRED_ROI_COLUMNS.extend(
    [
        f"{roi_name} Animal_1 facing"
        for roi_name in ("pared1", "pared2", "pared3", "pared4", "pared5", "pared6", "pared23")
    ]
)


def _looks_like_dlc_multilevel_csv(input_csv: str) -> bool:
    try:
        with open(input_csv, "r", encoding="utf-8", errors="ignore") as file_handle:
            first_line = file_handle.readline().strip().lower()
            second_line = file_handle.readline().strip().lower()
        return first_line.startswith("scorer,") and second_line.startswith("bodyparts,")
    except Exception:
        return False


def _load_pose_dataframe(input_csv: str) -> pd.DataFrame:
    """
    Acepta:
    - CSV DLC crudo con encabezado multinivel (scorer/bodyparts/coords)
    - CSV ya aplanado tipo SimBA
    - CSV enriquecido de features que aun conserva las 24 columnas base
    """
    if _looks_like_dlc_multilevel_csv(input_csv):
        print("[ENGINE] Formato detectado: CSV DLC crudo (multi-header)")
        df_in = pd.read_csv(input_csv, header=[0, 1, 2], index_col=0)
        flat_columns = []
        for _, bodypart, coord in df_in.columns:
            coord_name = "likelihood" if coord in {"p", "likelihood"} else coord
            flat_columns.append(f"{bodypart}_{coord_name}")
        df_in.columns = flat_columns
        df_in = df_in.reset_index().rename(columns={"index": "Unnamed: 0"})
        return df_in

    print("[ENGINE] Formato detectado: CSV tabular")
    df_in = pd.read_csv(input_csv)
    if "Unnamed: 0" not in df_in.columns:
        unnamed_cols = [column for column in df_in.columns if column.startswith("Unnamed")]
        if unnamed_cols:
            df_in = df_in.rename(columns={unnamed_cols[0]: "Unnamed: 0"})
        else:
            df_in.insert(0, "Unnamed: 0", list(range(len(df_in))))
    return df_in


def _resolve_pose_column(columns, bodypart_names, suffix: str) -> str | None:
    if isinstance(bodypart_names, str):
        bodypart_names = [bodypart_names]

    column_lookup = {str(column).lower(): str(column) for column in columns}
    candidates: list[str] = []
    for bodypart_name in bodypart_names:
        if suffix == "_likelihood":
            candidates.extend(
                [
                    f"{bodypart_name}_likelihood",
                    f"{bodypart_name}_p",
                ]
            )
        else:
            candidates.append(f"{bodypart_name}{suffix}")

    for candidate in candidates:
        if candidate in columns:
            return candidate
        normalized = column_lookup.get(candidate.lower())
        if normalized:
            return normalized
    return None


def _extract_numeric_suffix(label: str) -> int:
    digits = "".join(character for character in label if character.isdigit())
    return int(digits) if digits else 999


def _normalize_zone_label(zone_data: dict) -> str:
    return str(
        zone_data.get("id")
        or zone_data.get("name")
        or zone_data.get("Nombre Zona")
        or "Zona"
    ).strip()


def _collect_rectangular_zones(zonas_list: list[dict]) -> list[dict]:
    rectangles: list[dict] = []
    for zone in zonas_list:
        if str(zone.get("type", "rect")).lower() == "line":
            continue
        x = zone.get("x", zone.get("left"))
        y = zone.get("y", zone.get("top"))
        width = zone.get("w", zone.get("width"))
        height = zone.get("h", zone.get("height"))
        # Checks separados para que pyright pueda estrechar los tipos a no-None
        if x is None or y is None or width is None or height is None:
            continue
        rectangles.append(
            {
                "label": _normalize_zone_label(zone),
                "label_lower": _normalize_zone_label(zone).lower(),
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
            }
        )
    return rectangles


def _map_zones_to_simba_rois(zonas_list: list[dict]) -> dict[str, dict]:
    rectangles = _collect_rectangular_zones(zonas_list)
    sort_key = lambda item: (_extract_numeric_suffix(item["label"]), item["label_lower"])
    open_zones = sorted(
        [zone for zone in rectangles if "abierto" in zone["label_lower"] or "open" in zone["label_lower"]],
        key=sort_key,
    )
    closed_zones = sorted(
        [zone for zone in rectangles if "cerrado" in zone["label_lower"] or "closed" in zone["label_lower"]],
        key=sort_key,
    )
    center_zones = sorted(
        [zone for zone in rectangles if "centro" in zone["label_lower"] or "center" in zone["label_lower"]],
        key=sort_key,
    )

    roi_map: dict[str, dict] = {}
    if open_zones:
        roi_map["pared1"] = open_zones[0]
        roi_map["pared2"] = open_zones[1] if len(open_zones) > 1 else open_zones[0]
    if closed_zones:
        roi_map["pared3"] = closed_zones[0]
        roi_map["pared4"] = closed_zones[1] if len(closed_zones) > 1 else closed_zones[0]
        roi_map["pared6"] = closed_zones[0]
    if center_zones:
        roi_map["pared5"] = center_zones[0]
    return roi_map


def _infer_project_calibration(video_info_df: pd.DataFrame) -> tuple[float, float]:
    if video_info_df.empty:
        return 400.0, 2.5

    # .get() puede retornar None si la columna no existe → guard explícito antes de dropna()
    _px_col = video_info_df.get("pixels/mm")
    pixels_series = pd.to_numeric(_px_col, errors="coerce").dropna() if _px_col is not None else pd.Series(dtype=float)
    _dist_col = video_info_df.get("Distance_in_mm")
    distance_series = pd.to_numeric(_dist_col, errors="coerce").dropna() if _dist_col is not None else pd.Series(dtype=float)

    stable_pixels = pixels_series[pixels_series > 1.05]
    stable_distance = distance_series[distance_series > 0]

    pixels_per_mm = stable_pixels.median() if not stable_pixels.empty else 2.5
    distance_in_mm = stable_distance.median() if not stable_distance.empty else 400.0
    return distance_in_mm, pixels_per_mm


def _read_video_metadata(video_path: str | None) -> tuple[float, int, int, str]:
    if not video_path or not os.path.exists(video_path):
        return 30.0, 1280, 720, ".mp4"

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        return 30.0, 1280, 720, os.path.splitext(video_path)[1] or ".mp4"

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    capture.release()
    extension = os.path.splitext(video_path)[1] or ".mp4"
    return fps, width, height, extension


def _sync_video_registration(project_folder: str, video_name: str, video_path: str | None) -> tuple[float, float]:
    logs_dir = os.path.join(project_folder, "logs")
    videos_dir = os.path.join(project_folder, "videos")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)

    video_info_path = os.path.join(logs_dir, "video_info.csv")
    if os.path.exists(video_info_path):
        video_info_df = pd.read_csv(video_info_path)
    else:
        video_info_df = pd.DataFrame(
            columns=[
                "Video",
                "fps",
                "Resolution_width",
                "Resolution_height",
                "Distance_in_mm",
                "pixels/mm",
            ]
        )

    distance_in_mm, pixels_per_mm = _infer_project_calibration(video_info_df)
    fps, width, height, extension = _read_video_metadata(video_path)

    if video_path and os.path.exists(video_path):
        dest_video_path = os.path.join(videos_dir, f"{video_name}{extension}")
        if os.path.abspath(video_path) != os.path.abspath(dest_video_path):
            shutil.copy2(video_path, dest_video_path)
            print(f"[ENGINE] Video sincronizado en proyecto SimBA: {dest_video_path}")

    row = pd.DataFrame(
        [
            {
                "Video": video_name,
                "fps": fps,
                "Resolution_width": width,
                "Resolution_height": height,
                "Distance_in_mm": distance_in_mm,
                "pixels/mm": pixels_per_mm,
            }
        ]
    )
    video_info_df = pd.concat(
        [video_info_df[video_info_df["Video"] != video_name], row],
        ignore_index=True,
    )
    video_info_df.to_csv(video_info_path, index=False)
    print(
        f"[ENGINE] video_info.csv actualizado para {video_name} "
        f"(fps={fps:.2f}, {width}x{height}, px/mm={pixels_per_mm})"
    )
    return distance_in_mm, pixels_per_mm


def _empty_roi_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame(columns=RECTANGLE_HEADERS),
        pd.DataFrame(columns=CIRCLE_HEADERS),
        pd.DataFrame(columns=POLYGON_HEADERS),
    )


def _backup_corrupt_roi_file(roi_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = roi_path.replace(".h5", f".corrupt_{timestamp}.h5")
    shutil.copy2(roi_path, backup_path)
    print(f"[ENGINE] ROI_definitions.h5 corrupto respaldado en: {backup_path}")
    return backup_path


def _load_existing_roi_frames(roi_path: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rectangles_df, circles_df, polygon_df = _empty_roi_frames()
    if not os.path.exists(roi_path):
        return rectangles_df, circles_df, polygon_df

    invalid_store = False
    try:
        with pd.HDFStore(roi_path, mode="r") as store:
            keys = set(store.keys())
        if "/rectangles" in keys:
            rectangles_df = pd.DataFrame(pd.read_hdf(roi_path, key="rectangles"))
        if "/circleDf" in keys:
            circles_df = pd.DataFrame(pd.read_hdf(roi_path, key="circleDf"))
        if "/polygons" in keys:
            polygon_df = pd.DataFrame(pd.read_hdf(roi_path, key="polygons"))
    except Exception as error:
        invalid_store = True
        print(f"[ENGINE] ROI store invalido detectado: {error}")

    if invalid_store:
        _backup_corrupt_roi_file(roi_path)
        return _empty_roi_frames()

    return (
        rectangles_df.reindex(columns=RECTANGLE_HEADERS),
        circles_df.reindex(columns=CIRCLE_HEADERS),
        polygon_df.reindex(columns=POLYGON_HEADERS),
    )


def _create_rectangle_entry(video_name: str, roi_name: str, zone_data: dict, pixels_per_mm: float) -> dict:
    x = int(zone_data["x"])
    y = int(zone_data["y"])
    width = int(zone_data["width"])
    height = int(zone_data["height"])
    bottom_right_x = x + width
    bottom_right_y = y + height
    center_x = x + round(width / 2)
    center_y = y + round(height / 2)
    color_name, color_bgr = ROI_STYLE.get(roi_name, ("gray", (150, 150, 150)))
    px_per_mm_safe = pixels_per_mm if pixels_per_mm > 0 else 2.5
    width_cm = round((width / px_per_mm_safe) / 10, 2)
    height_cm = round((height / px_per_mm_safe) / 10, 2)

    return {
        "Video": video_name,
        "Shape_type": "rectangle",
        "Name": roi_name,
        "Color name": color_name,
        "Color BGR": color_bgr,
        "Thickness": 2,
        "Center_X": center_x,
        "Center_Y": center_y,
        "topLeftX": x,
        "topLeftY": y,
        "Bottom_right_X": bottom_right_x,
        "Bottom_right_Y": bottom_right_y,
        "width": width,
        "height": height,
        "width_cm": width_cm,
        "height_cm": height_cm,
        "area_cm": round(width_cm * height_cm, 2),
        "Tags": {
            "Center tag": (center_x, center_y),
            "Top left tag": (x, y),
            "Bottom right tag": (bottom_right_x, bottom_right_y),
            "Top right tag": (bottom_right_x, y),
            "Bottom left tag": (x, bottom_right_y),
            "Top tag": (center_x, y),
            "Right tag": (bottom_right_x, center_y),
            "Left tag": (x, center_y),
            "Bottom tag": (center_x, bottom_right_y),
        },
        "Ear_tag_size": 6,
    }


def _sync_roi_definitions(project_folder: str, video_name: str, zonas_path: str | None, pixels_per_mm: float) -> list[str]:
    roi_dir = os.path.join(project_folder, "logs", "measures")
    os.makedirs(roi_dir, exist_ok=True)
    roi_path = os.path.join(roi_dir, "ROI_definitions.h5")

    rectangles_df, circles_df, polygon_df = _load_existing_roi_frames(roi_path)
    rectangles_df = rectangles_df[rectangles_df["Video"] != video_name].reset_index(drop=True)
    circles_df = circles_df[circles_df["Video"] != video_name].reset_index(drop=True)
    polygon_df = polygon_df[polygon_df["Video"] != video_name].reset_index(drop=True)

    roi_names: list[str] = []
    if zonas_path and os.path.exists(zonas_path):
        with open(zonas_path, "r", encoding="utf-8") as file_handle:
            zonas_list = json.load(file_handle)
        roi_map = _map_zones_to_simba_rois(zonas_list)
        if roi_map:
            new_rectangles = pd.DataFrame(
                [
                    _create_rectangle_entry(video_name, roi_name, zone_data, pixels_per_mm)
                    for roi_name, zone_data in roi_map.items()
                ],
                columns=RECTANGLE_HEADERS,
            )
            rectangles_df = pd.concat([rectangles_df, new_rectangles], ignore_index=True)
            roi_names = list(roi_map.keys())
            print(f"[ENGINE] ROI SimBA sincronizadas para {video_name}: {roi_names}")
        else:
            print("[ENGINE] No se encontraron zonas rectangulares compatibles para generar ROIs.")
    else:
        print("[ENGINE] Sin zonas JSON: se preservan/repairan ROIs existentes sin agregar nuevas.")

    with pd.HDFStore(roi_path, mode="w") as store:
        store["rectangles"] = rectangles_df.reindex(columns=RECTANGLE_HEADERS)
        store["circleDf"] = circles_df.reindex(columns=CIRCLE_HEADERS)
        store["polygons"] = polygon_df.reindex(columns=POLYGON_HEADERS)

    return roi_names


def _ensure_required_roi_columns(df_features: pd.DataFrame) -> pd.DataFrame:
    wrong_facing_columns = [
        column_name
        for column_name in df_features.columns
        if column_name.startswith("pared") and column_name.endswith(" Animal_1 Center facing")
    ]
    if wrong_facing_columns:
        df_features = df_features.drop(columns=wrong_facing_columns)

    for column_name in REQUIRED_ROI_COLUMNS:
        if column_name not in df_features.columns:
            df_features[column_name] = 0.0
    return df_features


def _load_zonas_list(zonas_path: str | None) -> list[dict]:
    if not zonas_path or not os.path.exists(zonas_path):
        return []
    with open(zonas_path, "r", encoding="utf-8") as file_handle:
        zonas_data = json.load(file_handle)
    return zonas_data if isinstance(zonas_data, list) else []


def _get_existing_canonical_rois(project_folder: str, video_name: str) -> list[str]:
    roi_path = os.path.join(project_folder, "logs", "measures", "ROI_definitions.h5")
    rectangles_df, _, _ = _load_existing_roi_frames(roi_path)
    if rectangles_df.empty:
        return []

    valid_names = {"pared1", "pared2", "pared3", "pared4", "pared5", "pared6", "pared23"}
    video_roi_names = rectangles_df.loc[
        rectangles_df["Video"] == video_name,
        "Name",
    ].dropna().astype(str).tolist()
    return [roi_name for roi_name in video_roi_names if roi_name in valid_names]


def _build_pose_bridge(input_csv: str, output_dir: str, video_name: str) -> str:
    print("[ENGINE] Mapeando bodyparts DLC a configuracion SimBA 8bp...")
    df_in = _load_pose_dataframe(input_csv)
    mapping = {
        "Nose": ["nose", "Nose", "nariz"],
        "Ear_left": ["left_ear", "Ear_left", "oreja-izq", "left_front_paw"],
        "Ear_right": ["right_ear", "Ear_right", "oreja-der", "right_front_paw"],
        "Center": ["mouse_center", "head_midpoint", "Head_center", "Center", "torso", "body_center"],
        "Lat_left": ["left_midside", "Lateral_left", "Lat_left", "pata-izq", "left_back_paw"],
        "Lat_right": ["right_midside", "Lateral_right", "Lat_right", "pata-der", "right_back_paw"],
        "Tail_base": ["tail_base", "Tail_base", "cola-base"],
        "Tail_end": ["tail1", "tail_end", "Tail_end", "punta-cola", "neck"],
    }

    cols_to_keep = ["Unnamed: 0"]
    rename_dict: dict[str, str] = {}
    matched_columns = 0
    missing_columns: list[str] = []
    for simba_name, dlc_candidates in mapping.items():
        for suffix in ("_x", "_y", "_likelihood"):
            new_col = f"{simba_name}{'_p' if suffix == '_likelihood' else suffix}"
            old_col = _resolve_pose_column(df_in.columns, dlc_candidates, suffix)
            if old_col is not None and old_col in df_in.columns:
                cols_to_keep.append(old_col)
                rename_dict[old_col] = new_col
                matched_columns += 1
            else:
                df_in[new_col] = 0.0
                cols_to_keep.append(new_col)
                missing_columns.append(f"{dlc_candidates[0]}{suffix}")

    print(f"[ENGINE] Columnas base encontradas: {matched_columns}/24")
    if missing_columns:
        print(f"[ENGINE] Columnas faltantes rellenadas con 0.0: {missing_columns[:8]}")
    if matched_columns < 12:
        raise ValueError(
            "No se detectaron suficientes keypoints DLC/SimBA en el CSV fuente. "
            f"Columnas encontradas: {matched_columns}/24"
        )

    ordered_cols = [
        "Unnamed: 0",
        "Nose_x",
        "Nose_y",
        "Nose_p",
        "Ear_left_x",
        "Ear_left_y",
        "Ear_left_p",
        "Ear_right_x",
        "Ear_right_y",
        "Ear_right_p",
        "Center_x",
        "Center_y",
        "Center_p",
        "Lat_left_x",
        "Lat_left_y",
        "Lat_left_p",
        "Lat_right_x",
        "Lat_right_y",
        "Lat_right_p",
        "Tail_base_x",
        "Tail_base_y",
        "Tail_base_p",
        "Tail_end_x",
        "Tail_end_y",
        "Tail_end_p",
    ]
    df_bridge = df_in[cols_to_keep].rename(columns=rename_dict)[ordered_cols]
    bridge_csv = os.path.join(output_dir, f"bridge_{video_name}.csv")
    df_bridge.to_csv(bridge_csv, index=False)
    print(f"[ENGINE] Bridge 8bp generado: {bridge_csv}")
    return bridge_csv


def _sync_pose_files(project_folder: str, video_name: str, bridge_csv: str) -> tuple[str, str]:
    simba_input_dir = os.path.join(project_folder, "csv", "input_csv")
    simba_outlier_dir = os.path.join(project_folder, "csv", "outlier_corrected_movement_location")
    os.makedirs(simba_input_dir, exist_ok=True)
    os.makedirs(simba_outlier_dir, exist_ok=True)

    input_target = os.path.join(simba_input_dir, f"{video_name}.csv")
    outlier_target = os.path.join(simba_outlier_dir, f"{video_name}.csv")
    shutil.copy2(bridge_csv, input_target)
    shutil.copy2(bridge_csv, outlier_target)
    print(f"[ENGINE] Pose sincronizada en input_csv/outlier_corrected para {video_name}")
    return input_target, outlier_target


def _run_simba_extractors(config_ini: str, pose_csv_path: str, feature_csv_path: str, roi_names: list[str]) -> None:
    if os.path.exists(feature_csv_path):
        os.remove(feature_csv_path)

    print("[ENGINE] Ejecutando ExtractFeaturesFrom8bps sobre el video actual...")
    extractor = ExtractFeaturesFrom8bps(config_path=config_ini)
    extractor.files_found = [pose_csv_path]
    extractor.run()

    if roi_names:
        print("[ENGINE] Anexando ROI features nativas de SimBA...")
        roi_analyzer = ROIFeatureCreator(
            config_path=config_ini,
            body_parts=["Center"],
            data_path=pose_csv_path,
            append_data=True,
        )
        roi_analyzer.data_paths = [pose_csv_path]
        roi_analyzer.feature_file_paths = [feature_csv_path]
        roi_analyzer.run()
        roi_analyzer.save()


def run_feature_extraction(
    input_csv: str,
    output_csv: str,
    project_path: str,
    zonas_path: str | None = None,
    video_path: str | None = None,
    video_name: str | None = None,
) -> bool:
    input_csv = os.path.abspath(input_csv)
    output_csv = os.path.abspath(output_csv)
    project_path = os.path.abspath(project_path)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    derived_video_name = os.path.splitext(os.path.basename(input_csv))[0].replace("bridge_", "")
    if derived_video_name.endswith("_dlc"):
        derived_video_name = derived_video_name[:-4]
    video_name = (video_name or derived_video_name).strip()

    print(f"\n[ENGINE] Iniciando extraccion de caracteristicas SimBA para {video_name}...")

    try:
        zonas_list = _load_zonas_list(zonas_path)
        bridge_csv = _build_pose_bridge(
            input_csv=input_csv,
            output_dir=os.path.dirname(input_csv),
            video_name=video_name,
        )
    except Exception as error:
        print(f"[ENGINE] ERROR al construir bridge de pose: {error}")
        return False

    project_folder = os.path.join(project_path, "project_folder")
    config_ini = os.path.join(project_folder, "project_config.ini")
    simba_feat_dir = os.path.join(project_folder, "csv", "features_extracted")
    os.makedirs(simba_feat_dir, exist_ok=True)
    feature_csv_path = os.path.join(simba_feat_dir, f"{video_name}.csv")

    try:
        if zonas_list:
            roi_sync_result = sync_streamlit_rois_to_simba(
                project_folder=project_folder,
                video_name=video_name,
                zonas_list=zonas_list,
                video_path=video_path,
                include_model_aliases=True,
            )
            roi_names = roi_sync_result["canonical_roi_names"]
            print(
                f"[ENGINE] ROI SimBA reutilizadas desde Streamlit: "
                f"{roi_sync_result['saved_roi_names']}"
            )
        else:
            sync_video_to_simba_project(
                project_folder=project_folder,
                video_name=video_name,
                video_path=video_path,
            )
            roi_names = _get_existing_canonical_rois(project_folder, video_name)
            if roi_names:
                print(f"[ENGINE] ROIs existentes detectadas para {video_name}: {roi_names}")
            else:
                print("[ENGINE] Sin zonas nuevas ni ROIs previas para este video.")

        _, outlier_csv_path = _sync_pose_files(
            project_folder=project_folder,
            video_name=video_name,
            bridge_csv=bridge_csv,
        )

        _run_simba_extractors(
            config_ini=config_ini,
            pose_csv_path=outlier_csv_path,
            feature_csv_path=feature_csv_path,
            roi_names=roi_names,
        )

        if not os.path.exists(feature_csv_path):
            print(f"[ENGINE] ERROR: SimBA no genero el archivo esperado: {feature_csv_path}")
            return False

        df_features = pd.read_csv(feature_csv_path)
        df_features = _ensure_required_roi_columns(df_features)
        df_features.to_csv(feature_csv_path, index=False)
        df_features.to_csv(output_csv, index=False)
        print(f"[ENGINE] EXITO: metricas generadas en {output_csv}")
        return True
    except Exception as error:
        print(f"[ENGINE] ERROR FATAL: {error}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--zonas", required=False)
    parser.add_argument("--video", required=False)
    parser.add_argument("--video_name", required=False)
    args = parser.parse_args()

    ok = run_feature_extraction(
        input_csv=args.input,
        output_csv=args.output,
        project_path=args.project,
        zonas_path=args.zonas,
        video_path=args.video,
        video_name=args.video_name,
    )
    raise SystemExit(0 if ok else 1)
