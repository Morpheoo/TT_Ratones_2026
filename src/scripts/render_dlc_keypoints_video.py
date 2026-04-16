import argparse
import glob
import os
import subprocess

import cv2
import numpy as np
import pandas as pd

DEFAULT_P_CUTOFF = 0.2
DEFAULT_DOT_RADIUS = 3

SKELETON_EDGES = [
    ("nose", "head_midpoint"),
    ("head_midpoint", "left_ear"),
    ("head_midpoint", "right_ear"),
    ("head_midpoint", "left_eye"),
    ("head_midpoint", "right_eye"),
    ("head_midpoint", "neck"),
    ("neck", "mouse_center"),
    ("mouse_center", "mid_back"),
    ("mid_back", "mid_backend"),
    ("mid_backend", "mid_backend2"),
    ("mid_backend2", "mid_backend3"),
    ("mid_backend3", "tail_base"),
    ("tail_base", "tail1"),
    ("tail1", "tail2"),
    ("tail2", "tail3"),
    ("tail3", "tail4"),
    ("tail4", "tail5"),
    ("tail5", "tail_end"),
    ("mouse_center", "left_shoulder"),
    ("left_shoulder", "left_midside"),
    ("left_midside", "left_hip"),
    ("mouse_center", "right_shoulder"),
    ("right_shoulder", "right_midside"),
    ("right_midside", "right_hip"),
]


def _looks_like_dlc_multilevel_csv(input_csv: str) -> bool:
    try:
        with open(input_csv, "r", encoding="utf-8", errors="ignore") as file_handle:
            first_line = file_handle.readline().strip().lower()
            second_line = file_handle.readline().strip().lower()
        return first_line.startswith("scorer,") and second_line.startswith("bodyparts,")
    except Exception:
        return False


def _load_pose_dataframe(input_path: str) -> pd.DataFrame:
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".h5":
        return pd.read_hdf(input_path)
    if ext == ".csv" and _looks_like_dlc_multilevel_csv(input_path):
        return pd.read_csv(input_path, header=[0, 1, 2], index_col=0)
    raise ValueError(f"Unsupported pose file for renderer: {input_path}")


def _extract_bodyparts(df_pose: pd.DataFrame) -> list[str]:
    if not isinstance(df_pose.columns, pd.MultiIndex) or df_pose.columns.nlevels < 3:
        raise ValueError("Expected DeepLabCut MultiIndex columns (scorer, bodyparts, coords).")
    bodyparts = df_pose.columns.get_level_values(1).unique().tolist()
    return [str(bodypart) for bodypart in bodyparts]


def _build_bodypart_palette(bodyparts: list[str]) -> dict[str, tuple[int, int, int]]:
    palette: dict[str, tuple[int, int, int]] = {}
    for index, bodypart in enumerate(bodyparts):
        hue = int((index * 179) / max(len(bodyparts), 1))
        hsv_color = np.uint8([[[hue, 220, 255]]])
        bgr = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0][0]
        palette[bodypart] = tuple(int(channel) for channel in bgr)
    return palette


def _resolve_column(df_pose: pd.DataFrame, bodypart: str, coord: str):
    if bodypart not in df_pose.columns.get_level_values(1):
        return None

    scorer = df_pose.columns[df_pose.columns.get_level_values(1) == bodypart][0][0]
    coord_candidates = [coord]
    if coord == "likelihood":
        coord_candidates.extend(["p"])

    for coord_name in coord_candidates:
        column = (scorer, bodypart, coord_name)
        if column in df_pose.columns:
            return column
    return None


def render_keypoints_video(
    video_path: str,
    pose_path: str,
    output_path: str,
    pcutoff: float = DEFAULT_P_CUTOFF,
    dot_radius: int = DEFAULT_DOT_RADIUS,
) -> str:
    output_path = os.path.abspath(output_path)
    raw_output_path = os.path.splitext(output_path)[0] + "_raw.mp4"

    df_pose = _load_pose_dataframe(pose_path)
    bodyparts = _extract_bodyparts(df_pose)
    palette = _build_bodypart_palette(bodyparts)

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = cv2.VideoWriter(
        raw_output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not create output video: {raw_output_path}")

    total_frames = min(frame_count, len(df_pose)) if frame_count else len(df_pose)
    print(f"[RENDER] Video: {video_path}")
    print(f"[RENDER] Pose: {pose_path}")
    print(f"[RENDER] Output: {output_path}")
    print(f"[RENDER] Frames to render: {total_frames}")

    frame_index = 0
    progress_step = max(1, total_frames // 20) if total_frames else 1
    while frame_index < total_frames:
        ok, frame = capture.read()
        if not ok:
            break

        row = df_pose.iloc[frame_index]
        points: dict[str, tuple[int, int]] = {}
        for bodypart in bodyparts:
            x_col = _resolve_column(df_pose, bodypart, "x")
            y_col = _resolve_column(df_pose, bodypart, "y")
            p_col = _resolve_column(df_pose, bodypart, "likelihood")
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
            start_point = points[start_bp]
            end_point = points[end_bp]
            edge_color = palette.get(start_bp, (255, 255, 255))
            cv2.line(frame, start_point, end_point, edge_color, 1, lineType=cv2.LINE_AA)

        cv2.putText(
            frame,
            f"frame {frame_index + 1}/{total_frames}",
            (16, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            lineType=cv2.LINE_AA,
        )

        writer.write(frame)
        frame_index += 1
        if frame_index % progress_step == 0 or frame_index == total_frames:
            print(f"[RENDER] {frame_index}/{total_frames}")

    capture.release()
    writer.release()
    print("[RENDER] Transcoding overlay to browser-friendly H.264...")
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        raw_output_path,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]
    try:
        subprocess.run(
            ffmpeg_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if os.path.exists(raw_output_path):
            os.remove(raw_output_path)
    except Exception as error:
        if os.path.exists(output_path):
            os.remove(output_path)
        os.replace(raw_output_path, output_path)
        print(f"[WARN] Browser-friendly transcode failed, using raw MP4 instead: {error}")

    print(f"[OUTPUT] OVERLAY_VIDEO={output_path}")
    print("[RENDER] Done")
    return output_path


def _guess_pose_path(video_path: str) -> str:
    base = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = os.path.dirname(video_path)
    for pattern in (f"{base}*DLC*.h5", f"{base}*DLC*.csv"):
        matched = sorted(glob.glob(os.path.join(video_dir, pattern)))
        if matched:
            return matched[0]
    raise FileNotFoundError(f"No DLC pose file found for video: {video_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a video with DeepLabCut keypoints overlay.")
    parser.add_argument("--video", required=True, help="Path to the analyzed video.")
    parser.add_argument("--pose", required=False, help="Path to the DLC H5/CSV pose file.")
    parser.add_argument("--output", required=False, help="Path to the output labeled MP4.")
    parser.add_argument("--pcutoff", type=float, default=DEFAULT_P_CUTOFF, help="Minimum likelihood to draw a keypoint.")
    args = parser.parse_args()

    video_path = os.path.abspath(args.video)
    pose_path = os.path.abspath(args.pose) if args.pose else _guess_pose_path(video_path)
    output_path = os.path.abspath(args.output) if args.output else os.path.splitext(video_path)[0] + "_dlc_overlay.mp4"

    render_keypoints_video(
        video_path=video_path,
        pose_path=pose_path,
        output_path=output_path,
        pcutoff=args.pcutoff,
    )
