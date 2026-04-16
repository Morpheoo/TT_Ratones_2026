from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


ARTIFACT_DIRS = [
    Path("csv"),
    Path("videos"),
    Path("csv") / "input_csv",
    Path("csv") / "outlier_corrected_movement",
    Path("csv") / "outlier_corrected_movement_location",
    Path("csv") / "features_extracted",
    Path("csv") / "targets_inserted",
    Path("csv") / "targets_inserted_respaldo_clips",
    Path("csv") / "machine_results",
    Path("csv") / "validation",
]

ROI_KEYS = {
    "rectangles": "roi_rectangles",
    "circleDf": "roi_circles",
    "polygons": "roi_polygons",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prune a SimBA project so only selected videos remain active."
    )
    parser.add_argument(
        "--project-folder",
        required=True,
        help="Path to the SimBA project_folder directory.",
    )
    parser.add_argument(
        "--keep",
        nargs="+",
        required=True,
        help="Video names to keep active inside the SimBA project.",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Optional backup directory. Defaults to <project_root>/cleanup_backups/prune_<timestamp>.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply changes. Without this flag the script only reports what would be removed.",
    )
    return parser.parse_args()


def backup_shared_file(source: Path, backup_root: Path, project_folder: Path) -> None:
    if not source.exists():
        return
    relative = source.relative_to(project_folder)
    destination = backup_root / "shared_before_cleanup" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def move_file_to_backup(source: Path, backup_root: Path, project_folder: Path) -> None:
    relative = source.relative_to(project_folder)
    destination = backup_root / "removed_files" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def collect_artifact_files(project_folder: Path, keep_set: set[str]) -> list[Path]:
    removable: list[Path] = []
    for relative_dir in ARTIFACT_DIRS:
        directory = project_folder / relative_dir
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            if path.stem not in keep_set:
                removable.append(path)
    return removable


def load_roi_frames(roi_path: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    if not roi_path.exists():
        return frames

    with pd.HDFStore(roi_path, mode="r") as store:
        keys = set(store.keys())

    for key in ROI_KEYS:
        hdf_key = f"/{key}"
        if hdf_key in keys:
            frames[key] = pd.read_hdf(roi_path, key=key)
    return frames


def summarize(project_folder: Path, keep_set: set[str]) -> dict[str, object]:
    video_info_path = project_folder / "logs" / "video_info.csv"
    roi_path = project_folder / "logs" / "measures" / "ROI_definitions.h5"

    video_info_df = pd.read_csv(video_info_path) if video_info_path.exists() else pd.DataFrame()
    roi_frames = load_roi_frames(roi_path)
    removable_files = collect_artifact_files(project_folder, keep_set)

    removable_videos = []
    if not video_info_df.empty and "Video" in video_info_df.columns:
        removable_videos = video_info_df.loc[
            ~video_info_df["Video"].astype(str).isin(keep_set), "Video"
        ].astype(str).tolist()

    roi_counts: dict[str, int] = {}
    for key, frame in roi_frames.items():
        if "Video" not in frame.columns:
            roi_counts[key] = 0
            continue
        roi_counts[key] = int((~frame["Video"].astype(str).isin(keep_set)).sum())

    return {
        "video_info_path": video_info_path,
        "roi_path": roi_path,
        "video_info_df": video_info_df,
        "roi_frames": roi_frames,
        "removable_files": removable_files,
        "removable_videos": removable_videos,
        "roi_counts": roi_counts,
    }


def persist_filtered_video_info(video_info_path: Path, backup_root: Path, project_folder: Path, keep_set: set[str]) -> int:
    if not video_info_path.exists():
        return 0
    backup_shared_file(video_info_path, backup_root, project_folder)
    df = pd.read_csv(video_info_path)
    if "Video" not in df.columns:
        return 0
    removed_count = int((~df["Video"].astype(str).isin(keep_set)).sum())
    filtered = df[df["Video"].astype(str).isin(keep_set)].copy()
    filtered.to_csv(video_info_path, index=False)
    removed_rows_path = backup_root / "removed_rows" / "video_info_removed.csv"
    removed_rows_path.parent.mkdir(parents=True, exist_ok=True)
    df[~df["Video"].astype(str).isin(keep_set)].to_csv(removed_rows_path, index=False)
    return removed_count


def persist_filtered_roi(roi_path: Path, backup_root: Path, project_folder: Path, keep_set: set[str]) -> dict[str, int]:
    if not roi_path.exists():
        return {}
    backup_shared_file(roi_path, backup_root, project_folder)
    frames = load_roi_frames(roi_path)
    removed_counts: dict[str, int] = {}
    removed_rows_dir = backup_root / "removed_rows"
    removed_rows_dir.mkdir(parents=True, exist_ok=True)

    with pd.HDFStore(roi_path, mode="w") as store:
        for key, frame in frames.items():
            if "Video" not in frame.columns:
                removed_counts[key] = 0
                store[key] = frame
                continue
            mask = frame["Video"].astype(str).isin(keep_set)
            removed_counts[key] = int((~mask).sum())
            frame.loc[~mask].to_csv(removed_rows_dir / f"{ROI_KEYS[key]}_removed.csv", index=False)
            store[key] = frame.loc[mask].copy()

    return removed_counts


def main() -> int:
    args = parse_args()
    project_folder = Path(args.project_folder).resolve()
    keep_set = {item.strip() for item in args.keep if item.strip()}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_root = project_folder.parent
    backup_root = (
        Path(args.backup_dir).resolve()
        if args.backup_dir
        else (project_root / "cleanup_backups" / f"prune_{timestamp}")
    )

    if not project_folder.exists():
        raise FileNotFoundError(f"Project folder not found: {project_folder}")
    if not keep_set:
        raise ValueError("Keep list is empty.")

    summary = summarize(project_folder, keep_set)
    removable_files: list[Path] = summary["removable_files"]  # type: ignore[assignment]
    removable_videos: list[str] = summary["removable_videos"]  # type: ignore[assignment]
    roi_counts: dict[str, int] = summary["roi_counts"]  # type: ignore[assignment]

    print("=" * 72)
    print("SIMBA PROJECT PRUNE")
    print("=" * 72)
    print(f"Project folder : {project_folder}")
    print(f"Keep videos    : {', '.join(sorted(keep_set))}")
    print(f"Backup folder  : {backup_root}")
    print(f"Execute        : {args.execute}")
    print()
    print(f"Video rows to remove: {len(removable_videos)}")
    for name in removable_videos:
        print(f"  - {name}")
    print()
    print("ROI rows to remove:")
    for key, count in roi_counts.items():
        print(f"  - {key}: {count}")
    print()
    print(f"Artifact files to remove/move: {len(removable_files)}")
    for path in removable_files:
        print(f"  - {path.relative_to(project_folder)}")

    if not args.execute:
        print()
        print("[DRY-RUN] No changes were applied.")
        return 0

    backup_root.mkdir(parents=True, exist_ok=True)

    removed_video_rows = persist_filtered_video_info(
        summary["video_info_path"],  # type: ignore[arg-type]
        backup_root,
        project_folder,
        keep_set,
    )
    removed_roi_rows = persist_filtered_roi(
        summary["roi_path"],  # type: ignore[arg-type]
        backup_root,
        project_folder,
        keep_set,
    )

    moved_files = 0
    for path in removable_files:
        move_file_to_backup(path, backup_root, project_folder)
        moved_files += 1

    print()
    print("[DONE] Project cleanup applied successfully.")
    print(f"Moved files          : {moved_files}")
    print(f"Removed video rows   : {removed_video_rows}")
    for key, count in removed_roi_rows.items():
        print(f"Removed {key} rows   : {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
