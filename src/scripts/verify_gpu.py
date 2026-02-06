import sys
import os

# Fix for DeepLabCut on newer TensorFlow/Keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import torch
import platform

def verify_gpu():
    print("="*40)
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print("="*40)
    
    try:
        print(f"PyTorch Version: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"CUDA Available: {cuda_available}")
        
        if cuda_available:
            print(f"CUDA Version: {torch.version.cuda}")
            device_count = torch.cuda.device_count()
            print(f"GPU Device Count: {device_count}")
            
            for i in range(device_count):
                print(f"Device {i}: {torch.cuda.get_device_name(i)}")
                print(f"  - Capability: {torch.cuda.get_device_capability(i)}")
                print(f"  - Properties: {torch.cuda.get_device_properties(i)}")
        else:
            print("WARNING: CUDA is NOT available. DeepLabCut will run slowly on CPU.")
            
    except ImportError as e:
        print(f"ERROR: Could not import torch. {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error checking GPU: {e}")

    print("="*40)
    
    # Check DeepLabCut import status
    try:
        import deeplabcut
        print(f"DeepLabCut Version: {deeplabcut.__version__}")
        print(f"DeepLabCut File: {deeplabcut.__file__}")
    except ImportError:
        print("WARNING: DeepLabCut not installed or not found.")
    except Exception as e:
        print(f"ERROR: DeepLabCut import failed: {e}")

if __name__ == "__main__":
    verify_gpu()
