import argparse
import glob
import os
import site
import sys
import threading
import time
from pathlib import Path

import cv2


def log(message):
    print(message, flush=True)


def configure_runtime(force_cpu: bool):
    if force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        os.environ["TF_USE_LEGACY_KERAS"] = "1"
        os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
    else:
        os.environ["TF_USE_LEGACY_KERAS"] = "1"
        os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

    os.environ["HF_HOME"] = os.path.abspath("hf_cache")

    try:
        site_packages = site.getsitepackages()[1]
        nvidia_path = os.path.join(site_packages, "nvidia")
        if os.path.exists(nvidia_path):
            for root, dirs, _files in os.walk(nvidia_path):
                if "bin" not in dirs:
                    continue
                bin_path = os.path.join(root, "bin")
                os.environ["PATH"] = str(bin_path) + os.pathsep + os.environ["PATH"]
                try:
                    os.add_dll_directory(bin_path)
                except Exception:
                    pass
    except Exception as error:
        log(f"[WARN] Could not auto-configure NVIDIA DLLs: {error}")


def start_heartbeat(name: str, interval_seconds: int = 12):
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
    capture = cv2.VideoCapture(video_path)
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

    duration_seconds = frame_count / fps
    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds,
    }


def trim_video_segment(video_path: str, start_seconds: float, end_seconds: float, output_path: str) -> str:
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
        cv2.VideoWriter_fourcc(*"mp4v"),
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
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = os.path.dirname(video_path)
    patterns = [
        f"{base_name}*filtered*.csv",
        f"{base_name}*filtered*.h5",
        f"{base_name}*DLC*.csv",
        f"{base_name}*DLC*.h5",
    ]
    for pattern in patterns:
        matched = sorted(glob.glob(os.path.join(video_dir, pattern)))
        if matched:
            return os.path.abspath(matched[-1])
    return None


def analyze_video(
    video_path: str,
    model_name: str = "superanimal_topviewmouse",
    batch_size: int = 16,
    force_cpu: bool = False,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
):
    configure_runtime(force_cpu)

    log("=" * 60)
    log("DEEPLABCUT ANALYSIS: SUPERANIMAL")
    log("=" * 60)
    log("[STEP] BOOT")
    log(f"[INFO] Input video: {os.path.abspath(video_path)}")
    log(f"[INFO] Model: {model_name}")
    log(f"[INFO] Batch size: {batch_size}")
    log(f"[INFO] Force CPU: {force_cpu}")
    log(f"[INFO] HF cache: {os.environ['HF_HOME']}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    analysis_video = resolve_analysis_video(video_path, start_seconds, end_seconds)

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

    log("[STEP] IMPORT_DLC")
    import_heartbeat = start_heartbeat("import_dlc")
    try:
        from deeplabcut.modelzoo.api.superanimal_inference import video_inference
        import torch
    finally:
        import_heartbeat.set()

    if force_cpu:
        log("[INFO] CPU mode requested by user.")
    elif torch.cuda.is_available():
        log(f"[INFO] GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        log("[WARN] CUDA not detected. Inference may run on CPU.")

    log("[STEP] INFERENCE")
    inference_heartbeat = start_heartbeat("inference")
    try:
        video_inference(
            videos=[analysis_video],
            superanimal_name=model_name,
            videotype=os.path.splitext(analysis_video)[1].lstrip(".").lower(),
            batchsize=batch_size,
        )
    finally:
        inference_heartbeat.set()

    pose_file = find_pose_file(analysis_video)
    if pose_file:
        log(f"[OUTPUT] POSE_FILE={pose_file}")
    else:
        log("[WARN] No pose file detected after inference.")

    log("[STEP] COMPLETE")
    log(f"[OUTPUT] ANALYZED_VIDEO={analysis_video}")
    log("=" * 60)
    log("SUCCESS: Analysis complete.")
    log("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run DeepLabCut SuperAnimal analysis with optional trimming.")
    parser.add_argument("--video", required=True, help="Path to the source video file.")
    parser.add_argument("--model", default="superanimal_topviewmouse", help="SuperAnimal model name.")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size for inference.")
    parser.add_argument("--force-cpu", action="store_true", help="Disable CUDA for this run.")
    parser.add_argument("--start-seconds", type=float, default=0.0, help="Start time of the analysis window.")
    parser.add_argument("--end-seconds", type=float, default=None, help="End time of the analysis window.")
    args = parser.parse_args()

    try:
        analyze_video(
            video_path=os.path.abspath(args.video),
            model_name=args.model,
            batch_size=max(1, min(int(args.batch_size), 64)),
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
