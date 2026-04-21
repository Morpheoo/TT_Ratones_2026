import argparse
import os
import sys
from typing import Dict, Tuple

import cv2
import numpy as np
import pandas as pd

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

from src.scripts.render_dlc_keypoints_video import (
    SKELETON_EDGES,
    _build_bodypart_palette,
    _extract_bodyparts,
    _load_pose_dataframe,
    _resolve_column,
)
from src.config import YOLO_POSE_MODEL

# Usar el modelo YOLO11 pose para detección de bbox
# Los modelos de pose también generan bboxes de detección
YOLO_MODEL_PATH = str(YOLO_POSE_MODEL) if YOLO_POSE_MODEL.exists() else os.path.join(PROJECT_DIR, "yolo11n.pt")
DEFAULT_MARGIN = 30
DEFAULT_P_CUTOFF = 0.2
DEFAULT_DOT_RADIUS = 3
DEFAULT_CONFIDENCE = 0.25
DEFAULT_INFERRED_BBOX_EXTRA_MARGIN = 20
DEFAULT_ANTI_STICKING_FRAMES = 90
DEFAULT_CORRECTED_LIKELIHOOD = 0.25
DEFAULT_SAVGOL_WINDOW = 11
DEFAULT_SAVGOL_POLYORDER = 2
DEFAULT_MOVING_AVG_WINDOW = 7
DEFAULT_OCCLUSION_LIKELIHOOD = 0.3
DEFAULT_OCCLUSION_RADIUS_SCALE = 0.5
DEFAULT_TEMPORAL_VETO_WINDOW_RADIUS = 6
DEFAULT_TEMPORAL_VETO_BBOX_SCALE = 0.35
DEFAULT_SMOOTH_WINDOW = 21
DEFAULT_FINAL_MAX_BBOX_CENTER_DISTANCE_SCALE = 0.8
DEFAULT_MAX_PX_PER_FRAME = 18.0

ANTI_STICKING_BODYPARTS = {
    "nose",
    "snout",
    "left_ear",
    "ear_left",
    "right_ear",
    "ear_right",
    "mouse_center",
    "body_center",
    "center",
}

VETO_TIERS = {
    "hot": {
        "bodyparts": {
            "nose",
            "snout",
            "left_ear",
            "ear_left",
            "right_ear",
            "ear_right",
            "left_ear_tip",
            "ear_left_tip",
            "right_ear_tip",
            "ear_right_tip",
            "left_eye",
            "eye_left",
            "right_eye",
            "eye_right",
            "head_midpoint",
            "neck",
            "mouse_center",
            "body_center",
            "center",
        },
        "window_radius": 6,
        "bbox_scale": 0.25,
        "smooth_window": 21,
        "occlusion_radius_scale": 0.5,
        "max_px_per_frame": 12.0,
    },
    "warm": {
        "bodyparts": {
            "left_shoulder",
            "right_shoulder",
            "left_midside",
            "right_midside",
            "mid_back",
            "left_hip",
            "right_hip",
        },
        "window_radius": 6,
        "bbox_scale": 0.35,
        "smooth_window": 31,
        "occlusion_radius_scale": 0.5,
        "max_px_per_frame": 18.0,
    },
    "cold": {
        "bodyparts": {
            "tail_base",
            "tail1",
            "tail2",
            "tail3",
            "tail4",
            "tail5",
            "tail_end",
            "mid_backend",
            "mid_backend2",
            "mid_backend3",
        },
        "window_radius": 8,
        "bbox_scale": 0.20,
        "smooth_window": 13,
        "occlusion_radius_scale": 0.85,
        "max_px_per_frame": 25.0,
    },
}


def get_yolo_class():
    from ultralytics import YOLO

    return YOLO


def _build_column_cache(df_pose: pd.DataFrame, bodyparts: list[str]) -> dict[str, dict[str, object]]:
    cache: dict[str, dict[str, object]] = {}
    for bodypart in bodyparts:
        cache[bodypart] = {
            "x": _resolve_column(df_pose, bodypart, "x"),
            "y": _resolve_column(df_pose, bodypart, "y"),
            "likelihood": _resolve_column(df_pose, bodypart, "likelihood"),
        }
    return cache


def _bbox_with_margin(bbox: tuple[int, int, int, int], margin: int) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return float(x1 - margin), float(y1 - margin), float(x2 + margin), float(y2 + margin)


def _bbox_centroid(bbox_xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox_xyxy
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _clamp_point_to_box(
    x_coord: float,
    y_coord: float,
    bbox_xyxy: tuple[float, float, float, float],
) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox_xyxy
    return float(np.clip(x_coord, x1, x2)), float(np.clip(y_coord, y1, y2))


def _normalize_bodypart_name(bodypart: str) -> str:
    return bodypart.lower().replace(" ", "_").replace("-", "_")


def _is_anti_sticking_bodypart(bodypart: str) -> bool:
    normalized = _normalize_bodypart_name(bodypart)
    return normalized in ANTI_STICKING_BODYPARTS or normalized.endswith("_center")


NORMALIZED_VETO_TIERS = {
    tier_name: {
        "bodyparts": {_normalize_bodypart_name(bodypart) for bodypart in tier_config["bodyparts"]},
        "window_radius": int(tier_config["window_radius"]),
        "bbox_scale": float(tier_config["bbox_scale"]),
        "smooth_window": int(tier_config["smooth_window"]),
        "occlusion_radius_scale": float(tier_config["occlusion_radius_scale"]),
        "max_px_per_frame": float(tier_config["max_px_per_frame"]),
    }
    for tier_name, tier_config in VETO_TIERS.items()
}


def _get_temporal_veto_config(
    bodypart: str,
    default_window_radius: int,
    default_bbox_scale: float,
) -> tuple[str, int, float]:
    normalized = _normalize_bodypart_name(bodypart)
    for tier_name, tier_config in NORMALIZED_VETO_TIERS.items():
        if normalized in tier_config["bodyparts"]:
            return tier_name, tier_config["window_radius"], tier_config["bbox_scale"]
    return "default", default_window_radius, default_bbox_scale


def _point_inside_box(x_coord: float, y_coord: float, bbox_xyxy: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = bbox_xyxy
    return x1 <= x_coord <= x2 and y1 <= y_coord <= y2


def _get_temporal_smoothing_window(bodypart: str, default_window: int = DEFAULT_SMOOTH_WINDOW) -> int:
    normalized = _normalize_bodypart_name(bodypart)
    for tier_config in NORMALIZED_VETO_TIERS.values():
        if normalized in tier_config["bodyparts"]:
            return int(tier_config["smooth_window"])
    return int(default_window)


def _get_occlusion_radius_scale(bodypart: str, default_scale: float = DEFAULT_OCCLUSION_RADIUS_SCALE) -> float:
    normalized = _normalize_bodypart_name(bodypart)
    for tier_config in NORMALIZED_VETO_TIERS.values():
        if normalized in tier_config["bodyparts"]:
            return float(tier_config["occlusion_radius_scale"])
    return float(default_scale)


def _get_max_per_frame_displacement(bodypart: str, default_px: float = DEFAULT_MAX_PX_PER_FRAME) -> float:
    normalized = _normalize_bodypart_name(bodypart)
    for tier_config in NORMALIZED_VETO_TIERS.values():
        if normalized in tier_config["bodyparts"]:
            return float(tier_config["max_px_per_frame"])
    return float(default_px)


def _merge_count_dicts(*counts: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for count_dict in counts:
        for key, value in count_dict.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def _set_bodypart_point(
    df_pose: pd.DataFrame,
    row_idx: int,
    x_col,
    y_col,
    p_col,
    x_coord: float,
    y_coord: float,
    likelihood: float | None = None,
) -> None:
    df_pose.at[df_pose.index[row_idx], x_col] = float(x_coord)
    df_pose.at[df_pose.index[row_idx], y_col] = float(y_coord)
    if p_col is not None and likelihood is not None:
        df_pose.at[df_pose.index[row_idx], p_col] = float(np.clip(likelihood, 0.0, 1.0))


def _set_bodypart_nan(
    df_pose: pd.DataFrame,
    row_idx: int,
    x_col,
    y_col,
    p_col,
) -> None:
    df_pose.at[df_pose.index[row_idx], x_col] = np.nan
    df_pose.at[df_pose.index[row_idx], y_col] = np.nan
    if p_col is not None:
        df_pose.at[df_pose.index[row_idx], p_col] = np.nan


def _frame_bbox_with_policy(
    frame_idx: int,
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int],
    margin: int,
    inferred_bbox_extra_margin: int,
) -> tuple[float, float, float, float] | None:
    bbox = yolo_bboxes.get(frame_idx)
    if bbox is None:
        return None
    effective_margin = margin + (inferred_bbox_extra_margin if frame_idx in inferred_frames else 0)
    return _bbox_with_margin(bbox, effective_margin)


def _estimate_body_center(
    row: pd.Series,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    bbox_xyxy: tuple[float, float, float, float],
) -> tuple[float, float]:
    points: list[tuple[float, float]] = []
    for bodypart in bodyparts:
        x_col = column_cache[bodypart]["x"]
        y_col = column_cache[bodypart]["y"]
        if x_col is None or y_col is None:
            continue
        x_val = row.get(x_col)
        y_val = row.get(y_col)
        if pd.isna(x_val) or pd.isna(y_val):
            continue
        x_coord = float(x_val)
        y_coord = float(y_val)
        if _point_inside_box(x_coord, y_coord, bbox_xyxy):
            points.append((x_coord, y_coord))

    if points:
        xs = np.array([point[0] for point in points], dtype=float)
        ys = np.array([point[1] for point in points], dtype=float)
        return float(np.median(xs)), float(np.median(ys))

    x1, y1, x2, y2 = bbox_xyxy
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _hard_clamp_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int],
    corrected_counts: dict[int, int],
    margin: int,
    inferred_bbox_extra_margin: int,
    fill_missing: bool = True,
    max_bbox_center_distance_scale: float | None = None,
) -> None:
    for frame_idx in range(len(df_pose)):
        bbox_xyxy = _frame_bbox_with_policy(
            frame_idx=frame_idx,
            yolo_bboxes=yolo_bboxes,
            inferred_frames=inferred_frames,
            margin=margin,
            inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        )
        if bbox_xyxy is None:
            continue

        row = df_pose.iloc[frame_idx]
        bbox_center = _bbox_centroid(bbox_xyxy)
        x1, y1, x2, y2 = bbox_xyxy
        bbox_size = max(x2 - x1, y2 - y1, 1.0)

        for bodypart in bodyparts:
            x_col = column_cache[bodypart]["x"]
            y_col = column_cache[bodypart]["y"]
            p_col = column_cache[bodypart]["likelihood"]
            if x_col is None or y_col is None:
                continue

            x_val = row.get(x_col)
            y_val = row.get(y_col)
            p_val = row.get(p_col) if p_col is not None else 1.0
            corrected = False
            if pd.isna(x_val) or pd.isna(y_val):
                if not fill_missing:
                    continue
                x_coord, y_coord = bbox_center
                corrected = True
            else:
                x_coord = float(x_val)
                y_coord = float(y_val)
                if max_bbox_center_distance_scale is not None:
                    distance_to_bbox_center = float(np.hypot(x_coord - bbox_center[0], y_coord - bbox_center[1]))
                    if distance_to_bbox_center > bbox_size * max_bbox_center_distance_scale:
                        _set_bodypart_nan(df_pose, frame_idx, x_col, y_col, p_col)
                        corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                        continue
                clamped_x, clamped_y = _clamp_point_to_box(x_coord, y_coord, bbox_xyxy)
                corrected = (clamped_x != x_coord) or (clamped_y != y_coord)
                x_coord, y_coord = clamped_x, clamped_y

            if corrected:
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                likelihood = DEFAULT_CORRECTED_LIKELIHOOD if pd.isna(p_val) else max(float(p_val), DEFAULT_CORRECTED_LIKELIHOOD)
                _set_bodypart_point(df_pose, frame_idx, x_col, y_col, p_col, x_coord, y_coord, likelihood)


def _anti_sticking_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int],
    corrected_counts: dict[int, int],
    margin: int,
    inferred_bbox_extra_margin: int,
    anti_sticking_frames: int,
) -> None:
    last_points: dict[str, tuple[float, float]] = {}
    repeated_counts: dict[str, int] = {}

    for frame_idx in range(len(df_pose)):
        bbox_xyxy = _frame_bbox_with_policy(
            frame_idx=frame_idx,
            yolo_bboxes=yolo_bboxes,
            inferred_frames=inferred_frames,
            margin=margin,
            inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        )
        if bbox_xyxy is None:
            continue

        bbox_center = _bbox_centroid(bbox_xyxy)
        row = df_pose.iloc[frame_idx]

        for bodypart in bodyparts:
            if not _is_anti_sticking_bodypart(bodypart):
                continue

            x_col = column_cache[bodypart]["x"]
            y_col = column_cache[bodypart]["y"]
            p_col = column_cache[bodypart]["likelihood"]
            if x_col is None or y_col is None:
                continue

            x_val = row.get(x_col)
            y_val = row.get(y_col)
            if pd.isna(x_val) or pd.isna(y_val):
                last_points.pop(bodypart, None)
                repeated_counts[bodypart] = 0
                continue

            current_point = (float(x_val), float(y_val))
            previous_point = last_points.get(bodypart)
            if previous_point is not None and current_point == previous_point:
                repeated_counts[bodypart] = repeated_counts.get(bodypart, 1) + 1
            else:
                repeated_counts[bodypart] = 1

            if repeated_counts[bodypart] > anti_sticking_frames:
                likelihood = max(float(row.get(p_col, 0.0) or 0.0), DEFAULT_CORRECTED_LIKELIHOOD) if p_col is not None else None
                _set_bodypart_point(df_pose, frame_idx, x_col, y_col, p_col, bbox_center[0], bbox_center[1], likelihood)
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                current_point = bbox_center
                repeated_counts[bodypart] = 1

            last_points[bodypart] = current_point


def _mark_occlusions_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int],
    corrected_counts: dict[int, int],
    margin: int,
    inferred_bbox_extra_margin: int,
    occlusion_likelihood: float,
    occlusion_radius_scale: float,
) -> None:
    for frame_idx in range(len(df_pose)):
        bbox_xyxy = _frame_bbox_with_policy(
            frame_idx=frame_idx,
            yolo_bboxes=yolo_bboxes,
            inferred_frames=inferred_frames,
            margin=margin,
            inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        )
        if bbox_xyxy is None:
            continue

        row = df_pose.iloc[frame_idx]
        body_center = _estimate_body_center(row, bodyparts, column_cache, bbox_xyxy)

        for bodypart in bodyparts:
            x_col = column_cache[bodypart]["x"]
            y_col = column_cache[bodypart]["y"]
            p_col = column_cache[bodypart]["likelihood"]
            if x_col is None or y_col is None:
                continue

            x_val = row.get(x_col)
            y_val = row.get(y_col)
            if pd.isna(x_val) or pd.isna(y_val):
                continue

            p_val = row.get(p_col) if p_col is not None else 1.0
            low_likelihood = pd.isna(p_val) or float(p_val) < occlusion_likelihood
            x1, y1, x2, y2 = bbox_xyxy
            bbox_size = max(x2 - x1, y2 - y1, 1.0)
            max_body_radius = bbox_size * _get_occlusion_radius_scale(bodypart, occlusion_radius_scale)
            distance_to_center = float(np.hypot(float(x_val) - body_center[0], float(y_val) - body_center[1]))
            far_from_center = distance_to_center > max_body_radius

            if low_likelihood or far_from_center:
                _set_bodypart_nan(df_pose, frame_idx, x_col, y_col, p_col)
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1


def _max_per_frame_displacement_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    corrected_counts: dict[int, int],
) -> dict[str, int]:
    displacement_counts: dict[str, int] = {}

    for bodypart in bodyparts:
        x_col = column_cache[bodypart]["x"]
        y_col = column_cache[bodypart]["y"]
        p_col = column_cache[bodypart]["likelihood"]
        if x_col is None or y_col is None:
            continue

        max_px_per_frame = _get_max_per_frame_displacement(bodypart)
        previous_point: tuple[float, float] | None = None

        for frame_idx in range(len(df_pose)):
            row = df_pose.iloc[frame_idx]
            x_val = row.get(x_col)
            y_val = row.get(y_col)
            if pd.isna(x_val) or pd.isna(y_val):
                previous_point = None
                continue

            current_point = (float(x_val), float(y_val))
            if previous_point is None:
                previous_point = current_point
                continue

            dx = current_point[0] - previous_point[0]
            dy = current_point[1] - previous_point[1]
            distance = float(np.hypot(dx, dy))
            if distance > max_px_per_frame and distance > 0.0:
                scale = max_px_per_frame / distance
                clamped_point = (
                    previous_point[0] + dx * scale,
                    previous_point[1] + dy * scale,
                )
                likelihood = None
                if p_col is not None:
                    p_val = row.get(p_col)
                    if not pd.isna(p_val):
                        likelihood = float(p_val)
                _set_bodypart_point(
                    df_pose=df_pose,
                    row_idx=frame_idx,
                    x_col=x_col,
                    y_col=y_col,
                    p_col=p_col,
                    x_coord=clamped_point[0],
                    y_coord=clamped_point[1],
                    likelihood=likelihood,
                )
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                displacement_counts[bodypart] = displacement_counts.get(bodypart, 0) + 1
                current_point = clamped_point

            previous_point = current_point

    return displacement_counts


def _temporal_outlier_veto_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int],
    corrected_counts: dict[int, int],
    margin: int,
    inferred_bbox_extra_margin: int,
    default_window_radius: int,
    default_bbox_scale: float,
    bbox_scale_multiplier: float = 1.0,
) -> tuple[dict[str, int], dict[str, int]]:
    veto_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    bbox_sizes: list[float | None] = []
    bbox_fast_motion: set[int] = set()
    for frame_idx in range(len(df_pose)):
        bbox_xyxy = _frame_bbox_with_policy(
            frame_idx=frame_idx,
            yolo_bboxes=yolo_bboxes,
            inferred_frames=inferred_frames,
            margin=margin,
            inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        )
        if bbox_xyxy is None:
            bbox_sizes.append(None)
            continue
        x1, y1, x2, y2 = bbox_xyxy
        bbox_sizes.append(max(x2 - x1, y2 - y1, 1.0))

    for frame_idx in range(1, len(bbox_sizes)):
        bbox_size = bbox_sizes[frame_idx]
        if bbox_size is None or bbox_sizes[frame_idx - 1] is None:
            continue
        prev_bbox = yolo_bboxes.get(frame_idx - 1)
        curr_bbox = yolo_bboxes.get(frame_idx)
        if prev_bbox is None or curr_bbox is None:
            continue
        prev_cx = (prev_bbox[0] + prev_bbox[2]) / 2.0
        prev_cy = (prev_bbox[1] + prev_bbox[3]) / 2.0
        curr_cx = (curr_bbox[0] + curr_bbox[2]) / 2.0
        curr_cy = (curr_bbox[1] + curr_bbox[3]) / 2.0
        displacement = float(np.hypot(curr_cx - prev_cx, curr_cy - prev_cy))
        if displacement > float(bbox_size) * 0.15:
            for future_idx in range(frame_idx, min(frame_idx + 5, len(bbox_sizes))):
                bbox_fast_motion.add(future_idx)

    for bodypart in bodyparts:
        x_col = column_cache[bodypart]["x"]
        y_col = column_cache[bodypart]["y"]
        p_col = column_cache[bodypart]["likelihood"]
        if x_col is None or y_col is None:
            continue

        tier_name, window_radius, bbox_scale = _get_temporal_veto_config(
            bodypart=bodypart,
            default_window_radius=default_window_radius,
            default_bbox_scale=default_bbox_scale,
        )
        effective_bbox_scale = float(bbox_scale) * float(bbox_scale_multiplier)
        x_values = pd.to_numeric(df_pose[x_col], errors="coerce").to_numpy(dtype=float)
        y_values = pd.to_numeric(df_pose[y_col], errors="coerce").to_numpy(dtype=float)

        for frame_idx, bbox_size in enumerate(bbox_sizes):
            if bbox_size is None:
                continue

            if frame_idx in bbox_fast_motion:
                continue

            current_x = x_values[frame_idx]
            current_y = y_values[frame_idx]
            if np.isnan(current_x) or np.isnan(current_y):
                continue

            start_idx = max(0, frame_idx - window_radius)
            if frame_idx <= start_idx:
                continue

            history_x = x_values[start_idx:frame_idx]
            history_y = y_values[start_idx:frame_idx]
            valid_mask = ~(np.isnan(history_x) | np.isnan(history_y))
            if int(np.count_nonzero(valid_mask)) < 4:
                continue

            median_x = float(np.median(history_x[valid_mask]))
            median_y = float(np.median(history_y[valid_mask]))
            distance = float(np.hypot(current_x - median_x, current_y - median_y))
            veto_threshold = float(bbox_size) * effective_bbox_scale

            if distance > veto_threshold:
                _set_bodypart_nan(df_pose, frame_idx, x_col, y_col, p_col)
                x_values[frame_idx] = np.nan
                y_values[frame_idx] = np.nan
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                veto_counts[bodypart] = veto_counts.get(bodypart, 0) + 1
                tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1

    return veto_counts, tier_counts


def _smooth_numeric_segment(
    values: np.ndarray,
    use_savgol: bool,
    savgol_filter,
    savgol_window: int,
    savgol_polyorder: int,
    moving_avg_window: int,
) -> np.ndarray:
    if len(values) == 0:
        return values

    if use_savgol and len(values) >= savgol_window:
        window = savgol_window if savgol_window % 2 == 1 else savgol_window + 1
        window = min(window, len(values) if len(values) % 2 == 1 else len(values) - 1)
        if window >= 3 and window > savgol_polyorder and savgol_filter is not None:
            return savgol_filter(values, window_length=window, polyorder=savgol_polyorder, mode="interp")

    return (
        pd.Series(values)
        .rolling(window=moving_avg_window, min_periods=1, center=True)
        .mean()
        .to_numpy(dtype=float)
    )


def _temporal_smooth_pose(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
) -> None:
    for bodypart in bodyparts:
        smoothing_window = _get_temporal_smoothing_window(bodypart)
        if smoothing_window % 2 == 0:
            smoothing_window += 1
        for coord_name in ("x", "y"):
            column = column_cache[bodypart].get(coord_name)
            if column is None:
                continue

            series = pd.to_numeric(df_pose[column], errors="coerce").astype(float)
            if series.isna().all():
                continue

            smoothed = series.rolling(window=smoothing_window, center=True, min_periods=3).mean()
            smoothed[series.isna()] = np.nan
            df_pose[column] = smoothed.interpolate(method="linear", limit=3)


def extract_yolo_bboxes(
    video_path: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE,
    max_frames: int | None = None,
) -> tuple[Dict[int, Tuple[int, int, int, int]], set[int]]:
    print(f"[BBOX] Loading YOLO model: {YOLO_MODEL_PATH}")
    
    if not os.path.exists(YOLO_MODEL_PATH):
        raise FileNotFoundError(f"YOLO model not found: {YOLO_MODEL_PATH}")
    
    YOLO = get_yolo_class()
    print(f"[BBOX] Initializing model...")
    model = YOLO(YOLO_MODEL_PATH)
    print(f"[BBOX] Model loaded successfully")

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video for YOLO bbox extraction: {video_path}")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if max_frames is not None:
        total_frames = min(total_frames, max_frames)

    yolo_bboxes: Dict[int, Tuple[int, int, int, int]] = {}
    inferred_frames: set[int] = set()
    last_bbox: Tuple[int, int, int, int] | None = None
    frame_idx = 0

    print(f"[BBOX] Extracting YOLO boxes from: {video_path}")
    while frame_idx < total_frames:
        ok, frame = capture.read()
        if not ok:
            break

        results = model(frame, verbose=False)
        best_bbox = None
        best_conf = -1.0

        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf < confidence_threshold:
                continue
            if conf > best_conf:
                coords = tuple(int(round(value)) for value in box.xyxy[0].tolist())
                best_bbox = coords
                best_conf = conf

        if best_bbox is not None:
            last_bbox = best_bbox
            yolo_bboxes[frame_idx] = best_bbox
        elif last_bbox is not None:
            yolo_bboxes[frame_idx] = last_bbox
            inferred_frames.add(frame_idx)

        frame_idx += 1
        if frame_idx % 300 == 0 or frame_idx == total_frames:
            print(f"[BBOX] {frame_idx}/{total_frames}")

    capture.release()
    print(f"[BBOX] Completed. Boxes available for {len(yolo_bboxes)} frames.")
    return yolo_bboxes, inferred_frames


def apply_bbox_constraint(
    df_dlc: pd.DataFrame,
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int] | None = None,
    margin: int = DEFAULT_MARGIN,
    inferred_bbox_extra_margin: int = DEFAULT_INFERRED_BBOX_EXTRA_MARGIN,
    anti_sticking_frames: int = DEFAULT_ANTI_STICKING_FRAMES,
    occlusion_likelihood: float = DEFAULT_OCCLUSION_LIKELIHOOD,
    occlusion_radius_scale: float = DEFAULT_OCCLUSION_RADIUS_SCALE,
    temporal_veto_window_radius: int = DEFAULT_TEMPORAL_VETO_WINDOW_RADIUS,
    temporal_veto_bbox_scale: float = DEFAULT_TEMPORAL_VETO_BBOX_SCALE,
) -> pd.DataFrame:
    if not isinstance(df_dlc.columns, pd.MultiIndex) or df_dlc.columns.nlevels < 3:
        raise ValueError("Expected a DLC MultiIndex DataFrame (scorer/bodypart/coords).")

    df_corrected = df_dlc.copy()
    bodyparts = _extract_bodyparts(df_corrected)
    column_cache = _build_column_cache(df_corrected, bodyparts)
    corrected_counts: dict[int, int] = {}
    inferred_frames = inferred_frames or set()

    _hard_clamp_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        fill_missing=False,
    )
    _mark_occlusions_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        occlusion_likelihood=occlusion_likelihood,
        occlusion_radius_scale=occlusion_radius_scale,
    )
    veto_counts, veto_tier_counts = _temporal_outlier_veto_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        default_window_radius=temporal_veto_window_radius,
        default_bbox_scale=temporal_veto_bbox_scale,
    )
    _temporal_smooth_pose(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
    )
    displacement_counts = _max_per_frame_displacement_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        corrected_counts=corrected_counts,
    )
    veto_counts_pass2, veto_tier_counts_pass2 = _temporal_outlier_veto_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        default_window_radius=temporal_veto_window_radius,
        default_bbox_scale=temporal_veto_bbox_scale,
        bbox_scale_multiplier=1.5,
    )
    _anti_sticking_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        anti_sticking_frames=anti_sticking_frames,
    )
    _hard_clamp_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        corrected_counts=corrected_counts,
        margin=margin,
        inferred_bbox_extra_margin=inferred_bbox_extra_margin,
        fill_missing=False,
        max_bbox_center_distance_scale=DEFAULT_FINAL_MAX_BBOX_CENTER_DISTANCE_SCALE,
    )

    veto_counts = _merge_count_dicts(veto_counts, veto_counts_pass2)
    veto_tier_counts = _merge_count_dicts(veto_tier_counts, veto_tier_counts_pass2)
    df_corrected.attrs["bbox_constraint_counts"] = corrected_counts
    df_corrected.attrs["bbox_constraint_total"] = int(sum(corrected_counts.values()))
    df_corrected.attrs["temporal_outlier_veto_counts"] = veto_counts
    df_corrected.attrs["temporal_outlier_veto_total"] = int(sum(veto_counts.values()))
    df_corrected.attrs["temporal_outlier_veto_tier_counts"] = veto_tier_counts
    df_corrected.attrs["temporal_outlier_veto_pass1_total"] = int(sum(veto_counts.values()) - sum(veto_counts_pass2.values()))
    df_corrected.attrs["temporal_outlier_veto_pass2_total"] = int(sum(veto_counts_pass2.values()))
    df_corrected.attrs["max_per_frame_displacement_counts"] = displacement_counts
    df_corrected.attrs["max_per_frame_displacement_total"] = int(sum(displacement_counts.values()))
    return df_corrected


def _draw_dotted_line(
    frame: np.ndarray,
    start_point: tuple[int, int],
    end_point: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 2,
    dash_length: int = 10,
) -> None:
    x1, y1 = start_point
    x2, y2 = end_point
    distance = int(np.hypot(x2 - x1, y2 - y1))
    if distance == 0:
        return

    for start in range(0, distance, dash_length * 2):
        end = min(start + dash_length, distance)
        start_ratio = start / distance
        end_ratio = end / distance
        sx = int(x1 + (x2 - x1) * start_ratio)
        sy = int(y1 + (y2 - y1) * start_ratio)
        ex = int(x1 + (x2 - x1) * end_ratio)
        ey = int(y1 + (y2 - y1) * end_ratio)
        cv2.line(frame, (sx, sy), (ex, ey), color, thickness, lineType=cv2.LINE_AA)


def _draw_dotted_rectangle(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    color: tuple[int, int, int],
    thickness: int = 2,
) -> None:
    x1, y1, x2, y2 = bbox
    _draw_dotted_line(frame, (x1, y1), (x2, y1), color, thickness=thickness)
    _draw_dotted_line(frame, (x2, y1), (x2, y2), color, thickness=thickness)
    _draw_dotted_line(frame, (x2, y2), (x1, y2), color, thickness=thickness)
    _draw_dotted_line(frame, (x1, y2), (x1, y1), color, thickness=thickness)


def render_bbox_constraint_video(
    video_path: str,
    df_pose: pd.DataFrame,
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    inferred_frames: set[int] | None,
    output_path: str,
    margin: int = DEFAULT_MARGIN,
    inferred_bbox_extra_margin: int = DEFAULT_INFERRED_BBOX_EXTRA_MARGIN,
    pcutoff: float = DEFAULT_P_CUTOFF,
    dot_radius: int = DEFAULT_DOT_RADIUS,
) -> str:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video for render: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    total_frames = min(frame_count, len(df_pose)) if frame_count else len(df_pose)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not create output video: {output_path}")

    bodyparts = _extract_bodyparts(df_pose)
    column_cache = _build_column_cache(df_pose, bodyparts)
    palette = _build_bodypart_palette(bodyparts)
    corrected_counts = df_pose.attrs.get("bbox_constraint_counts", {})

    print(f"[RENDER] Rendering bbox-constrained video: {output_path}")
    frame_idx = 0
    while frame_idx < total_frames:
        ok, frame = capture.read()
        if not ok:
            break

        bbox = yolo_bboxes.get(frame_idx)
        if bbox is not None:
            _draw_dotted_rectangle(frame, bbox, color=(0, 255, 0), thickness=2)
            effective_margin = margin + (inferred_bbox_extra_margin if inferred_frames and frame_idx in inferred_frames else 0)
            if effective_margin > 0:
                x1, y1, x2, y2 = bbox
                margin_bbox = (
                    max(0, x1 - effective_margin),
                    max(0, y1 - effective_margin),
                    min(width - 1, x2 + effective_margin),
                    min(height - 1, y2 + effective_margin),
                )
                cv2.rectangle(frame, (margin_bbox[0], margin_bbox[1]), (margin_bbox[2], margin_bbox[3]), (0, 120, 0), 1)

        row = df_pose.iloc[frame_idx]
        points: dict[str, tuple[int, int]] = {}
        for bodypart in bodyparts:
            x_col = column_cache[bodypart]["x"]
            y_col = column_cache[bodypart]["y"]
            p_col = column_cache[bodypart]["likelihood"]
            if x_col is None or y_col is None:
                continue

            x_val = row.get(x_col)
            y_val = row.get(y_col)
            p_val = row.get(p_col) if p_col is not None else 1.0
            if pd.isna(x_val) or pd.isna(y_val) or pd.isna(p_val) or float(p_val) < pcutoff:
                continue

            x_coord = int(round(float(x_val)))
            y_coord = int(round(float(y_val)))
            if x_coord < 0 or x_coord >= width or y_coord < 0 or y_coord >= height:
                continue

            color = palette[bodypart]
            points[bodypart] = (x_coord, y_coord)
            cv2.circle(frame, (x_coord, y_coord), dot_radius, color, -1, lineType=cv2.LINE_AA)

        for start_bp, end_bp in SKELETON_EDGES:
            if start_bp not in points or end_bp not in points:
                continue
            cv2.line(frame, points[start_bp], points[end_bp], palette.get(start_bp, (255, 255, 255)), 1, lineType=cv2.LINE_AA)

        corrected_this_frame = int(corrected_counts.get(frame_idx, 0))
        cv2.putText(frame, "BBox Constraint ON", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, lineType=cv2.LINE_AA)
        cv2.putText(
            frame,
            f"Corrected keypoints: {corrected_this_frame}",
            (16, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            lineType=cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"frame {frame_idx + 1}/{total_frames}",
            (16, 84),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            lineType=cv2.LINE_AA,
        )

        writer.write(frame)
        frame_idx += 1
        if frame_idx % 300 == 0 or frame_idx == total_frames:
            print(f"[RENDER] {frame_idx}/{total_frames}")

    capture.release()
    writer.release()
    print(f"[RENDER] Completed bbox-constrained render: {output_path}")
    return output_path


def save_pose_dataframe(df_pose: pd.DataFrame, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".h5":
        df_pose.to_hdf(output_path, key="df", mode="w")
    elif ext == ".csv":
        df_pose.to_csv(output_path)
    else:
        raise ValueError(f"Unsupported pose output format: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a YOLO bbox constraint to DLC keypoints and render a validation video.")
    parser.add_argument("--video", required=True, help="Path to the analyzed video.")
    parser.add_argument("--pose", required=True, help="Path to the DLC H5/CSV pose file.")
    parser.add_argument("--output_pose", required=True, help="Path to save the corrected DLC pose file.")
    parser.add_argument("--output_video", required=True, help="Path to save the bbox-constrained overlay video.")
    parser.add_argument("--output_csv", default="", help="Optional path to also save the corrected pose as CSV.")
    parser.add_argument("--margin", type=int, default=DEFAULT_MARGIN, help="Extra padding around the YOLO bbox.")
    parser.add_argument(
        "--inferred_bbox_extra_margin",
        type=int,
        default=DEFAULT_INFERRED_BBOX_EXTRA_MARGIN,
        help="Extra padding when YOLO is missing and the last known bbox is reused.",
    )
    parser.add_argument("--pcutoff", type=float, default=DEFAULT_P_CUTOFF, help="Minimum likelihood to draw a keypoint in the render.")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE, help="Minimum YOLO confidence to accept a bbox.")
    parser.add_argument(
        "--anti_sticking_frames",
        type=int,
        default=DEFAULT_ANTI_STICKING_FRAMES,
        help="If a sensitive keypoint stays exactly in the same position longer than this, replace it with the bbox centroid.",
    )
    parser.add_argument(
        "--occlusion_likelihood",
        type=float,
        default=DEFAULT_OCCLUSION_LIKELIHOOD,
        help="Likelihood threshold below which a keypoint is treated as occluded before smoothing.",
    )
    parser.add_argument(
        "--occlusion_radius_scale",
        type=float,
        default=DEFAULT_OCCLUSION_RADIUS_SCALE,
        help="If a keypoint is farther than this fraction of bbox size from body center, mark it as occluded before smoothing.",
    )
    parser.add_argument(
        "--temporal_veto_window_radius",
        type=int,
        default=DEFAULT_TEMPORAL_VETO_WINDOW_RADIUS,
        help="Temporal window radius for median-based local outlier veto.",
    )
    parser.add_argument(
        "--temporal_veto_bbox_scale",
        type=float,
        default=DEFAULT_TEMPORAL_VETO_BBOX_SCALE,
        help="If a head/face keypoint deviates more than this fraction of bbox size from local median, mark it as NaN.",
    )
    parser.add_argument("--max_frames", type=int, default=0, help="Optional limit for debugging short runs.")
    args = parser.parse_args()

    max_frames = args.max_frames if args.max_frames > 0 else None
    df_pose = _load_pose_dataframe(os.path.abspath(args.pose))
    yolo_bboxes, inferred_frames = extract_yolo_bboxes(
        video_path=os.path.abspath(args.video),
        confidence_threshold=args.confidence,
        max_frames=max_frames,
    )
    if max_frames is not None:
        df_pose = df_pose.iloc[:max_frames].copy()

    df_corrected = apply_bbox_constraint(
        df_dlc=df_pose,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        margin=args.margin,
        inferred_bbox_extra_margin=args.inferred_bbox_extra_margin,
        anti_sticking_frames=args.anti_sticking_frames,
        occlusion_likelihood=args.occlusion_likelihood,
        occlusion_radius_scale=args.occlusion_radius_scale,
        temporal_veto_window_radius=args.temporal_veto_window_radius,
        temporal_veto_bbox_scale=args.temporal_veto_bbox_scale,
    )
    print(f"[BBOX] Total corrected keypoints: {df_corrected.attrs.get('bbox_constraint_total', 0)}")
    print(f"[BBOX] Temporal veto total: {df_corrected.attrs.get('temporal_outlier_veto_total', 0)}")
    print(f"[BBOX] Temporal veto pass 1: {df_corrected.attrs.get('temporal_outlier_veto_pass1_total', 0)}")
    print(f"[BBOX] Temporal veto pass 2: {df_corrected.attrs.get('temporal_outlier_veto_pass2_total', 0)}")
    print(f"[BBOX] Max per-frame displacement total: {df_corrected.attrs.get('max_per_frame_displacement_total', 0)}")
    veto_tier_counts = df_corrected.attrs.get("temporal_outlier_veto_tier_counts", {})
    if veto_tier_counts:
        print("[BBOX] Temporal veto by tier:")
        for tier_name, count in sorted(veto_tier_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"  - {tier_name}: {count}")
    veto_counts = df_corrected.attrs.get("temporal_outlier_veto_counts", {})
    if veto_counts:
        print("[BBOX] Temporal veto by keypoint:")
        for bodypart, count in sorted(veto_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"  - {bodypart}: {count}")
    displacement_counts = df_corrected.attrs.get("max_per_frame_displacement_counts", {})
    if displacement_counts:
        print("[BBOX] Max per-frame displacement by keypoint:")
        for bodypart, count in sorted(displacement_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"  - {bodypart}: {count}")

    save_pose_dataframe(df_corrected, os.path.abspath(args.output_pose))
    if args.output_csv:
        save_pose_dataframe(df_corrected, os.path.abspath(args.output_csv))

    render_bbox_constraint_video(
        video_path=os.path.abspath(args.video),
        df_pose=df_corrected,
        yolo_bboxes=yolo_bboxes,
        inferred_frames=inferred_frames,
        output_path=os.path.abspath(args.output_video),
        margin=args.margin,
        inferred_bbox_extra_margin=args.inferred_bbox_extra_margin,
        pcutoff=args.pcutoff,
    )


if __name__ == "__main__":
    main()
