import os
import yaml
from ultralytics import YOLO

def main():
    # 1. Arreglar rutas en data.yaml para que sean absolutas y YOLO no se pierda
    dataset_path = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\RoedoresV3_3_5_26.v2i.yolov11"
    yaml_path = os.path.join(dataset_path, "data.yaml")
    
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
        
    data['train'] = os.path.join(dataset_path, "train", "images")
    data['val'] = os.path.join(dataset_path, "valid", "images")
    data['test'] = os.path.join(dataset_path, "test", "images")
    
    with open(yaml_path, 'w') as f:
        yaml.safe_dump(data, f)
        
    print("rutas de data.yaml actualizadas a absolutas.")
    print("Iniciando entrenamiento local YOLO11n (Nano) en tu RTX...")

    # 2. Cargar modelo YOLOv11n (el más ligero y rápido, ideal para Tracking en vivo a 60fps)
    # Se descargará automáticamente el yolo11n.pt base pre-entrenado si no existe
    model = YOLO("yolo11n.pt") 
    
    # 3. Lanzar Entrenamiento Feroz 🔥
    # Usamos 50 epochs porque tienes +2200 imágenes y YOLO11 converge rapidísimo.
    # imgsz 640 es estándar, batch 16 es ideal para la RAM de la 5070 Ti.
    results = model.train(
        data=yaml_path,
        epochs=50,
        imgsz=640,
        device=0, # Asegurar que usa GPU (NVIDIA RTX 5070 Ti)
        batch=16,
        name="yolov11_raton_tracker",
        patience=15 # Early stopping si ya no mejora
    )
    
    print("\n¡Entrenamiento Completado! 🎉")
    print(f"Mejor peso guardado (best.pt) lo puedes encontrar en la consola.")

if __name__ == "__main__":
    main()
