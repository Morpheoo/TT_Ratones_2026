import os
import os
import sys
from pathlib import Path
import torch # Move torch upstream to early-detect GPU

# PATCH: Add NVIDIA library paths from venv to environment
# This allows TensorFlow to find cuDNN/CUDA without system-wide installation
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

# Critical fix for DeepLabCut 2.3.x compatibility
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
# Short path for HuggingFace cache to avoid Windows MAX_PATH limit
os.environ["HF_HOME"] = os.path.abspath("hf_cache")

import deeplabcut
import torch

def analyze_video(video_path, model_name="superanimal_topviewmouse"):
    print("=" * 60)
    print("           DEEPLABCUT ANALYSIS: SUPERANIMAL")
    print("=" * 60)
    
    if torch.cuda.is_available():
        print(f"GPU DETECTED: {torch.cuda.get_device_name(0)}")
    else:
        print("WARNING: GPU NOT DETECTED. Using CPU (Will be slow).")

    print(f"Video: {video_path}")
    print(f"Model: {model_name}")
    print("-" * 60)
    print("Starting analysis... (This downloads the model first)")

    try:
        # Running SuperAnimal inference
        deeplabcut.video_inference_superanimal(
            [video_path], 
            superanimal_name=model_name
        )
        print("\n" + "=" * 60)
        print("Rendering labeled video with keypoints...")
        
        # Superanimal trick to render without config: pass empty string as config and provide superanimal_name
        deeplabcut.create_labeled_video(
            "",
            [video_path],
            videotype=os.path.splitext(video_path)[1],
            filtered=False,
            draw_skeleton=True,
            superanimal_name=model_name
        )

        print("\n" + "=" * 60)
        print("SUCCESS: Analysis Complete!")
        print(f"Results saved in: {os.path.dirname(video_path)}")
        print("=" * 60)
        
    except Exception as e:
        print("\n ERROR DURING ANALYSIS:")
        print(e)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run DeepLabCut SuperAnimal Analysis")
    parser.add_argument("--video", type=str, required=True, help="Path to the video file")
    parser.add_argument("--model", type=str, default="superanimal_topviewmouse", help="SuperAnimal model name")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)
        
    analyze_video(args.video, args.model)
