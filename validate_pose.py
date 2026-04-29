"""
Inferencia de validacion visual — primeros 30 segundos del video.
Uso: python validate_pose.py
"""
from ultralytics import YOLO
import cv2

MODEL_PATH = r"runs/pose/yolo11s_pose_raton_v4/weights/best.pt"
VIDEO_IN   = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dataset_tt\R5Y20_01mar24.mp4"
VIDEO_OUT  = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\validacion_pose_v3_R5Y20_5min.mp4"
MAX_SECONDS = 300

# Keypoints: 0=nariz, 1=oreja-izq, 2=oreja-der, 3=torso,
#            4=pata-izq, 5=pata-der, 6=cola-base, 7=punta-cola
# 0=nariz, 1=torso, 2=cola-base, 3=oreja-izq, 4=oreja-der,
# 5=pata-izq, 6=pata-der, 7=punta-cola
KP_NAMES = ["nariz", "torso", "cola-base", "oreja-izq", "oreja-der",
            "pata-izq", "pata-der", "punta-cola"]
KP_COLORS = [
    (0,   0,   255),  # nariz      - rojo
    (128, 0,   128),  # torso      - morado
    (0,   20,  255),  # cola-base  - rosa
    (0,   165, 255),  # oreja-izq  - naranja
    (255, 191, 0  ),  # oreja-der  - azul claro
    (0,   165, 255),  # pata-izq   - naranja
    (255, 191, 0  ),  # pata-der   - azul claro
    (0,   20,  255),  # punta-cola - rosa
]
SKELETON = [(0,3),(0,4),(0,1),(1,5),(1,6),(1,2),(2,7)]

# Threshold por keypoint — patas requieren mayor confianza para mostrarse
# 0=nariz, 1=torso, 2=cola-base, 3=oreja-izq, 4=oreja-der,
# 5=pata-izq, 6=pata-der, 7=punta-cola
KP_CONF = [0.4, 0.4, 0.4, 0.4, 0.4, 0.75, 0.75, 0.4]


if __name__ == "__main__":
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(VIDEO_IN)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    max_frames = int(fps * MAX_SECONDS)

    out = cv2.VideoWriter(VIDEO_OUT, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    frame_idx = 0
    while frame_idx < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.25, verbose=False)[0]

        if results.keypoints is not None and len(results.keypoints.data) > 0:
            kps = results.keypoints.data[0].cpu().numpy()  # (8, 3) -> x, y, conf

            # Esqueleto
            for i, j in SKELETON:
                xi, yi, ci = kps[i]
                xj, yj, cj = kps[j]
                if ci > KP_CONF[i] and cj > KP_CONF[j]:
                    cv2.line(frame, (int(xi), int(yi)), (int(xj), int(yj)),
                             (50, 50, 50), 1)

            # Keypoints
            for k, (x, y, c) in enumerate(kps):
                if c > KP_CONF[k]:
                    cv2.circle(frame, (int(x), int(y)), 3, KP_COLORS[k], -1)
                    cv2.putText(frame, KP_NAMES[k], (int(x)+4, int(y)-3),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.3, KP_COLORS[k], 1)

        # Bounding box
        if results.boxes is not None and len(results.boxes) > 0:
            box = results.boxes.xyxy[0].cpu().numpy().astype(int)
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (200, 200, 200), 1)

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    print(f"Video guardado: {VIDEO_OUT}")
    print(f"Frames procesados: {frame_idx}")
