"""
run_yolo11_pose.py - Extracción de Keypoints con YOLO11 Pose
TT Ratones 2026 | ESCOM - IPN

Reemplaza DeepLabCut SuperAnimal con YOLO11 para detección de pose.
Genera archivos CSV compatibles con el pipeline de SimBA.
"""

import argparse
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import YOLO_POSE_MODEL


def log(message):
    """Imprime mensaje con flush para compatibilidad con pipeline."""
    print(message, flush=True)


def start_heartbeat(name: str, interval_seconds: int = 12):
    """Inicia thread de heartbeat para monitoreo de progreso."""
    stop_event = threading.Event()
    started_at = time.time()

    def runner():
        while not stop_event.wait(interval_seconds):
            elapsed = int(time.time() - started_at)
            log(f"[HEARTBEAT] {name} elapsed={elapsed}s")

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return stop_event


def get_video_metadata(video_path: str) -> dict:
    """Obtiene metadata del video."""
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video metadata for: {video_path}")

    duration_seconds = frame_count / fps
    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds,
    }


def trim_video_segment(video_path: str, start_seconds: float, end_seconds: float, output_path: str) -> str:
    """Recorta segmento del video."""
    metadata = get_video_metadata(video_path)
    fps = metadata["fps"]
    width = metadata["width"]
    height = metadata["height"]
    total_frames = metadata["frame_count"]

    start_frame = max(0, min(int(start_seconds * fps), total_frames - 1))
    end_frame = max(start_frame + 1, min(int(end_seconds * fps), total_frames))
    frames_to_write = max(end_frame - start_frame, 1)

    capture = cv2.VideoCapture(video_path)
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter.fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not create trimmed video: {output_path}")

    progress_step = max(1, frames_to_write // 10)
    written = 0
    while written < frames_to_write:
        ok, frame = capture.read()
        if not ok:
            break
        writer.write(frame)
        written += 1
        if written % progress_step == 0 or written == frames_to_write:
            pct = int((written / frames_to_write) * 100)
            log(f"[TRIM] {written}/{frames_to_write} ({pct}%)")

    capture.release()
    writer.release()

    if written == 0:
        raise RuntimeError("Trim operation produced an empty output video.")

    return output_path


def resolve_analysis_video(video_path: str, start_seconds: float, end_seconds: float | None) -> str:
    """Determina si necesita recortar el video."""
    metadata = get_video_metadata(video_path)
    total_duration = metadata["duration_seconds"]
    safe_end = total_duration if end_seconds is None else min(end_seconds, total_duration)
    safe_start = max(0.0, min(start_seconds, safe_end - 0.1))

    needs_trim = safe_start > 0.0 or safe_end < total_duration - 0.5
    if not needs_trim:
        log("[INFO] Full video will be analyzed.")
        log(f"[OUTPUT] ANALYZED_VIDEO={os.path.abspath(video_path)}")
        return os.path.abspath(video_path)

    log("[STEP] TRIM")
    log(f"[INFO] Applying trim window: {safe_start:.2f}s -> {safe_end:.2f}s")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    trimmed_name = f"{base_name}_trimmed_{int(safe_start)}_{int(safe_end)}.mp4"
    trimmed_path = os.path.abspath(os.path.join(os.path.dirname(video_path), trimmed_name))

    if os.path.exists(trimmed_path):
        log(f"[INFO] Reusing existing trimmed file: {trimmed_path}")
    else:
        trim_video_segment(video_path, safe_start, safe_end, trimmed_path)

    log(f"[OUTPUT] ANALYZED_VIDEO={trimmed_path}")
    return trimmed_path


def find_pose_file(video_path: str) -> str | None:
    """Busca archivo de pose existente."""
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = os.path.dirname(video_path)
    patterns = [
        f"{base_name}*YOLO11*.csv",
        f"{base_name}*pose*.csv",
    ]
    import glob
    for pattern in patterns:
        matched = sorted(glob.glob(os.path.join(video_dir, pattern)))
        if matched:
            return os.path.abspath(matched[-1])
    return None


def run_yolo11_inference(
    video_path: str,
    model_path: str,
    conf_threshold: float = 0.25,
    device: str = "cuda:0",
) -> pd.DataFrame:
    """
    Ejecuta inferencia de YOLO11 Pose en el video.
    
    Returns:
        DataFrame con columnas multi-nivel compatibles con DeepLabCut/SimBA:
        - Nivel 0: scorer (nombre del modelo)
        - Nivel 1: bodyparts (nombres de keypoints)
        - Nivel 2: coords ('x', 'y', 'likelihood')
    """
    log("[STEP] IMPORT_YOLO")
    import_heartbeat = start_heartbeat("import_yolo")
    try:
        from ultralytics import YOLO
    finally:
        import_heartbeat.set()

    log(f"[INFO] Loading YOLO11 model: {model_path}")
    model = YOLO(model_path)

    # Nombres reales del modelo YOLO Pose v4 del proyecto.
    # Mantener este orden sincronizado con src/scripts/yolo_pose_to_csv.py.
    keypoint_names = [
        "nariz",
        "torso",
        "cola-base",
        "oreja-izq",
        "oreja-der",
        "pata-izq",
        "pata-der",
        "punta-cola",
    ]

    log(f"[INFO] Device: {device}")
    log(f"[INFO] Confidence threshold: {conf_threshold}")
    log("[STEP] INFERENCE")

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = capture.get(cv2.CAP_PROP_FPS)

    log(f"[INFO] Video frames: {total_frames}, FPS: {fps}")

    inference_heartbeat = start_heartbeat("inference")

    # Almacenar resultados
    all_results = []

    try:
        # Procesar video con YOLO
        results = model.predict(
            source=video_path,
            stream=True,
            conf=conf_threshold,
            device=device,
            verbose=False,
        )

        frame_idx = 0
        progress_step = max(1, total_frames // 20)

        for result in results:
            frame_data: dict[str, float] = {"frame": frame_idx}

            # Extraer keypoints si hay detecciones
            if result.keypoints is not None and len(result.keypoints) > 0:
                # Tomar la detección con mayor confianza (primer resultado)
                keypoints = result.keypoints.data[0].cpu().numpy()  # Shape: (num_keypoints, 3) [x, y, conf]

                for i, kp_name in enumerate(keypoint_names):
                    if i < len(keypoints):
                        x, y, conf = keypoints[i]
                        frame_data[f"{kp_name}_x"] = float(x)
                        frame_data[f"{kp_name}_y"] = float(y)
                        frame_data[f"{kp_name}_likelihood"] = float(conf)
                    else:
                        # Keypoint no disponible
                        frame_data[f"{kp_name}_x"] = np.nan
                        frame_data[f"{kp_name}_y"] = np.nan
                        frame_data[f"{kp_name}_likelihood"] = 0.0
            else:
                # No hay detección en este frame
                for kp_name in keypoint_names:
                    frame_data[f"{kp_name}_x"] = np.nan
                    frame_data[f"{kp_name}_y"] = np.nan
                    frame_data[f"{kp_name}_likelihood"] = 0.0

            all_results.append(frame_data)
            frame_idx += 1

            if frame_idx % progress_step == 0 or frame_idx == total_frames:
                pct = int((frame_idx / total_frames) * 100)
                log(f"[INFERENCE] {frame_idx}/{total_frames} ({pct}%)")

    finally:
        inference_heartbeat.set()
        capture.release()

    # Crear DataFrame
    df = pd.DataFrame(all_results)

    # Reorganizar en formato multi-nivel compatible con DLC
    # Nivel 0: scorer
    # Nivel 1: bodyparts
    # Nivel 2: coords
    scorer_name = "YOLO11s-pose-v4"

    # Crear columnas multi-nivel (sin incluir 'frame')
    multi_columns = []
    for kp_name in keypoint_names:
        multi_columns.append((scorer_name, kp_name, "x"))
        multi_columns.append((scorer_name, kp_name, "y"))
        multi_columns.append((scorer_name, kp_name, "likelihood"))

    # Reorganizar columnas del DataFrame (sin 'frame')
    cols_flat = []
    for kp_name in keypoint_names:
        cols_flat.extend([f"{kp_name}_x", f"{kp_name}_y", f"{kp_name}_likelihood"])

    # Separar frame como índice
    df_indexed = df.set_index('frame')
    df_indexed = df_indexed[cols_flat]

    # Renombrar columnas a multi-nivel
    df_indexed.columns = pd.MultiIndex.from_tuples(multi_columns)

    log(f"[INFO] Extracted keypoints for {len(df_indexed)} frames")

    return df_indexed


def analyze_video(
    video_path: str,
    conf_threshold: float = 0.25,
    device: str = "cuda:0",
    force_cpu: bool = False,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
):
    """Analiza video con YOLO11 Pose."""
    log("=" * 60)
    log("YOLO11 POSE ANALYSIS")
    log("=" * 60)
    log("[STEP] BOOT")
    log(f"[INFO] Input video: {os.path.abspath(video_path)}")
    log(f"[INFO] Model: {YOLO_POSE_MODEL}")
    log(f"[INFO] Confidence threshold: {conf_threshold}")
    log(f"[INFO] Force CPU: {force_cpu}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if not YOLO_POSE_MODEL.exists():
        raise FileNotFoundError(f"YOLO11 model not found: {YOLO_POSE_MODEL}")

    # Determinar device
    if force_cpu:
        device = "cpu"
        log("[INFO] CPU mode requested by user.")
    else:
        try:
            import torch
            if torch.cuda.is_available():
                log(f"[INFO] GPU detected: {torch.cuda.get_device_name(0)}")
                device = "cuda:0"
            else:
                log("[WARN] CUDA not detected. Inference will run on CPU.")
                device = "cpu"
        except ImportError:
            log("[WARN] PyTorch not available. Inference will run on CPU.")
            device = "cpu"

    # Resolver video a analizar (con trimming si es necesario)
    analysis_video = resolve_analysis_video(video_path, start_seconds, end_seconds)

    # Buscar archivo de pose existente
    existing_pose = find_pose_file(analysis_video)
    if existing_pose:
        log(f"[INFO] Reusing existing pose file: {existing_pose}")
        log(f"[OUTPUT] POSE_FILE={existing_pose}")
        log("[STEP] COMPLETE")
        log(f"[OUTPUT] ANALYZED_VIDEO={analysis_video}")
        log("=" * 60)
        log("SUCCESS: Analysis complete.")
        log("=" * 60)
        return

    # Ejecutar inferencia
    df_poses = run_yolo11_inference(
        video_path=analysis_video,
        model_path=str(YOLO_POSE_MODEL),
        conf_threshold=conf_threshold,
        device=device,
    )

    # Guardar resultados
    base_name = os.path.splitext(os.path.basename(analysis_video))[0]
    output_csv = os.path.join(os.path.dirname(analysis_video), f"{base_name}_YOLO11_pose.csv")

    df_poses.to_csv(output_csv)
    log(f"[INFO] Pose CSV saved: {output_csv}")
    log(f"[OUTPUT] POSE_FILE={output_csv}")
    log("[STEP] COMPLETE")
    log(f"[OUTPUT] ANALYZED_VIDEO={analysis_video}")
    log("=" * 60)
    log("SUCCESS: Analysis complete.")
    log("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run YOLO11 Pose analysis with optional trimming.")
    parser.add_argument("--video", required=True, help="Path to the source video file.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for detections.")
    parser.add_argument("--device", default="cuda:0", help="Device for inference (cuda:0, cpu, etc.).")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU mode for inference.")
    parser.add_argument("--start-seconds", type=float, default=0.0, help="Start time of the analysis window.")
    parser.add_argument("--end-seconds", type=float, default=None, help="End time of the analysis window.")
    args = parser.parse_args()

    try:
        analyze_video(
            video_path=os.path.abspath(args.video),
            conf_threshold=max(0.0, min(float(args.conf), 1.0)),
            device=str(args.device),
            force_cpu=bool(args.force_cpu),
            start_seconds=float(args.start_seconds or 0.0),
            end_seconds=None if args.end_seconds is None else float(args.end_seconds),
        )
    except Exception as error:
        log("[STEP] ERROR")
        log(f"[ERROR] {error}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
