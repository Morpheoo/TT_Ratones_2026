from __future__ import annotations

import argparse
import configparser
import glob
import os
import subprocess
import sys
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    GROOMING_MODEL, SIMBA_BASE, SIMBA_PROJECT_DIR, THIGMOTAXIS_MODEL,
    GROOMING_MODEL_YOLO, THIGMOTAXIS_MODEL_YOLO,
    SIMBA_YOLO_BASE, SIMBA_YOLO_PROJECT_DIR,
)


PY310 = PROJECT_ROOT / "venv_310" / "Scripts" / "python.exe"
PY311 = PROJECT_ROOT / "venv_311" / "Scripts" / "python.exe"
RUN_SUPERANIMAL_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "run_superanimal.py"
APPLY_BBOX_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "apply_dlc_bbox_constraint.py"
COMPUTE_FEATURES_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "compute_simba_features.py"
FINAL_VIDEO_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "generar_video_prediccion.py"
YOLO_POSE_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "yolo_pose_to_csv.py"
GROOMING_LSTM_SCRIPT = PROJECT_ROOT / "src" / "scripts" / "infer_grooming_lstm.py"
GROOMING_LSTM_MODEL_DIR = PROJECT_ROOT / "data" / "models" / "lstm_grooming_yolo"
YOLO_POSE_MODEL = PROJECT_ROOT / "runs" / "pose" / "yolo11s_pose_raton_v4" / "weights" / "best.pt"
KEYPOINTS_YOLO_DIR = PROJECT_ROOT / "keypoints_yolo"
RESULTADOS_YOLO_DIR = PROJECT_ROOT / "resultados_yolo"


def log(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        safe_message = message.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8",
            errors="replace",
        )
        print(safe_message, flush=True)


def ensure_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def quote_command(parts: list[str]) -> str:
    formatted: list[str] = []
    for part in parts:
        if any(character.isspace() for character in part):
            formatted.append(f'"{part}"')
        else:
            formatted.append(part)
    return " ".join(formatted)


def run_and_stream(command: list[str], label: str) -> list[str]:
    log(f"[CMD] {label}: {quote_command(command)}")
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=no_window,
    )

    collected_lines: list[str] = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        collected_lines.append(line)
        if line:
            log(line)

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"{label} failed with exit code {return_code}")
    return collected_lines


def collect_output_markers(lines: list[str]) -> dict[str, str]:
    markers: dict[str, str] = {}
    for line in lines:
        if not line.startswith("[OUTPUT] "):
            continue
        payload = line[len("[OUTPUT] ") :]
        if "=" not in payload:
            continue
        key, value = payload.split("=", 1)
        markers[key.strip().lower()] = value.strip()
    return markers


def find_pose_file(video_path: Path) -> Path | None:
    base_name = video_path.stem
    patterns = [
        f"{base_name}*filtered*.h5",
        f"{base_name}*_bbox_constrained.h5",
        f"{base_name}*DLC*.h5",
        f"{base_name}*filtered*.csv",
        f"{base_name}*_bbox_constrained.csv",
        f"{base_name}*DLC*.csv",
    ]
    for pattern in patterns:
        matches = sorted(video_path.parent.glob(pattern))
        if matches:
            return matches[-1].resolve()
    return None


def is_output_fresh(output_path: Path, dependencies: list[Path]) -> bool:
    if not output_path.exists():
        return False
    output_mtime = output_path.stat().st_mtime
    for dependency in dependencies:
        if dependency.exists() and dependency.stat().st_mtime > output_mtime:
            return False
    return True


def get_video_metadata(video_path: Path) -> dict[str, float]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video metadata for: {video_path}")

    return {
        "fps": fps,
        "frame_count": float(frame_count),
        "width": float(width),
        "height": float(height),
        "duration_seconds": frame_count / fps,
    }


def trim_video_segment(video_path: Path, start_seconds: float, end_seconds: float, output_path: Path) -> Path:
    metadata = get_video_metadata(video_path)
    fps = float(metadata["fps"])
    total_frames = int(metadata["frame_count"])
    width = int(metadata["width"])
    height = int(metadata["height"])

    start_frame = max(0, min(int(start_seconds * fps), total_frames - 1))
    end_frame = max(start_frame + 1, min(int(end_seconds * fps), total_frames))
    frames_to_write = max(end_frame - start_frame, 1)

    log("[STEP] TRIM")
    log(f"[INFO] Applying trim window: {start_seconds:.2f}s -> {end_seconds:.2f}s")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        capture.release()
        writer.release()
        raise RuntimeError(f"Could not create trimmed video: {output_path}")

    written = 0
    try:
        while written < frames_to_write:
            ok, frame = capture.read()
            if not ok:
                break
            writer.write(frame)
            written += 1
            if written == 1 or written == frames_to_write or written % max(int(fps * 5), 1) == 0:
                log(f"[TRIM] {written}/{frames_to_write}")
    finally:
        capture.release()
        writer.release()

    if written <= 0:
        raise RuntimeError("Trim operation produced an empty output video.")

    return output_path.resolve()


def resolve_analysis_video(video_path: Path, start_seconds: float, end_seconds: float | None) -> Path:
    metadata = get_video_metadata(video_path)
    total_duration = float(metadata["duration_seconds"])
    safe_end = total_duration if end_seconds is None else min(float(end_seconds), total_duration)
    safe_start = max(0.0, min(float(start_seconds or 0.0), safe_end - 0.1))

    needs_trim = safe_start > 0.0 or safe_end < total_duration - 0.5
    if not needs_trim:
        log("[INFO] Full video will be analyzed.")
        log(f"[OUTPUT] ANALYZED_VIDEO={video_path.resolve()}")
        return video_path.resolve()

    trimmed_name = f"{video_path.stem}_trimmed_{int(safe_start)}_{int(safe_end)}.mp4"
    trimmed_path = video_path.with_name(trimmed_name).resolve()
    if is_output_fresh(trimmed_path, [video_path]):
        log(f"[INFO] Reusing existing trimmed file: {trimmed_path}")
    else:
        trim_video_segment(video_path, safe_start, safe_end, trimmed_path)

    log(f"[OUTPUT] ANALYZED_VIDEO={trimmed_path}")
    return trimmed_path


def ensure_simba_project_config(
    project_root: Path,
    *,
    grooming_model: Path = GROOMING_MODEL,
    thigmotaxis_model: Path = THIGMOTAXIS_MODEL,
) -> Path:
    config_path = project_root / "project_folder" / "project_config.ini"
    ensure_path(config_path, "SimBA project config")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    # Actualizar todas las rutas a absolutas desde rutas relativas
    config.set("General settings", "project_path", str((project_root / "project_folder").resolve()))
    config.set("SML settings", "model_dir", str((project_root / "models").resolve()))
    config.set("SML settings", "model_path_1", str(thigmotaxis_model.resolve()))
    config.set("SML settings", "model_path_2", str(grooming_model.resolve()))

    with open(config_path, "w", encoding="utf-8") as config_file:
        config.write(config_file)

    return config_path


def run_dlc_stage(
    *,
    video_path: Path,
    batch_size: int,
    start_seconds: float,
    end_seconds: float | None,
    force_cpu: bool,
) -> tuple[Path, Path]:
    log("[STEP] DLC")
    command = [
        str(PY310),
        str(RUN_SUPERANIMAL_SCRIPT),
        "--video",
        str(video_path.resolve()),
        "--model",
        "superanimal_topviewmouse",
        "--batch-size",
        str(batch_size),
        "--start-seconds",
        str(start_seconds),
    ]
    if end_seconds is not None:
        command.extend(["--end-seconds", str(end_seconds)])
    if force_cpu:
        command.append("--force-cpu")

    markers = collect_output_markers(run_and_stream(command, "DLC"))
    analyzed_video = Path(markers.get("analyzed_video", str(video_path.resolve()))).resolve()
    pose_candidate = markers.get("pose_file")
    if not pose_candidate:
        inferred_pose = find_pose_file(analyzed_video)
        pose_candidate = str(inferred_pose) if inferred_pose else ""
    if not pose_candidate:
        raise FileNotFoundError(f"Pose file not found after DLC stage for {analyzed_video}")

    pose_file = Path(pose_candidate).resolve()
    if not pose_file.exists() or pose_file.is_dir():
        raise FileNotFoundError(f"Pose file not found after DLC stage: {pose_file}")

    log(f"[OUTPUT] ANALYZED_VIDEO={analyzed_video}")
    log(f"[OUTPUT] RAW_POSE_FILE={pose_file}")
    return analyzed_video, pose_file


def run_yolo_pose_stage(*, video_path: Path, conf: float = 0.25) -> tuple[Path, Path, Path]:
    log("[STEP] YOLO_POSE")
    out_dir = KEYPOINTS_YOLO_DIR / video_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    output_csv = out_dir / f"{video_path.stem}_yolo_pose.csv"
    output_video = out_dir / f"{video_path.stem}_yolo_keypoints.mp4"

    command = [
        str(PY311),
        str(YOLO_POSE_SCRIPT),
        "--video",     str(video_path.resolve()),
        "--output",    str(output_csv),
        "--video-out", str(output_video),
        "--conf",      str(conf),
        "--model",     str(YOLO_POSE_MODEL.resolve()),
    ]
    run_and_stream(command, "YOLO_POSE")

    log(f"[OUTPUT] ANALYZED_VIDEO={video_path.resolve()}")
    log(f"[OUTPUT] FILTERED_CSV={output_csv.resolve()}")
    log(f"[OUTPUT] YOLO_KEYPOINTS_VIDEO={output_video.resolve()}")
    return video_path.resolve(), output_csv.resolve(), output_video.resolve()


def run_bbox_stage(*, analyzed_video: Path, pose_file: Path) -> tuple[Path, Path, Path]:
    log("[STEP] BBOX")
    base_name = analyzed_video.stem
    filtered_pose = analyzed_video.with_name(f"{base_name}_bbox_constrained.h5")
    filtered_csv = analyzed_video.with_name(f"{base_name}_bbox_constrained.csv")
    bbox_video = analyzed_video.with_name(f"{base_name}_bbox_constraint.mp4")

    if all(
        is_output_fresh(output_path, [analyzed_video, pose_file, APPLY_BBOX_SCRIPT])
        for output_path in (filtered_pose, filtered_csv, bbox_video)
    ):
        log(f"[INFO] Reusing existing bbox outputs for {base_name}.")
    else:
        command = [
            str(PY311),
            str(APPLY_BBOX_SCRIPT),
            "--video",
            str(analyzed_video),
            "--pose",
            str(pose_file),
            "--output_pose",
            str(filtered_pose),
            "--output_video",
            str(bbox_video),
            "--output_csv",
            str(filtered_csv),
        ]
        run_and_stream(command, "BBOX")

    log(f"[OUTPUT] FILTERED_POSE={filtered_pose.resolve()}")
    log(f"[OUTPUT] FILTERED_CSV={filtered_csv.resolve()}")
    log(f"[OUTPUT] BBOX_VIDEO={bbox_video.resolve()}")
    return filtered_pose.resolve(), filtered_csv.resolve(), bbox_video.resolve()


def run_feature_stage(
    *,
    analyzed_video: Path,
    filtered_csv: Path,
    project_root: Path,
    zones_file: Path | None,
) -> Path:
    log("[STEP] SIMBA_FEATURES")
    video_name = analyzed_video.stem
    feature_csv = project_root / "project_folder" / "csv" / "features_extracted" / f"{video_name}.csv"
    dependencies = [filtered_csv, COMPUTE_FEATURES_SCRIPT]
    if zones_file is not None:
        dependencies.append(zones_file)

    if is_output_fresh(feature_csv, dependencies):
        log(f"[INFO] Reusing existing SimBA features for {video_name}.")
    else:
        command = [
            str(PY310),
            str(COMPUTE_FEATURES_SCRIPT),
            "--input",
            str(filtered_csv),
            "--output",
            str(feature_csv),
            "--project",
            str(project_root),
            "--video",
            str(analyzed_video),
            "--video_name",
            video_name,
        ]
        if zones_file is not None:
            command.extend(["--zonas", str(zones_file)])
        run_and_stream(command, "SIMBA_FEATURES")

    log(f"[OUTPUT] FEATURE_CSV={feature_csv.resolve()}")
    return feature_csv.resolve()


def run_grooming_lstm_stage(
    *,
    feature_csv: Path,
    output_dir: Path,
    fps: float = 30.0,
) -> Path:
    log("[STEP] GROOMING_LSTM")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / f"{feature_csv.stem}_grooming_lstm.csv"
    dependencies = [
        feature_csv,
        GROOMING_LSTM_SCRIPT,
        GROOMING_LSTM_MODEL_DIR / "grooming_lstm.keras",
        GROOMING_LSTM_MODEL_DIR / "scaler.pkl",
        GROOMING_LSTM_MODEL_DIR / "metadata.json",
    ]

    if is_output_fresh(output_csv, dependencies):
        log(f"[INFO] Reusing existing Grooming LSTM inference for {feature_csv.stem}.")
    else:
        command = [
            str(PY310),
            str(GROOMING_LSTM_SCRIPT),
            "--features",
            str(feature_csv),
            "--model-dir",
            str(GROOMING_LSTM_MODEL_DIR),
            "--output",
            str(output_csv),
            "--fps",
            str(fps),
        ]
        run_and_stream(command, "GROOMING_LSTM")

    log(f"[OUTPUT] GROOMING_LSTM_CSV={output_csv.resolve()}")
    return output_csv.resolve()


def find_generated_model(patterns: list[str], model_dir: Path) -> Path:
    for pattern in patterns:
        matches = sorted(model_dir.glob(pattern))
        if matches:
            return matches[-1].resolve()
    raise FileNotFoundError(f"No model file found in {model_dir} for patterns: {patterns}")


def run_final_video_stage(
    *,
    analyzed_video: Path,
    feature_csv: Path,
    zones_file: Path | None,
    project_root: Path,
    grooming_model: Path = GROOMING_MODEL,
    thigmotaxis_model: Path = THIGMOTAXIS_MODEL,
    output_dir: Path | None = None,
    grooming_source: str = "rf",
    lstm_grooming_csv: Path | None = None,
) -> tuple[Path, Path | None, Path | None]:
    log("[STEP] FINAL_VIDEO")
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = analyzed_video.stem
        output_video = output_dir / f"{stem}_STREAMLIT_MULTIMODAL.mp4"
    else:
        output_video = analyzed_video.with_name(f"{analyzed_video.stem}_STREAMLIT_MULTIMODAL.mp4")
    trajectory_file = output_video.with_name(output_video.stem + "_trajectory.csv")
    grooming_timelog = output_video.with_name(output_video.stem + "_GROOMING_TIMELOG.csv")
    thigmotaxis_timelog = output_video.with_name(output_video.stem + "_THIGMOTAXIS_TIMELOG.csv")
    dependencies = [analyzed_video, feature_csv, FINAL_VIDEO_SCRIPT, grooming_model, thigmotaxis_model]
    if zones_file is not None:
        dependencies.append(zones_file)
    if lstm_grooming_csv is not None:
        dependencies.append(lstm_grooming_csv)

    final_outputs = [output_video, trajectory_file, grooming_timelog, thigmotaxis_timelog]
    if all(is_output_fresh(output_path, dependencies) for output_path in final_outputs):
        log(f"[INFO] Reusing existing multimodal video for {analyzed_video.stem}.")
    else:
        command = [
            str(PY311),
            str(FINAL_VIDEO_SCRIPT),
            "--video",
            str(analyzed_video),
            "--features",
            str(feature_csv),
            "--model_thigmo",
            str(thigmotaxis_model.resolve()),
            "--model_grooming",
            str(grooming_model.resolve()),
            "--output",
            str(output_video),
            "--grooming-source",
            grooming_source,
            "--grooming-confirm-threshold",
            "0.41",
        ]
        if lstm_grooming_csv is not None:
            command.extend(
                [
                    "--lstm-grooming-csv",
                    str(lstm_grooming_csv),
                    "--lstm-rescue-rf-threshold",
                    "0.22",
                    "--lstm-rescue-threshold",
                    "0.11",
                ]
            )
        if zones_file is not None:
            command.extend(["--zonas_file", str(zones_file)])
        run_and_stream(command, "FINAL_VIDEO")

    log(f"[OUTPUT] MULTIMODAL_VIDEO={output_video.resolve()}")
    if trajectory_file.exists():
        log(f"[OUTPUT] TRAJECTORY_FILE={trajectory_file.resolve()}")
    if grooming_timelog.exists():
        log(f"[OUTPUT] GROOMING_TIMELOG={grooming_timelog.resolve()}")
    if thigmotaxis_timelog.exists():
        log(f"[OUTPUT] THIGMOTAXIS_TIMELOG={thigmotaxis_timelog.resolve()}")
    return (
        output_video.resolve(),
        trajectory_file.resolve() if trajectory_file.exists() else None,
        grooming_timelog.resolve() if grooming_timelog.exists() else None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the operational TT 2026 behavior pipeline.")
    parser.add_argument("--video", required=True, help="Input video path.")
    parser.add_argument("--zones-file", default="", help="Path to the normalized zones JSON file.")
    parser.add_argument("--project-root", default=str(SIMBA_BASE.resolve()), help="Root path of the active SimBA project.")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size for DLC inference.")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU for the DLC stage.")
    parser.add_argument("--start-seconds", type=float, default=0.0, help="Trim start in seconds.")
    parser.add_argument("--end-seconds", type=float, default=None, help="Trim end in seconds.")
    parser.add_argument("--skip-final-video", action="store_true", help="Stop after bbox + SimBA feature sync.")
    parser.add_argument("--backend", default="dlc", choices=["dlc", "yolo"], help="Pose extraction backend: dlc or yolo.")
    parser.add_argument(
        "--grooming-source",
        default="rescue",
        choices=["rf", "lstm", "ensemble", "rescue"],
        help="Grooming decision source for the final video. YOLO default uses RF with LSTM temporal rescue.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        video_path = Path(args.video).expanduser().resolve()
        zones_file = Path(args.zones_file).expanduser().resolve() if args.zones_file else None

        # Seleccionar proyecto y modelos según backend
        if args.backend == "yolo":
            # Si el usuario paso --project-root explicito (distinto del
            # default legacy DLC), respetarlo (caso sandbox). Los modelos
            # YOLO siempre vienen del productivo (referenciados en el
            # project_config.ini del sandbox).
            explicit_root = Path(args.project_root).expanduser().resolve()
            if explicit_root != SIMBA_BASE.resolve():
                project_root = explicit_root
            else:
                project_root = SIMBA_YOLO_BASE.resolve()
            grooming_model = GROOMING_MODEL_YOLO
            thigmotaxis_model = THIGMOTAXIS_MODEL_YOLO
        else:
            project_root = Path(args.project_root).expanduser().resolve()
            grooming_model = GROOMING_MODEL
            thigmotaxis_model = THIGMOTAXIS_MODEL

        ensure_path(video_path, "Input video")
        ensure_path(PY310, "venv_310 python")
        ensure_path(PY311, "venv_311 python")
        ensure_path(COMPUTE_FEATURES_SCRIPT, "SimBA feature bridge")
        ensure_path(FINAL_VIDEO_SCRIPT, "Multimodal renderer")
        ensure_path(project_root, "SimBA project root")
        ensure_path(grooming_model, "Grooming model")
        ensure_path(thigmotaxis_model, "Thigmotaxis model")
        if zones_file is not None:
            ensure_path(zones_file, "Zones JSON")
        if args.backend == "dlc":
            ensure_path(RUN_SUPERANIMAL_SCRIPT, "DLC script")
            ensure_path(APPLY_BBOX_SCRIPT, "BBox script")
        else:
            ensure_path(YOLO_POSE_SCRIPT, "YOLO Pose script")
            ensure_path(YOLO_POSE_MODEL, "YOLO Pose model (best.pt)")
            if not bool(args.skip_final_video) and args.grooming_source != "rf":
                ensure_path(GROOMING_LSTM_SCRIPT, "Grooming LSTM inference script")
                ensure_path(GROOMING_LSTM_MODEL_DIR / "grooming_lstm.keras", "Grooming LSTM model")
                ensure_path(GROOMING_LSTM_MODEL_DIR / "scaler.pkl", "Grooming LSTM scaler")
                ensure_path(GROOMING_LSTM_MODEL_DIR / "metadata.json", "Grooming LSTM metadata")

        log("=" * 72)
        log("TT 2026 BEHAVIOR PIPELINE")
        log("=" * 72)
        log("[STEP] BOOT")
        
        # Actualizar rutas de SimBA automáticamente
        fix_simba_script = PROJECT_ROOT / "fix_simba_paths.py"
        if fix_simba_script.exists():
            log("[INFO] Actualizando rutas de SimBA...")
            try:
                subprocess.run(
                    [str(PY311), str(fix_simba_script)],
                    cwd=str(PROJECT_ROOT),
                    check=True,
                    capture_output=True,
                    text=True
                )
                log("[INFO] Rutas de SimBA actualizadas correctamente")
            except subprocess.CalledProcessError as e:
                log(f"[WARNING] No se pudieron actualizar las rutas de SimBA: {e}")
        
        log(f"[INFO] Video: {video_path}")
        log(f"[INFO] Backend: {args.backend.upper()}")
        log(f"[INFO] SimBA project: {project_root}")
        log(f"[INFO] Grooming source: {args.grooming_source if args.backend == 'yolo' else 'rf'}")
        if args.backend == "dlc":
            log(f"[INFO] DLC batch size: {max(4, min(int(args.batch_size), 32))}")
            log(f"[INFO] Force CPU: {bool(args.force_cpu)}")
        if zones_file is not None:
            log(f"[INFO] Zones file: {zones_file}")
        log(f"[INFO] Skip final video: {bool(args.skip_final_video)}")

        config_path = ensure_simba_project_config(
            project_root,
            grooming_model=grooming_model,
            thigmotaxis_model=thigmotaxis_model,
        )
        log(f"[OUTPUT] SIMBA_CONFIG={config_path.resolve()}")

        if args.backend == "yolo":
            analysis_video = resolve_analysis_video(
                video_path,
                start_seconds=float(args.start_seconds or 0.0),
                end_seconds=None if args.end_seconds is None else float(args.end_seconds),
            )
            analyzed_video, filtered_csv, kp_video = run_yolo_pose_stage(video_path=analysis_video)
            feature_csv = run_feature_stage(
                analyzed_video=analyzed_video,
                filtered_csv=filtered_csv,
                project_root=project_root,
                zones_file=zones_file,
            )
            if bool(args.skip_final_video):
                log("[STEP] COMPLETE")
                log(f"[OUTPUT] FILTERED_CSV={filtered_csv}")
                log(f"[OUTPUT] YOLO_KEYPOINTS_VIDEO={kp_video}")
                log(f"[OUTPUT] FINAL_FEATURE_CSV={feature_csv}")
                log("=" * 72)
                log("SUCCESS: Keypoints prep pipeline complete.")
                log("=" * 72)
            else:
                yolo_out_dir = RESULTADOS_YOLO_DIR / analyzed_video.stem
                lstm_grooming_csv = None
                if args.grooming_source != "rf":
                    lstm_grooming_csv = run_grooming_lstm_stage(
                        feature_csv=feature_csv,
                        output_dir=yolo_out_dir,
                    )
                multimodal_video, trajectory_file, grooming_timelog = run_final_video_stage(
                    analyzed_video=analyzed_video,
                    feature_csv=feature_csv,
                    zones_file=zones_file,
                    project_root=project_root,
                    grooming_model=grooming_model,
                    thigmotaxis_model=thigmotaxis_model,
                    output_dir=yolo_out_dir,
                    grooming_source=args.grooming_source,
                    lstm_grooming_csv=lstm_grooming_csv,
                )
                log(f"[OUTPUT] RESULTADOS_DIR={yolo_out_dir.resolve()}")
                thigmotaxis_timelog = multimodal_video.with_name(multimodal_video.stem + "_THIGMOTAXIS_TIMELOG.csv")
                log("[STEP] COMPLETE")
                log(f"[OUTPUT] FILTERED_CSV={filtered_csv}")
                log(f"[OUTPUT] YOLO_KEYPOINTS_VIDEO={kp_video}")
                log(f"[OUTPUT] FINAL_FEATURE_CSV={feature_csv}")
                if lstm_grooming_csv is not None:
                    log(f"[OUTPUT] FINAL_GROOMING_LSTM_CSV={lstm_grooming_csv}")
                log(f"[OUTPUT] FINAL_VIDEO={multimodal_video}")
                if trajectory_file is not None:
                    log(f"[OUTPUT] FINAL_TRAJECTORY={trajectory_file}")
                if grooming_timelog is not None:
                    log(f"[OUTPUT] FINAL_GROOMING_TIMELOG={grooming_timelog}")
                if thigmotaxis_timelog.exists():
                    log(f"[OUTPUT] FINAL_THIGMOTAXIS_TIMELOG={thigmotaxis_timelog.resolve()}")
                log("=" * 72)
                log("SUCCESS: Full behavior pipeline complete.")
                log("=" * 72)
        else:
            analyzed_video, raw_pose = run_dlc_stage(
                video_path=video_path,
                batch_size=max(4, min(int(args.batch_size), 32)),
                start_seconds=float(args.start_seconds or 0.0),
                end_seconds=None if args.end_seconds is None else float(args.end_seconds),
                force_cpu=bool(args.force_cpu),
            )
            filtered_pose, filtered_csv, bbox_video = run_bbox_stage(
                analyzed_video=analyzed_video,
                pose_file=raw_pose,
            )
            feature_csv = run_feature_stage(
                analyzed_video=analyzed_video,
                filtered_csv=filtered_csv,
                project_root=project_root,
                zones_file=zones_file,
            )
            if bool(args.skip_final_video):
                log("[STEP] COMPLETE")
                log(f"[OUTPUT] FILTERED_POSE_FILE={filtered_pose}")
                log(f"[OUTPUT] BBOX_VALIDATION_VIDEO={bbox_video}")
                log(f"[OUTPUT] FINAL_FEATURE_CSV={feature_csv}")
                log("=" * 72)
                log("SUCCESS: Keypoints prep pipeline complete.")
                log("=" * 72)
            else:
                multimodal_video, trajectory_file, grooming_timelog = run_final_video_stage(
                    analyzed_video=analyzed_video,
                    feature_csv=feature_csv,
                    zones_file=zones_file,
                    project_root=project_root,
                )
                thigmotaxis_timelog = multimodal_video.with_name(multimodal_video.stem + "_THIGMOTAXIS_TIMELOG.csv")
                log("[STEP] COMPLETE")
                log(f"[OUTPUT] FILTERED_POSE_FILE={filtered_pose}")
                log(f"[OUTPUT] BBOX_VALIDATION_VIDEO={bbox_video}")
                log(f"[OUTPUT] FINAL_FEATURE_CSV={feature_csv}")
                log(f"[OUTPUT] FINAL_VIDEO={multimodal_video}")
                if trajectory_file is not None:
                    log(f"[OUTPUT] FINAL_TRAJECTORY={trajectory_file}")
                if grooming_timelog is not None:
                    log(f"[OUTPUT] FINAL_GROOMING_TIMELOG={grooming_timelog}")
                if thigmotaxis_timelog.exists():
                    log(f"[OUTPUT] FINAL_THIGMOTAXIS_TIMELOG={thigmotaxis_timelog.resolve()}")
                log("=" * 72)
                log("SUCCESS: Full behavior pipeline complete.")
                log("=" * 72)
        return 0
    except Exception as error:
        log("[STEP] ERROR")
        log(f"[ERROR] {error}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
