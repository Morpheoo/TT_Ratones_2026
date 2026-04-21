"""
config.py - Configuración Centralizada del Proyecto
TT Ratones 2026 | ESCOM - IPN

Maneja todas las rutas del proyecto de forma relativa y portable.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(override=True)

# ============================================
# RUTAS BASE
# ============================================

# Detectar raíz del proyecto automáticamente
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Directorios principales
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = PROJECT_ROOT / "videos_data"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crear directorios si no existen
for directory in [DATA_DIR, VIDEOS_DIR, MODELS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================
# SIMBA
# ============================================

SIMBA_BASE = DATA_DIR / "simba_projects" / "New folder" / "thigmotaxis_optimizado"
SIMBA_PROJECT_DIR = SIMBA_BASE / "project_folder"
SIMBA_MODELS_DIR = SIMBA_BASE / "models"
SIMBA_GENERATED_MODELS_DIR = SIMBA_MODELS_DIR / "generated_models"

# Modelos SimBA
GROOMING_MODEL = SIMBA_GENERATED_MODELS_DIR / "Grooming.sav"
THIGMOTAXIS_MODEL = SIMBA_GENERATED_MODELS_DIR / "Thigmotaxis.sav"

# Directorios SimBA
SIMBA_INPUT_CSV = SIMBA_PROJECT_DIR / "csv" / "input_csv"
SIMBA_OUTLIER_CSV = SIMBA_PROJECT_DIR / "csv" / "outlier_corrected_movement_location"
SIMBA_FEATURES_CSV = SIMBA_PROJECT_DIR / "csv" / "features_extracted"
SIMBA_VIDEOS = SIMBA_PROJECT_DIR / "videos"

# ============================================
# DEEPLABCUT
# ============================================

DLC_MODEL_DIR = MODELS_DIR / "topview"
DLC_MODEL_PATH = DLC_MODEL_DIR / "DLC_ma_supertopview5k_resnet_50_iteration-0_shuffle-1"

# ============================================
# YOLO
# ============================================

YOLO_MODELS_DIR = MODELS_DIR / "yolo"
YOLO_POSE_MODEL = YOLO_MODELS_DIR / "yolo11s_pose_raton_v12.pt"

# Legacy fallback
YOLO_MODEL = PROJECT_ROOT / os.getenv("YOLO_MODEL", "yolo_tracker.pt")

# ============================================
# FFMPEG
# ============================================

def get_ffmpeg_path():
    """Detecta FFmpeg automáticamente."""
    # 1. Intentar desde .env
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    
    # 2. Intentar desde PATH del sistema
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    
    # 3. Buscar en ubicaciones comunes de Windows
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return str(path)
    
    # 4. No encontrado
    return None

FFMPEG_PATH = get_ffmpeg_path()

# ============================================
# FUNCIONES HELPER
# ============================================

def get_video_path(filename: str) -> Path:
    """Obtiene ruta completa de un video."""
    return VIDEOS_DIR / filename

def get_model_path(model_name: str) -> Path:
    """Obtiene ruta completa de un modelo."""
    return MODELS_DIR / model_name

def validate_paths():
    """Valida que las rutas críticas existan."""
    issues = []
    
    if not GROOMING_MODEL.exists():
        issues.append(f"❌ Modelo Grooming no encontrado: {GROOMING_MODEL}")
    
    if not THIGMOTAXIS_MODEL.exists():
        issues.append(f"❌ Modelo Thigmotaxis no encontrado: {THIGMOTAXIS_MODEL}")
    
    if not YOLO_POSE_MODEL.exists():
        issues.append(f"❌ Modelo YOLO11 Pose no encontrado: {YOLO_POSE_MODEL}")
    
    if not DLC_MODEL_PATH.exists():
        issues.append(f"⚠️ Modelo DeepLabCut no encontrado: {DLC_MODEL_PATH}")
    
    if not FFMPEG_PATH:
        issues.append(f"⚠️ FFmpeg no encontrado en el sistema")
    
    return issues

# ============================================
# VALIDACIÓN AL IMPORTAR
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("CONFIGURACIÓN DEL PROYECTO TT RATONES 2026")
    print("=" * 60)
    print(f"\n📁 Raíz del proyecto: {PROJECT_ROOT}")
    print(f"📁 Directorio de datos: {DATA_DIR}")
    print(f"📁 Directorio de videos: {VIDEOS_DIR}")
    print(f"📁 Directorio de modelos: {MODELS_DIR}")
    print(f"\n🤖 Modelo Grooming: {GROOMING_MODEL}")
    print(f"🤖 Modelo Thigmotaxis: {THIGMOTAXIS_MODEL}")
    print(f"🤖 Modelo YOLO11 Pose: {YOLO_POSE_MODEL}")
    print(f"🤖 Modelo DeepLabCut: {DLC_MODEL_PATH}")
    print(f"🤖 Modelo YOLO (legacy): {YOLO_MODEL}")
    print(f"\n🎬 FFmpeg: {FFMPEG_PATH or 'NO ENCONTRADO'}")
    
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE RUTAS")
    print("=" * 60)
    
    issues = validate_paths()
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✅ Todas las rutas críticas están OK")
