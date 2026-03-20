"""
Solo YOLO Tracker - Punto Rojo Puro
-------------------------------------
Script minimalista que ÚNICAMENTE usa el nuevo YOLOv11 entrenado
para seguir al ratón con un punto rojo en el centro del video.
SIN DLC, SIN SimBA, SIN análisis de comportamiento.
Solo el tracker.
"""

import cv2
import argparse
from ultralytics import YOLO

YOLO_MODEL_PATH = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\yolo_tracker.pt"

def run_tracker(video_path: str, output_path: str):
    print("Cargando modelo YOLOv11...")
    model = YOLO(YOLO_MODEL_PATH)

    cap = cv2.VideoCapture(video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Procesando {total} frames -> {output_path}")
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)

        # Seleccionamos la detección con mayor confianza
        best_box = None
        for box in results[0].boxes:
            if box.conf[0] > 0.35:
                if best_box is None:
                    best_box = box
                elif box.conf[0] > best_box.conf[0]:
                    best_box = box

        if best_box is not None:
            # type: ignore
            x1, y1, x2, y2 = map(int, best_box.xyxy[0]) # type: ignore
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            # Punto rojo sólido interior + aro cian exterior (visible sobre cualquier fondo)
            cv2.circle(frame, (cx, cy), 4,  (0, 0, 255), -1)  # interior rojo
            cv2.circle(frame, (cx, cy), 8,  (0, 220, 220), 1)  # aro cian
            cv2.circle(frame, (cx, cy), 12, (255, 255, 255), 1) # aro blanco exterior

        out.write(frame)
        frame_idx += 1
        if frame_idx % 300 == 0:
            print(f"  Frame {frame_idx}/{total}")

    cap.release()
    out.release()
    print(f"\n¡Listo! Video guardado en: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solo YOLO tracker - punto rojo puro")
    parser.add_argument("--video",  required=True,  help="Video de entrada")
    parser.add_argument("--output", required=True,  help="Video de salida")
    args = parser.parse_args()
    run_tracker(args.video, args.output)
