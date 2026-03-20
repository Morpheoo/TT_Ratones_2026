import argparse
import glob
import os
import shutil
import subprocess
import sys
from datetime import datetime

import pandas as pd


PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATASET_DIR = os.path.join(PROJECT_DIR, "dataset_tt")
DEFAULT_PROJECT_ROOT = os.path.join(
    PROJECT_DIR,
    "data",
    "simba_projects",
    "New folder",
    "thigmotaxis_optimizado",
)
DEFAULT_PROJECT_FOLDER = os.path.join(DEFAULT_PROJECT_ROOT, "project_folder")
DEFAULT_TARGETS_DIR = os.path.join(DEFAULT_PROJECT_FOLDER, "csv", "targets_inserted")
DEFAULT_FEATURES_DIR = os.path.join(DEFAULT_PROJECT_FOLDER, "csv", "features_extracted")
DEFAULT_PY310 = os.path.join(PROJECT_DIR, "venv_310", "Scripts", "python.exe")
DEFAULT_PY311 = os.path.join(PROJECT_DIR, "venv_311", "Scripts", "python.exe")
DEFAULT_BBOX_SCRIPT = os.path.join(PROJECT_DIR, "src", "scripts", "apply_dlc_bbox_constraint.py")
DEFAULT_FEATURE_SCRIPT = os.path.join(PROJECT_DIR, "src", "scripts", "compute_simba_features.py")
SOURCE_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _ensure_exists(path: str, description: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{description} not found: {path}")


def _find_source_video(video_name: str, dataset_dir: str) -> str:
    for extension in SOURCE_EXTENSIONS:
        candidate = os.path.join(dataset_dir, f"{video_name}{extension}")
        if os.path.exists(candidate):
            return candidate

    matches: list[str] = []
    for extension in SOURCE_EXTENSIONS:
        matches.extend(glob.glob(os.path.join(dataset_dir, f"{video_name}*{extension}")))
    matches = [path for path in sorted(matches) if "_bbox_constrained" not in os.path.basename(path)]
    if not matches:
        raise FileNotFoundError(f"No source video found for {video_name} in {dataset_dir}")
    return matches[0]


def _find_source_pose(video_name: str, dataset_dir: str) -> str:
    patterns = [
        os.path.join(dataset_dir, f"{video_name}DLC*.h5"),
        os.path.join(dataset_dir, f"{video_name}*DLC*.h5"),
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern))

    filtered = []
    for path in sorted(set(matches)):
        base = os.path.basename(path).lower()
        if "bbox_constrained" in base or "_labeled" in base:
            continue
        filtered.append(path)

    if not filtered:
        raise FileNotFoundError(f"No DLC H5 found for {video_name} in {dataset_dir}")
    return filtered[0]


def _run_command(cmd: list[str], label: str) -> None:
    print(f"\n[{label}] Running:")
    print(" ".join(cmd))
    ret = subprocess.call(cmd)
    if ret != 0:
        raise RuntimeError(f"{label} failed with exit code {ret}")


def _refresh_bbox_pose(
    video_name: str,
    source_video: str,
    source_pose: str,
    dataset_dir: str,
    py311: str,
    bbox_script: str,
    margin: int,
    max_jump_scale: float,
    max_radius_scale: float,
    confidence: float,
) -> tuple[str, str, str]:
    filtered_h5 = os.path.join(dataset_dir, f"{video_name}_bbox_constrained.h5")
    filtered_csv = os.path.join(dataset_dir, f"{video_name}_bbox_constrained.csv")
    filtered_mp4 = os.path.join(dataset_dir, f"{video_name}_bbox_constrained.mp4")

    bbox_outputs_ready = all(os.path.exists(path) for path in (filtered_h5, filtered_csv, filtered_mp4))
    if bbox_outputs_ready:
        newest_input = max(os.path.getmtime(path) for path in (source_video, source_pose, bbox_script))
        oldest_output = min(os.path.getmtime(path) for path in (filtered_h5, filtered_csv, filtered_mp4))
        if oldest_output >= newest_input:
            print(f"[BBOX {video_name}] Reusing existing filtered pose and validation video.")
            return filtered_h5, filtered_csv, filtered_mp4

    bbox_cmd = [
        py311,
        bbox_script,
        "--video", source_video,
        "--pose", source_pose,
        "--output_pose", filtered_h5,
        "--output_video", filtered_mp4,
        "--output_csv", filtered_csv,
        "--margin", str(margin),
        "--confidence", str(confidence),
        "--max_jump_scale", str(max_jump_scale),
        "--max_radius_scale", str(max_radius_scale),
    ]
    _run_command(bbox_cmd, f"BBOX {video_name}")
    return filtered_h5, filtered_csv, filtered_mp4


def _refresh_simba_features(
    video_name: str,
    source_video: str,
    filtered_csv: str,
    py310: str,
    feature_script: str,
    project_root: str,
    features_dir: str,
) -> str:
    feature_path = os.path.join(features_dir, f"{video_name}.csv")
    feature_cmd = [
        py310,
        feature_script,
        "--input", filtered_csv,
        "--output", feature_path,
        "--project", project_root,
        "--video", source_video,
        "--video_name", video_name,
    ]
    _run_command(feature_cmd, f"SIMBA {video_name}")
    return feature_path


def _merge_targets(video_name: str, feature_path: str, target_path: str, backup_dir: str) -> dict:
    feature_df = pd.read_csv(feature_path)
    target_df = pd.read_csv(target_path)

    if len(feature_df) != len(target_df):
        raise ValueError(
            f"Frame mismatch for {video_name}: features={len(feature_df)} vs targets_inserted={len(target_df)}"
        )

    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"{video_name}.csv")
    if not os.path.exists(backup_path):
        shutil.copy2(target_path, backup_path)

    extra_columns = [column for column in target_df.columns if column not in feature_df.columns]
    merged_df = pd.concat(
        [feature_df.reset_index(drop=True), target_df[extra_columns].reset_index(drop=True)],
        axis=1,
    )
    merged_df.to_csv(target_path, index=False)

    return {
        "frames": len(merged_df),
        "feature_columns": len(feature_df.columns),
        "extra_columns": len(extra_columns),
    }


def _discover_videos(targets_dir: str, requested_videos: list[str] | None) -> list[str]:
    if requested_videos:
        return requested_videos

    target_files = sorted(glob.glob(os.path.join(targets_dir, "*.csv")))
    return [os.path.splitext(os.path.basename(path))[0] for path in target_files]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh DLC pose with YOLO bbox constraint and rebuild SimBA training targets."
    )
    parser.add_argument("--project_root", default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--dataset_dir", default=DEFAULT_DATASET_DIR)
    parser.add_argument("--targets_dir", default=DEFAULT_TARGETS_DIR)
    parser.add_argument("--features_dir", default=DEFAULT_FEATURES_DIR)
    parser.add_argument("--py310", default=DEFAULT_PY310)
    parser.add_argument("--py311", default=DEFAULT_PY311)
    parser.add_argument("--bbox_script", default=DEFAULT_BBOX_SCRIPT)
    parser.add_argument("--feature_script", default=DEFAULT_FEATURE_SCRIPT)
    parser.add_argument("--margin", type=int, default=30)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--max_jump_scale", type=float, default=0.45)
    parser.add_argument("--max_radius_scale", type=float, default=0.65)
    parser.add_argument("--videos", nargs="*", default=None, help="Optional subset of labeled videos to refresh.")
    args = parser.parse_args()

    _ensure_exists(args.project_root, "SimBA project root")
    _ensure_exists(args.dataset_dir, "Dataset directory")
    _ensure_exists(args.targets_dir, "targets_inserted directory")
    _ensure_exists(args.py310, "venv_310 python")
    _ensure_exists(args.py311, "venv_311 python")
    _ensure_exists(args.bbox_script, "BBox constraint script")
    _ensure_exists(args.feature_script, "SimBA feature bridge script")
    os.makedirs(args.features_dir, exist_ok=True)

    videos = _discover_videos(args.targets_dir, args.videos)
    if not videos:
        raise RuntimeError("No labeled videos found to rebuild.")

    backup_dir = os.path.join(
        os.path.dirname(args.targets_dir),
        "targets_inserted_backups",
        f"bbox_refresh_{_timestamp()}",
    )

    _print_header("SIMBA TRAINING REFRESH [BBOX-CONSTRAINED]")
    print(f"Project root: {args.project_root}")
    print(f"Dataset dir:  {args.dataset_dir}")
    print(f"Videos:       {', '.join(videos)}")
    print(f"Backup dir:   {backup_dir}")

    successes: list[str] = []
    failures: dict[str, str] = {}

    for video_name in videos:
        _print_header(f"PROCESSING {video_name}")
        target_path = os.path.join(args.targets_dir, f"{video_name}.csv")
        try:
            source_video = _find_source_video(video_name, args.dataset_dir)
            source_pose = _find_source_pose(video_name, args.dataset_dir)
            print(f"Source video: {source_video}")
            print(f"Source pose:  {source_pose}")

            _, filtered_csv, filtered_mp4 = _refresh_bbox_pose(
                video_name=video_name,
                source_video=source_video,
                source_pose=source_pose,
                dataset_dir=args.dataset_dir,
                py311=args.py311,
                bbox_script=args.bbox_script,
                margin=args.margin,
                max_jump_scale=args.max_jump_scale,
                max_radius_scale=args.max_radius_scale,
                confidence=args.confidence,
            )
            print(f"Filtered pose CSV: {filtered_csv}")
            print(f"Validation video:  {filtered_mp4}")

            feature_path = _refresh_simba_features(
                video_name=video_name,
                source_video=source_video,
                filtered_csv=filtered_csv,
                py310=args.py310,
                feature_script=args.feature_script,
                project_root=args.project_root,
                features_dir=args.features_dir,
            )
            print(f"Feature CSV: {feature_path}")

            stats = _merge_targets(
                video_name=video_name,
                feature_path=feature_path,
                target_path=target_path,
                backup_dir=backup_dir,
            )
            print(
                f"targets_inserted refreshed: {stats['frames']} frames, "
                f"{stats['feature_columns']} feature columns, {stats['extra_columns']} preserved label/extra columns"
            )
            successes.append(video_name)
        except Exception as error:
            failures[video_name] = str(error)
            print(f"[ERROR] {video_name}: {error}")

    _print_header("SUMMARY")
    print(f"Successful videos: {len(successes)}")
    if successes:
        print("  " + ", ".join(successes))
    print(f"Failed videos: {len(failures)}")
    for video_name, error in failures.items():
        print(f"  - {video_name}: {error}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
