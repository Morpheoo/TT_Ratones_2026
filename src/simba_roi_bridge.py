import os
import shutil
from datetime import datetime
from typing import Any

import cv2
import pandas as pd

RECTANGLE_HEADERS = [
    "Video",
    "Shape_type",
    "Name",
    "Color name",
    "Color BGR",
    "Thickness",
    "Center_X",
    "Center_Y",
    "topLeftX",
    "topLeftY",
    "Bottom_right_X",
    "Bottom_right_Y",
    "width",
    "height",
    "width_cm",
    "height_cm",
    "area_cm",
    "Tags",
    "Ear_tag_size",
]
CIRCLE_HEADERS = [
    "Video",
    "Shape_type",
    "Name",
    "Color name",
    "Color BGR",
    "Thickness",
    "centerX",
    "centerY",
    "radius",
    "radius_cm",
    "area_cm",
    "Tags",
    "Ear_tag_size",
]
POLYGON_HEADERS = [
    "Video",
    "Shape_type",
    "Name",
    "Color name",
    "Color BGR",
    "Thickness",
    "Center_X",
    "Center_Y",
    "vertices",
    "center",
    "area",
    "max_vertice_distance",
    "area_cm",
    "Tags",
    "Ear_tag_size",
]

MODEL_ROI_STYLE = {
    "pared1": ("coral", (120, 120, 240)),
    "pared2": ("coral", (120, 120, 240)),
    "pared3": ("cyan", (255, 250, 0)),
    "pared4": ("cyan", (255, 250, 0)),
    "pared5": ("orange", (0, 165, 255)),
    "pared6": ("yellow", (0, 255, 255)),
}

USER_ZONE_STYLE = {
    "Brazo Abierto": ("coral", (120, 120, 240)),
    "Brazo Cerrado": ("blue", (255, 0, 0)),
    "Centro": ("orange", (0, 165, 255)),
    "Muro / Pared": ("cyan", (255, 255, 0)),
}


def _extract_numeric_suffix(label: str) -> int:
    digits = "".join(character for character in label if character.isdigit())
    return int(digits) if digits else 999


def _normalize_zone_label(zone_data: dict[str, Any]) -> str:
    return str(
        zone_data.get("id")
        or zone_data.get("name")
        or zone_data.get("Nombre Zona")
        or "Zona"
    ).strip()


def _infer_style(name: str) -> tuple[str, tuple[int, int, int]]:
    for key, value in USER_ZONE_STYLE.items():
        if key.lower() in name.lower():
            return value
    if "abierto" in name.lower():
        return USER_ZONE_STYLE["Brazo Abierto"]
    if "cerrado" in name.lower():
        return USER_ZONE_STYLE["Brazo Cerrado"]
    if "centro" in name.lower():
        return USER_ZONE_STYLE["Centro"]
    if "pared" in name.lower() or "muro" in name.lower():
        return USER_ZONE_STYLE["Muro / Pared"]
    return ("gray", (150, 150, 150))


def _infer_project_calibration(video_info_df: pd.DataFrame) -> tuple[float, float]:
    if video_info_df.empty:
        return 400.0, 2.5

    pixels_series = pd.to_numeric(video_info_df.get("pixels/mm"), errors="coerce").dropna()
    distance_series = pd.to_numeric(video_info_df.get("Distance_in_mm"), errors="coerce").dropna()

    stable_pixels = pixels_series[pixels_series > 1.05]
    stable_distance = distance_series[distance_series > 0]

    pixels_per_mm = float(stable_pixels.median()) if not stable_pixels.empty else 2.5
    distance_in_mm = float(stable_distance.median()) if not stable_distance.empty else 400.0
    return distance_in_mm, pixels_per_mm


def _read_video_metadata(video_path: str | None) -> tuple[float, int, int, str]:
    if not video_path or not os.path.exists(video_path):
        return 30.0, 1280, 720, ".mp4"

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        return 30.0, 1280, 720, os.path.splitext(video_path)[1] or ".mp4"

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    capture.release()
    return fps, width, height, os.path.splitext(video_path)[1] or ".mp4"


def sync_video_to_simba_project(project_folder: str, video_name: str, video_path: str | None) -> tuple[float, float]:
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
            rectangles_df = pd.read_hdf(roi_path, key="rectangles")
        if "/circleDf" in keys:
            circles_df = pd.read_hdf(roi_path, key="circleDf")
        if "/polygons" in keys:
            polygon_df = pd.read_hdf(roi_path, key="polygons")
    except Exception:
        invalid_store = True

    if invalid_store:
        _backup_corrupt_roi_file(roi_path)
        return _empty_roi_frames()

    return (
        rectangles_df.reindex(columns=RECTANGLE_HEADERS),
        circles_df.reindex(columns=CIRCLE_HEADERS),
        polygon_df.reindex(columns=POLYGON_HEADERS),
    )


def _create_rectangle_entry(
    video_name: str,
    roi_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    pixels_per_mm: float,
    color_name: str,
    color_bgr: tuple[int, int, int],
) -> dict[str, Any]:
    bottom_right_x = x + width
    bottom_right_y = y + height
    center_x = x + round(width / 2)
    center_y = y + round(height / 2)
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


def _create_rectangle_from_zone(
    video_name: str,
    roi_name: str,
    zone_data: dict[str, Any],
    pixels_per_mm: float,
    color_override: tuple[str, tuple[int, int, int]] | None = None,
) -> dict[str, Any]:
    x = int(zone_data.get("x", zone_data.get("left", 0)))
    y = int(zone_data.get("y", zone_data.get("top", 0)))
    width = int(zone_data.get("w", zone_data.get("width", 0)))
    height = int(zone_data.get("h", zone_data.get("height", 0)))
    color_name, color_bgr = color_override or _infer_style(roi_name)
    return _create_rectangle_entry(video_name, roi_name, x, y, width, height, pixels_per_mm, color_name, color_bgr)


def _create_rectangle_from_line(
    video_name: str,
    roi_name: str,
    zone_data: dict[str, Any],
    pixels_per_mm: float,
    thickness: int = 8,
) -> dict[str, Any]:
    x1 = int(zone_data.get("x1", 0))
    y1 = int(zone_data.get("y1", 0))
    x2 = int(zone_data.get("x2", 0))
    y2 = int(zone_data.get("y2", 0))
    left = min(x1, x2)
    top = min(y1, y2)
    width = max(abs(x2 - x1), 1)
    height = max(abs(y2 - y1), 1)
    if width < thickness:
        left -= thickness // 2
        width = thickness
    if height < thickness:
        top -= thickness // 2
        height = thickness
    color_name, color_bgr = _infer_style(roi_name)
    return _create_rectangle_entry(video_name, roi_name, left, top, width, height, pixels_per_mm, color_name, color_bgr)


def _collect_rectangular_zones(zonas_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rectangles: list[dict[str, Any]] = []
    for zone in zonas_list:
        if str(zone.get("type", "rect")).lower() == "line":
            continue
        x = zone.get("x", zone.get("left"))
        y = zone.get("y", zone.get("top"))
        width = zone.get("w", zone.get("width"))
        height = zone.get("h", zone.get("height"))
        if None in (x, y, width, height):
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


def _collect_wall_line_zones(zonas_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    line_zones: list[dict[str, Any]] = []
    for zone in zonas_list:
        zone_type = str(zone.get("type", "rect")).lower()
        zone_label = _normalize_zone_label(zone)
        zone_label_lower = zone_label.lower()
        if zone_type != "line":
            continue
        if "pared" not in zone_label_lower and "muro" not in zone_label_lower and "wall" not in zone_label_lower:
            continue
        line_zones.append(
            {
                "label": zone_label,
                "label_lower": zone_label_lower,
                "x1": int(zone.get("x1", 0)),
                "y1": int(zone.get("y1", 0)),
                "x2": int(zone.get("x2", 0)),
                "y2": int(zone.get("y2", 0)),
            }
        )
    return line_zones


def _map_zones_to_model_rois(zonas_list: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    wall_lines = _collect_wall_line_zones(zonas_list)
    sort_key = lambda item: (_extract_numeric_suffix(item["label"]), item["label_lower"])
    wall_lines = sorted(wall_lines, key=sort_key)
    if wall_lines:
        roi_map: dict[str, dict[str, Any]] = {}
        for index, wall_zone in enumerate(wall_lines[:6], start=1):
            roi_map[f"pared{index}"] = {
                "type": "line",
                "name": wall_zone["label"],
                "x1": wall_zone["x1"],
                "y1": wall_zone["y1"],
                "x2": wall_zone["x2"],
                "y2": wall_zone["y2"],
            }
        return roi_map

    rectangles = _collect_rectangular_zones(zonas_list)
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

    roi_map: dict[str, dict[str, Any]] = {}
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


def sync_streamlit_rois_to_simba(
    project_folder: str,
    video_name: str,
    zonas_list: list[dict[str, Any]],
    video_path: str | None = None,
    include_model_aliases: bool = True,
    include_user_zones: bool = False,
) -> dict[str, Any]:
    _, pixels_per_mm = sync_video_to_simba_project(project_folder, video_name, video_path)

    roi_dir = os.path.join(project_folder, "logs", "measures")
    os.makedirs(roi_dir, exist_ok=True)
    roi_path = os.path.join(roi_dir, "ROI_definitions.h5")

    rectangles_df, circles_df, polygon_df = _load_existing_roi_frames(roi_path)
    rectangles_df = rectangles_df[rectangles_df["Video"] != video_name].reset_index(drop=True)
    circles_df = circles_df[circles_df["Video"] != video_name].reset_index(drop=True)
    polygon_df = polygon_df[polygon_df["Video"] != video_name].reset_index(drop=True)

    new_rectangles: list[dict[str, Any]] = []
    user_roi_names: list[str] = []
    seen_roi_names: set[str] = set()
    for zone in zonas_list:
        zone_name = _normalize_zone_label(zone)
        if not zone_name:
            continue
        user_roi_names.append(zone_name)
        if not include_user_zones:
            continue
        if zone_name in seen_roi_names:
            continue
        seen_roi_names.add(zone_name)
        if str(zone.get("type", "rect")).lower() == "line":
            new_rectangles.append(
                _create_rectangle_from_line(video_name, zone_name, zone, pixels_per_mm)
            )
        else:
            new_rectangles.append(
                _create_rectangle_from_zone(video_name, zone_name, zone, pixels_per_mm)
            )

    canonical_roi_names: list[str] = []
    if include_model_aliases:
        roi_map = _map_zones_to_model_rois(zonas_list)
        for roi_name, zone_data in roi_map.items():
            if roi_name in seen_roi_names:
                continue
            seen_roi_names.add(roi_name)
            if str(zone_data.get("type", "rect")).lower() == "line":
                new_rectangles.append(
                    _create_rectangle_from_line(
                        video_name,
                        roi_name,
                        zone_data,
                        pixels_per_mm,
                    )
                )
                new_rectangles[-1]["Color name"] = MODEL_ROI_STYLE[roi_name][0]
                new_rectangles[-1]["Color BGR"] = MODEL_ROI_STYLE[roi_name][1]
            else:
                new_rectangles.append(
                    _create_rectangle_from_zone(
                        video_name,
                        roi_name,
                        zone_data,
                        pixels_per_mm,
                        color_override=MODEL_ROI_STYLE[roi_name],
                    )
                )
        canonical_roi_names = list(roi_map.keys())

    if new_rectangles:
        rectangles_df = pd.concat(
            [rectangles_df, pd.DataFrame(new_rectangles, columns=RECTANGLE_HEADERS)],
            ignore_index=True,
        )

    with pd.HDFStore(roi_path, mode="w") as store:
        store["rectangles"] = rectangles_df.reindex(columns=RECTANGLE_HEADERS)
        store["circleDf"] = circles_df.reindex(columns=CIRCLE_HEADERS)
        store["polygons"] = polygon_df.reindex(columns=POLYGON_HEADERS)

    return {
        "roi_path": roi_path,
        "user_roi_names": user_roi_names,
        "canonical_roi_names": canonical_roi_names,
        "saved_roi_names": [entry["Name"] for entry in new_rectangles],
    }
