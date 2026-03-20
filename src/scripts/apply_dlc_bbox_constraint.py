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

YOLO_MODEL_PATH = os.path.join(PROJECT_DIR, "yolo_tracker.pt")
DEFAULT_MARGIN = 30
DEFAULT_P_CUTOFF = 0.2
DEFAULT_DOT_RADIUS = 3
DEFAULT_CONFIDENCE = 0.25
DEFAULT_MAX_JUMP_SCALE = 0.45
DEFAULT_MAX_RADIUS_SCALE = 0.65
DEFAULT_MIN_JUMP_PX = 35.0
DEFAULT_MIN_RADIUS_PX = 45.0


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


def _point_inside_box(x_coord: float, y_coord: float, bbox_xyxy: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = bbox_xyxy
    return x1 <= x_coord <= x2 and y1 <= y_coord <= y2


def _invalidate_bodypart(
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


def _interpolate_pose(df_pose: pd.DataFrame, bodyparts: list[str], column_cache: dict[str, dict[str, object]]) -> None:
    for bodypart in bodyparts:
        for coord_name in ("x", "y", "likelihood"):
            column = column_cache[bodypart].get(coord_name)
            if column is None:
                continue
            series = pd.to_numeric(df_pose[column], errors="coerce")
            series = series.interpolate(method="linear", limit_direction="both")
            if coord_name == "likelihood":
                series = series.clip(lower=0.0, upper=1.0)
            df_pose[column] = series


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


def _spatial_cleanup_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    corrected_counts: dict[int, int],
    margin: int,
    max_jump_scale: float,
    max_radius_scale: float,
) -> None:
    previous_valid_points: dict[str, tuple[float, float]] = {}

    for frame_idx in range(len(df_pose)):
        bbox = yolo_bboxes.get(frame_idx)
        if bbox is None:
            continue

        bbox_xyxy = _bbox_with_margin(bbox, margin)
        x1, y1, x2, y2 = bbox_xyxy
        bbox_size = max(x2 - x1, y2 - y1, 1.0)
        max_jump_px = max(DEFAULT_MIN_JUMP_PX, bbox_size * max_jump_scale)
        max_radius_px = max(DEFAULT_MIN_RADIUS_PX, bbox_size * max_radius_scale)

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

            x_coord = float(x_val)
            y_coord = float(y_val)
            valid = _point_inside_box(x_coord, y_coord, bbox_xyxy)
            if valid:
                distance_to_center = float(np.hypot(x_coord - body_center[0], y_coord - body_center[1]))
                valid = distance_to_center <= max_radius_px

            if valid and bodypart in previous_valid_points:
                prev_x, prev_y = previous_valid_points[bodypart]
                jump_distance = float(np.hypot(x_coord - prev_x, y_coord - prev_y))
                valid = jump_distance <= max_jump_px

            if valid:
                previous_valid_points[bodypart] = (x_coord, y_coord)
                continue

            _invalidate_bodypart(df_pose, frame_idx, x_col, y_col, p_col)
            corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1


def _final_snap_pass(
    df_pose: pd.DataFrame,
    bodyparts: list[str],
    column_cache: dict[str, dict[str, object]],
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    corrected_counts: dict[int, int],
    margin: int,
    max_radius_scale: float,
) -> None:
    previous_valid_points: dict[str, tuple[float, float]] = {}

    for frame_idx in range(len(df_pose)):
        bbox = yolo_bboxes.get(frame_idx)
        if bbox is None:
            continue

        bbox_xyxy = _bbox_with_margin(bbox, margin)
        x1, y1, x2, y2 = bbox_xyxy
        bbox_size = max(x2 - x1, y2 - y1, 1.0)
        max_radius_px = max(DEFAULT_MIN_RADIUS_PX, bbox_size * max_radius_scale)

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
                replacement = previous_valid_points.get(bodypart, body_center)
                df_pose.at[df_pose.index[frame_idx], x_col] = replacement[0]
                df_pose.at[df_pose.index[frame_idx], y_col] = replacement[1]
                if p_col is not None:
                    df_pose.at[df_pose.index[frame_idx], p_col] = max(float(row.get(p_col, 0.0) or 0.0), 0.25)
                corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1
                continue

            x_coord = float(x_val)
            y_coord = float(y_val)
            distance_to_center = float(np.hypot(x_coord - body_center[0], y_coord - body_center[1]))
            valid = _point_inside_box(x_coord, y_coord, bbox_xyxy) and distance_to_center <= max_radius_px

            if valid:
                previous_valid_points[bodypart] = (x_coord, y_coord)
                continue

            replacement = previous_valid_points.get(bodypart, body_center)
            df_pose.at[df_pose.index[frame_idx], x_col] = replacement[0]
            df_pose.at[df_pose.index[frame_idx], y_col] = replacement[1]
            if p_col is not None:
                df_pose.at[df_pose.index[frame_idx], p_col] = max(float(row.get(p_col, 0.0) or 0.0), 0.25)
            corrected_counts[frame_idx] = corrected_counts.get(frame_idx, 0) + 1


def extract_yolo_bboxes(
    video_path: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE,
    max_frames: int | None = None,
) -> Dict[int, Tuple[int, int, int, int]]:
    YOLO = get_yolo_class()
    model = YOLO(YOLO_MODEL_PATH)

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video for YOLO bbox extraction: {video_path}")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if max_frames is not None:
        total_frames = min(total_frames, max_frames)

    yolo_bboxes: Dict[int, Tuple[int, int, int, int]] = {}
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

        frame_idx += 1
        if frame_idx % 300 == 0 or frame_idx == total_frames:
            print(f"[BBOX] {frame_idx}/{total_frames}")

    capture.release()
    print(f"[BBOX] Completed. Boxes available for {len(yolo_bboxes)} frames.")
    return yolo_bboxes


def apply_bbox_constraint(
    df_dlc: pd.DataFrame,
    yolo_bboxes: Dict[int, Tuple[int, int, int, int]],
    margin: int = DEFAULT_MARGIN,
    max_jump_scale: float = DEFAULT_MAX_JUMP_SCALE,
    max_radius_scale: float = DEFAULT_MAX_RADIUS_SCALE,
) -> pd.DataFrame:
    if not isinstance(df_dlc.columns, pd.MultiIndex) or df_dlc.columns.nlevels < 3:
        raise ValueError("Expected a DLC MultiIndex DataFrame (scorer/bodypart/coords).")

    df_corrected = df_dlc.copy()
    bodyparts = _extract_bodyparts(df_corrected)
    column_cache = _build_column_cache(df_corrected, bodyparts)
    corrected_counts: dict[int, int] = {}

    for frame_idx in range(len(df_corrected)):
        bbox = yolo_bboxes.get(frame_idx)
        if bbox is None:
            corrected_counts[frame_idx] = 0
            continue

        bbox_xyxy = _bbox_with_margin(bbox, margin)
        corrected_this_frame = 0
        row = df_corrected.iloc[frame_idx]

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

            x_coord = float(x_val)
            y_coord = float(y_val)
            inside_bbox = _point_inside_box(x_coord, y_coord, bbox_xyxy)
            if inside_bbox:
                continue

            _invalidate_bodypart(df_corrected, frame_idx, x_col, y_col, p_col)
            corrected_this_frame += 1

        corrected_counts[frame_idx] = corrected_this_frame

    _interpolate_pose(df_corrected, bodyparts, column_cache)
    _spatial_cleanup_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        corrected_counts=corrected_counts,
        margin=margin,
        max_jump_scale=max_jump_scale,
        max_radius_scale=max_radius_scale,
    )
    _interpolate_pose(df_corrected, bodyparts, column_cache)
    _final_snap_pass(
        df_pose=df_corrected,
        bodyparts=bodyparts,
        column_cache=column_cache,
        yolo_bboxes=yolo_bboxes,
        corrected_counts=corrected_counts,
        margin=margin,
        max_radius_scale=max_radius_scale,
    )

    df_corrected.attrs["bbox_constraint_counts"] = corrected_counts
    df_corrected.attrs["bbox_constraint_total"] = int(sum(corrected_counts.values()))
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
    output_path: str,
    margin: int = DEFAULT_MARGIN,
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
            if margin > 0:
                x1, y1, x2, y2 = bbox
                margin_bbox = (
                    max(0, x1 - margin),
                    max(0, y1 - margin),
                    min(width - 1, x2 + margin),
                    min(height - 1, y2 + margin),
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
    parser.add_argument("--pcutoff", type=float, default=DEFAULT_P_CUTOFF, help="Minimum likelihood to draw a keypoint in the render.")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE, help="Minimum YOLO confidence to accept a bbox.")
    parser.add_argument("--max_jump_scale", type=float, default=DEFAULT_MAX_JUMP_SCALE, help="Max frame-to-frame jump as a fraction of bbox size.")
    parser.add_argument("--max_radius_scale", type=float, default=DEFAULT_MAX_RADIUS_SCALE, help="Max distance from body center as a fraction of bbox size.")
    parser.add_argument("--max_frames", type=int, default=0, help="Optional limit for debugging short runs.")
    args = parser.parse_args()

    max_frames = args.max_frames if args.max_frames > 0 else None
    df_pose = _load_pose_dataframe(os.path.abspath(args.pose))
    yolo_bboxes = extract_yolo_bboxes(
        video_path=os.path.abspath(args.video),
        confidence_threshold=args.confidence,
        max_frames=max_frames,
    )
    if max_frames is not None:
        df_pose = df_pose.iloc[:max_frames].copy()

    df_corrected = apply_bbox_constraint(
        df_dlc=df_pose,
        yolo_bboxes=yolo_bboxes,
        margin=args.margin,
        max_jump_scale=args.max_jump_scale,
        max_radius_scale=args.max_radius_scale,
    )
    print(f"[BBOX] Total corrected keypoints: {df_corrected.attrs.get('bbox_constraint_total', 0)}")

    save_pose_dataframe(df_corrected, os.path.abspath(args.output_pose))
    if args.output_csv:
        save_pose_dataframe(df_corrected, os.path.abspath(args.output_csv))

    render_bbox_constraint_video(
        video_path=os.path.abspath(args.video),
        df_pose=df_corrected,
        yolo_bboxes=yolo_bboxes,
        output_path=os.path.abspath(args.output_video),
        margin=args.margin,
        pcutoff=args.pcutoff,
    )


if __name__ == "__main__":
    main()
