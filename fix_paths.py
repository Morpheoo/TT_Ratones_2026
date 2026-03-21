import os
import glob
import re

# We will scan all py files in src/scripts/ and apply replacements
scripts_dir = os.path.join("src", "scripts")
py_files = glob.glob(os.path.join(scripts_dir, "**/*.py"), recursive=True)

header_code = """
import sys
import os
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.config import (
        GROOMING_MODEL,
        THIGMOTAXIS_MODEL,
        SIMBA_PROJECT_DIR,
        SIMBA_FEATURES_CSV,
        VIDEOS_DIR,
        FFMPEG_PATH,
        YOLO_MODEL
    )
except ImportError:
    pass
"""

for file_path in py_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content

    # Replace specific paths with config variables
    content = re.sub(
        r'r"C:\\Users\\chavi\\.*?\\thigmotaxis_optimizado\\project_folder"', 
        'SIMBA_PROJECT_DIR', 
        content, flags=re.IGNORECASE|re.DOTALL
    )
    
    content = re.sub(
        r'r"C:\\Users\\chavi\\.*?\\thigmotaxis_optimizado\\models\\Thigmotaxis\.sav"', 
        'THIGMOTAXIS_MODEL', 
        content, flags=re.IGNORECASE|re.DOTALL
    )

    content = re.sub(
        r'r"C:\\Users\\chavi\\.*?\\features_extracted"', 
        'SIMBA_FEATURES_CSV', 
        content, flags=re.IGNORECASE|re.DOTALL
    )
    
    content = re.sub(
        r'r"C:\\Users\\chavi\\.*?\\yolo_tracker\.pt"', 
        'YOLO_MODEL', 
        content, flags=re.IGNORECASE|re.DOTALL
    )

    content = re.sub(
        r'r"C:\\Users\\chavi\\.*?\\dataset_tt"', 
        'VIDEOS_DIR', 
        content, flags=re.IGNORECASE|re.DOTALL
    )
    
    content = re.sub(
        r'r"C:\\ffmpeg\\.*?\\ffmpeg\.exe"', 
        'FFMPEG_PATH', 
        content, flags=re.IGNORECASE|re.DOTALL
    )

    # For simba_render_video.py
    content = re.sub(
        r'ffmpeg_exe = r"C:\\.*?"\s*\n\s*if not os\.path\.exists\(ffmpeg_exe\):',
        'ffmpeg_exe = FFMPEG_PATH\n        if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):',
        content, flags=re.IGNORECASE
    )

    # Note: For full_pipeline.py, we have specific changes to make
    if "full_pipeline.py" in file_path:
        # replace INPUT_VIDEO
        content = re.sub(
            r'INPUT_VIDEO\s*=\s*r"C:\\Users\\chavi\\[^"]+"',
            'import sys\nfrom src.config import PROJECT_ROOT, VIDEOS_DIR, FFMPEG_PATH\n\nif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):\n    INPUT_VIDEO = sys.argv[1]\nelse:\n    import glob\n    videos = glob.glob(str(VIDEOS_DIR / "*.mp4"))\n    if videos:\n        INPUT_VIDEO = str(videos[0])\n        print(f"[INFO] Usando video: {INPUT_VIDEO}")\n    else:\n        INPUT_VIDEO = ""',
            content
        )
        
        # fix ffmpeg path logic
        content = re.sub(
            r'ffmpeg_exe\s*=\s*FFMPEG_PATH\s*\n\s*if not os\.path\.exists\(ffmpeg_exe\):\s*\n\s*print\("  ERROR: ffmpeg not found for trimming"\)\s*\n\s*return False',
            'if not FFMPEG_PATH:\n        print("❌ ERROR: FFmpeg no encontrado. Instálalo o configura FFMPEG_PATH en .env")\n        return False\n\n    ffmpeg_exe = str(FFMPEG_PATH)',
            content
        )

    if content != original_content:
        # Add header if it has config vars
        if "SIMBA" in content or "THIGMOTAXIS" in content or "YOLO" in content or "FFMPEG_PATH" in content:
            if "from src.config import" not in content and "full_pipeline.py" not in file_path:
                content = header_code + "\n" + content
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {file_path}")

print("Done.")
