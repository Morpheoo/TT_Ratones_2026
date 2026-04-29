"""
Entrena YOLO11s-pose usando el dataset local extraído de Roboflow.
Uso: python train_pose.py

Dataset: dataset_yolo_v4/  (3953 imágenes — train:2928 / valid:682 / test:343)
Modelo resultante: runs/pose/yolo11s_pose_raton_v4/weights/best.pt
"""
import yaml
from pathlib import Path


DATA_YAML = Path("dataset_yolo_v4") / "data.yaml"
RUN_NAME  = "yolo11s_pose_raton_v4"


def fix_flip_idx(data_yaml: Path):
    CORRECT_FLIP_IDX = [0, 1, 2, 4, 3, 6, 5, 7]
    with open(data_yaml, "r") as f:
        cfg = yaml.safe_load(f)
    original_flip = cfg.get("flip_idx")
    if original_flip != CORRECT_FLIP_IDX:
        print(f"[fix] flip_idx: {original_flip} -> {CORRECT_FLIP_IDX}")
        cfg["flip_idx"] = CORRECT_FLIP_IDX
        with open(data_yaml, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    else:
        print("[ok] flip_idx ya es correcto")


if __name__ == "__main__":
    assert DATA_YAML.exists(), f"No se encontró el dataset en {DATA_YAML}. Extrae primero el ZIP."

    fix_flip_idx(DATA_YAML)

    from ultralytics import YOLO
    model = YOLO("yolo11s-pose.pt")
    model.train(
        data=str(DATA_YAML.resolve()),
        epochs=150,
        imgsz=1280,
        batch=8,
        device=0,
        patience=25,
        project="runs/pose",
        name=RUN_NAME,
        pose=12.0,
        kobj=0.5,
        fliplr=0.5,
        flipud=0.0,
        degrees=10.0,
        scale=0.4,
        mosaic=0.8,
    )

    print(f"\nEntrenamiento completo.")
    print(f"  Modelo: runs/pose/{RUN_NAME}/weights/best.pt")
