import os
import sys
from pathlib import Path

# PATCH: Add NVIDIA library paths from venv to environment
venv_path = Path(sys.executable).parent.parent
site_packages = venv_path / "Lib" / "site-packages"
nvidia_path = site_packages / "nvidia"

if nvidia_path.exists():
    for item in nvidia_path.iterdir():
        if item.is_dir():
            bin_path = item / "bin"
            if bin_path.exists():
                try:
                    os.add_dll_directory(bin_path)
                except Exception:
                    pass 
                os.environ["PATH"] = str(bin_path) + os.pathsep + os.environ["PATH"]

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "0"
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import tensorflow as tf
import torch
import sys

print("-" * 30)
print(f"Python Executable: {sys.executable}")
print("-" * 30)
print(f"TensorFlow Version: {tf.__version__}")
print(f"Num GPUs (TF): {len(tf.config.list_physical_devices('GPU'))}")
print(f"GPU Devices (TF): {tf.config.list_physical_devices('GPU')}")
print("-" * 30)
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available (Torch): {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Name (Torch): {torch.cuda.get_device_name(0)}")
print("-" * 30)
try:
    import deeplabcut
    print(f"DeepLabCut Version: {deeplabcut.__version__}")
except ImportError:
    print("DeepLabCut not found")
