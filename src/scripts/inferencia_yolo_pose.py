"""
Inferencia YOLO Pose sobre video de raton.
Genera video con keypoints y guarda CSV con coordenadas por frame.

Uso:
    python src/scripts/inferencia_yolo_pose.py --video mi_video.mp4
    python src/scripts/inferencia_yolo_pose.py --video mi_video.mp4 --modelo runs/pose/yolo_pose_raton_v1/weights/best.pt
"""
import argparse
import csv
from pathlib import Path
import cv2
from ultralytics import YOLO

KEYPOINT_NAMES = [
    "kp0", "kp1", "kp2", "kp3", "kp4", "kp5", "kp6", "kp7"
]

BEST_PT = Path(__file__).parent.parent.parent / "runs/pose/yolo_pose_raton_v1/weights/best.pt"


def inferencia(video_path: str, modelo_path: str, conf: float = 0.25):
    video_path = Path(video_path)
    modelo_path = Path(modelo_path)

    assert video_path.exists(), f"Video no encontrado: {video_path}"
    assert modelo_path.exists(), f"Modelo no encontrado: {modelo_path}"

    model = YOLO(str(modelo_path))

    output_dir = video_path.parent / f"{video_path.stem}_yolo_pose"
    output_dir.mkdir(exist_ok=True)
    output_video = output_dir / f"{video_path.stem}_keypoints.mp4"
    output_csv   = output_dir / f"{video_path.stem}_keypoints.csv"

    # Cabecera CSV
    kp_cols = []
    for name in KEYPOINT_NAMES:
        kp_cols += [f"{name}_x", f"{name}_y", f"{name}_vis"]
    csv_header = ["frame", "raton_id", "bbox_cx", "bbox_cy", "bbox_w", "bbox_h", "conf"] + kp_cols

    cap = cv2.VideoCapture(str(video_path))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print(f"Video: {video_path.name} | {width}x{height} @ {fps:.1f}fps | {total} frames")
    print(f"Modelo: {modelo_path}")
    print(f"Output: {output_dir}")

    writer = None
    frame_idx = 0
    rows = []

    results_gen = model.predict(
        source=str(video_path),
        conf=conf,
        device=0,
        stream=True,
        verbose=False,
    )

    for result in results_gen:
        frame = result.orig_img.copy()

        if result.keypoints is not None and len(result.keypoints) > 0:
            kps_xy  = result.keypoints.xy.cpu().numpy()    # (N, 8, 2)
            kps_vis = result.keypoints.conf.cpu().numpy()  # (N, 8)
            boxes   = result.boxes

            for i in range(len(kps_xy)):
                box  = boxes[i]
                cx, cy, w, h = box.xywhn[0].cpu().numpy()
                det_conf = float(box.conf[0].cpu())

                row = [frame_idx, i, round(float(cx), 5), round(float(cy), 5),
                       round(float(w), 5), round(float(h), 5), round(det_conf, 4)]

                for j in range(len(KEYPOINT_NAMES)):
                    x, y = kps_xy[i][j]
                    v    = kps_vis[i][j]
                    row += [round(float(x), 2), round(float(y), 2), round(float(v), 3)]

                rows.append(row)

        # Inicializar writer con el primer frame anotado
        annotated = result.plot(line_width=1, kpt_radius=2, font_size=0.4)
        if writer is None:
            h_out, w_out = annotated.shape[:2]
            writer = cv2.VideoWriter(
                str(output_video),
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps, (w_out, h_out)
            )

        writer.write(annotated)
        frame_idx += 1

        if frame_idx % 100 == 0:
            print(f"  Frame {frame_idx}/{total}...")

    if writer:
        writer.release()

    with open(output_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(csv_header)
        w.writerows(rows)

    print(f"\nListo!")
    print(f"  Video: {output_video}")
    print(f"  CSV:   {output_csv} ({len(rows)} detecciones)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",  required=True, help="Ruta al video de entrada")
    parser.add_argument("--modelo", default=str(BEST_PT), help="Ruta al best.pt")
    parser.add_argument("--conf",   type=float, default=0.25, help="Umbral de confianza")
    args = parser.parse_args()

    inferencia(args.video, args.modelo, args.conf)
