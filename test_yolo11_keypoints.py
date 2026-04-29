"""
test_yolo11_keypoints.py - Verificar keypoints del modelo YOLO11
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import YOLO_POSE_MODEL


def test_yolo_model():
    """Prueba el modelo YOLO11 para ver qué keypoints genera."""
    print("=" * 60)
    print("VERIFICACIÓN DEL MODELO YOLO11")
    print("=" * 60)
    
    print(f"\n📁 Modelo: {YOLO_POSE_MODEL}")
    print(f"[OK] Existe: {YOLO_POSE_MODEL.exists()}")
    
    if not YOLO_POSE_MODEL.exists():
        print("\n❌ ERROR: Modelo no encontrado")
        return
    
    print("\n[INFO] Cargando modelo YOLO11...")
    from ultralytics import YOLO
    
    model = YOLO(str(YOLO_POSE_MODEL))
    
    print(f"[INFO] Modelo cargado: {model.model_name if hasattr(model, 'model_name') else 'YOLO11'}")
    print(f"[INFO] Tipo de tarea: {model.task}")
    
    # Obtener nombres de keypoints si están disponibles
    if hasattr(model, 'names'):
        print(f"\n[INFO] Nombres de clases: {model.names}")
    
    # Para modelos de pose, los keypoints están definidos en el modelo
    # Intentar obtener información del modelo
    if hasattr(model.model, 'yaml'):
        print(f"\n[INFO] Configuración del modelo:")
        yaml_config = model.model.yaml
        if isinstance(yaml_config, dict):
            for key, value in yaml_config.items():
                if key in ['kpt_shape', 'nc', 'names']:
                    print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_yolo_model()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
