"""
Exporta keypoints de YOLO pose a CSV formato DLC para SimBA.
Opcionalmente genera un video con overlay de keypoints y esqueleto.

Uso:
    python src/scripts/yolo_pose_to_csv.py --video ruta/video.mp4 --output ruta/salida.csv
    python src/scripts/yolo_pose_to_csv.py --video ruta/video.mp4 --output ruta/salida.csv --video-out ruta/video_kp.mp4

El CSV generado tiene el formato DLC multi-index que SimBA espera:
    scorer     | YOLO11s-pose | ...
    bodyparts  | nariz        | nariz | nariz | torso | ...
    coords     | x            | y     | p     | x     | ...
"""
import argparse
import csv
from pathlib import Path
import cv2
import numpy as np

MODEL_PATH = "runs/pose/yolo11s_pose_raton_v4/weights/best.pt"

KP_NAMES = ["nariz", "torso", "cola-base", "oreja-izq", "oreja-der",
            "pata-izq", "pata-der", "punta-cola"]

# BGR colors por keypoint
KP_COLORS = [
    (0,   0,   255),   # nariz      - rojo
    (128, 0,   128),   # torso      - morado
    (0,   20,  255),   # cola-base  - rosa
    (0,   165, 255),   # oreja-izq  - naranja
    (255, 191, 0  ),   # oreja-der  - azul claro
    (0,   165, 255),   # pata-izq   - naranja
    (255, 191, 0  ),   # pata-der   - azul claro
    (0,   20,  255),   # punta-cola - rosa
]

# Pares de keypoints que forman el esqueleto
SKELETON = [(0, 3), (0, 4), (0, 1), (1, 5), (1, 6), (1, 2), (2, 7)]

# Umbral de confianza por keypoint (patas requieren más para mostrarse)
KP_CONF_VIZ = [0.4, 0.4, 0.4, 0.4, 0.4, 0.55, 0.55, 0.4]

SCORER = "YOLO11s-pose"


def build_header():
    row_scorer    = ["scorer"]
    row_bodyparts = ["bodyparts"]
    row_coords    = ["coords"]
    for name in KP_NAMES:
        for coord in ["x", "y", "likelihood"]:
            row_scorer.append(SCORER)
            row_bodyparts.append(name)
            row_coords.append(coord)
    return row_scorer, row_bodyparts, row_coords


def _draw_keypoints(frame, kps):
    """Dibuja esqueleto y keypoints sobre el frame. kps: (8, 3) numpy array [x, y, conf]."""
    for i, j in SKELETON:
        xi, yi, ci = kps[i]
        xj, yj, cj = kps[j]
        if ci > KP_CONF_VIZ[i] and cj > KP_CONF_VIZ[j]:
            cv2.line(frame, (int(xi), int(yi)), (int(xj), int(yj)), (50, 50, 50), 1)

    for k, (x, y, c) in enumerate(kps):
        if c > KP_CONF_VIZ[k]:
            cv2.circle(frame, (int(x), int(y)), 4, KP_COLORS[k], -1)
            cv2.putText(frame, KP_NAMES[k], (int(x) + 5, int(y) - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, KP_COLORS[k], 1)


def run(video_path: str, output_path: str, conf: float = 0.25, video_out: str | None = None):
    from ultralytics import YOLO
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer_video = None
    if video_out:
        video_out_path = Path(video_out)
        video_out_path.parent.mkdir(parents=True, exist_ok=True)
        writer_video = cv2.VideoWriter(
            str(video_out_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps, (width, height),
        )

    row_scorer, row_bodyparts, row_coords = build_header()

    print(f"[YOLO] Video: {Path(video_path).name} | {width}x{height} @ {fps:.1f}fps | {total_frames} frames")
    print(f"[YOLO] Modelo: {MODEL_PATH}")
    print(f"[YOLO] CSV de salida: {output_path}")
    if video_out:
        print(f"[YOLO] Video de salida: {video_out}")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row_scorer)
        writer.writerow(row_bodyparts)
        writer.writerow(row_coords)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = model(frame, conf=conf, verbose=False)[0]

            row = [frame_idx]

            if results.keypoints is not None and len(results.keypoints.data) > 0:
                kps = results.keypoints.data[0].cpu().numpy()
                for x, y, c in kps:
                    row.extend([float(x), float(y), float(c)])
                if writer_video is not None:
                    _draw_keypoints(frame, kps)
            else:
                for _ in KP_NAMES:
                    row.extend([np.nan, np.nan, 0.0])

            if writer_video is not None:
                writer_video.write(frame)

            writer.writerow(row)
            frame_idx += 1

            if frame_idx % 300 == 0:
                pct = frame_idx / total_frames * 100
                print(f"  [YOLO] {frame_idx}/{total_frames} frames ({pct:.1f}%)")

    cap.release()
    if writer_video is not None:
        writer_video.release()

    print(f"\n[YOLO] CSV guardado: {output_path}")
    if video_out:
        print(f"[YOLO] Video guardado: {video_out}")
    print(f"[YOLO] Total frames: {frame_idx} | FPS: {fps:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",     required=True,          help="Ruta al video de entrada")
    parser.add_argument("--output",    required=True,          help="Ruta al CSV de salida")
    parser.add_argument("--video-out", default=None,           help="Ruta al video de salida con keypoints (opcional)")
    parser.add_argument("--conf",      type=float, default=0.25, help="Threshold de confianza (default 0.25)")
    parser.add_argument("--model",     default=MODEL_PATH,     help="Ruta al modelo .pt")
    args = parser.parse_args()

    if args.model != MODEL_PATH:
        MODEL_PATH = args.model

    run(args.video, args.output, args.conf, args.video_out)
