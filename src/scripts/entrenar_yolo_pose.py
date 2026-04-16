"""
Entrenamiento YOLO Pose para deteccion de keypoints de raton.
Dataset: tt_2026-1 (8 keypoints por raton)
GPU: NVIDIA RTX 5070 Ti
"""
import os
from pathlib import Path
from ultralytics import YOLO

DATASET_DIR = Path(__file__).parent.parent.parent / "tt_2026-1"
DATA_YAML   = str(DATASET_DIR / "data.yaml")
RUN_NAME    = "yolo_pose_raton_v1"

def main():
    print(f"Dataset: {DATA_YAML}")
    assert os.path.exists(DATA_YAML), f"No se encontro {DATA_YAML}"

    # Modelo base pose de Ultralytics (nano = rapido, ideal para empezar)
    model = YOLO("yolo11n-pose.pt")

    results = model.train(
        data=DATA_YAML,
        task="pose",
        epochs=100,
        imgsz=640,
        device=0,          # RTX 5070 Ti
        batch=16,
        name=RUN_NAME,
        patience=20,       # early stopping
        save=True,
        plots=True,
        verbose=True,
    )

    best = Path("runs/pose") / RUN_NAME / "weights/best.pt"
    print(f"\nEntrenamiento completado.")
    print(f"Mejor modelo: {best.resolve()}")
    return str(best.resolve())


if __name__ == "__main__":
    main()
