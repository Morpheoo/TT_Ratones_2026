"""
Extrae frames de videos a 3fps y los auto-etiqueta con YOLO pose.
Genera un .zip listo para subir a Roboflow.

Uso:
    python src/scripts/extract_and_label_frames.py --videos carpeta/videos --output frames_para_roboflow
"""
import argparse
import zipfile
import cv2
from pathlib import Path


MODEL_PATH = "runs/pose/yolo11s_pose_raton_v3/weights/best.pt"
EXTRACT_FPS = 3
CONF_THRESHOLD = 0.25


def extract_and_label(video_path: Path, images_dir: Path, labels_dir: Path, model, target_fps: float):
    cap = cv2.VideoCapture(str(video_path))
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, round(source_fps / target_fps))
    saved = 0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            stem = f"{video_path.stem}_f{frame_idx:06d}"
            img_path = images_dir / f"{stem}.jpg"
            lbl_path = labels_dir / f"{stem}.txt"

            cv2.imwrite(str(img_path), frame)

            results = model(frame, conf=CONF_THRESHOLD, verbose=False)[0]

            lines = []
            if results.boxes is not None and len(results.boxes) > 0:
                for box_idx in range(len(results.boxes)):
                    box = results.boxes.xywhn[box_idx].cpu().numpy()
                    cx, cy, bw, bh = box

                    kps = results.keypoints.xyn[box_idx].cpu().numpy()
                    kps_conf = results.keypoints.conf[box_idx].cpu().numpy()

                    kp_str = ""
                    for i, (kx, ky) in enumerate(kps):
                        vis = 2 if kps_conf[i] > 0.5 else 1
                        kp_str += f" {kx:.6f} {ky:.6f} {vis}"

                    lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}{kp_str}")

            lbl_path.write_text("\n".join(lines))
            saved += 1

        frame_idx += 1

    cap.release()
    return saved


def main(videos_input: str, output_dir: str, fps: float):
    from ultralytics import YOLO
    model = YOLO(MODEL_PATH)

    videos_path = Path(videos_input)
    output_path = Path(output_dir)
    images_dir = output_path / "images"
    labels_dir = output_path / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    video_exts = {".mp4", ".avi", ".mov", ".mkv"}
    if videos_path.is_file():
        video_files = [videos_path]
    else:
        video_files = [p for p in videos_path.iterdir() if p.suffix.lower() in video_exts]

    print(f"Videos encontrados: {len(video_files)}")
    total_saved = 0

    for vf in video_files:
        print(f"\nProcesando: {vf.name}")
        saved = extract_and_label(vf, images_dir, labels_dir, model, fps)
        print(f"  Frames guardados: {saved}")
        total_saved += saved

    # data.yaml requerido por Roboflow para reconocer keypoints
    data_yaml = output_path / "data.yaml"
    data_yaml.write_text(
        "kpt_shape:\n- 8\n- 3\n"
        "flip_idx:\n- 0\n- 1\n- 2\n- 4\n- 3\n- 6\n- 5\n- 7\n"
        "names:\n- mouse\n"
        "nc: 1\n"
    )

    zip_path = output_path.parent / f"{output_path.name}.zip"
    print(f"\nCreando .zip: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(data_yaml, "data.yaml")
        for img in images_dir.iterdir():
            zf.write(img, f"images/{img.name}")
        for lbl in labels_dir.iterdir():
            zf.write(lbl, f"labels/{lbl.name}")

    print(f"\nListo!")
    print(f"  Total frames: {total_saved}")
    print(f"  ZIP para Roboflow: {zip_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", required=True, help="Video o carpeta con videos")
    parser.add_argument("--output", default="frames_para_roboflow", help="Carpeta de salida")
    parser.add_argument("--fps",    type=float, default=EXTRACT_FPS, help="FPS de extraccion (default 3)")
    parser.add_argument("--model",  default=MODEL_PATH, help="Ruta al modelo .pt")
    args = parser.parse_args()

    main(args.videos, args.output, args.fps)
