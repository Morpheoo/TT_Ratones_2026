import os
import sys
import site

# Fix for Windows: Add nvidia package DLLs to PATH so TensorFlow can find them
try:
    site_packages = site.getsitepackages()[1] # usually the venv site-packages
    nvidia_path = os.path.join(site_packages, "nvidia")
    if os.path.exists(nvidia_path):
        for root, dirs, files in os.walk(nvidia_path):
            if "bin" in dirs:
                bin_path = os.path.join(root, "bin")
                os.environ["PATH"] += os.pathsep + bin_path
                try:
                    os.add_dll_directory(bin_path) # Python 3.8+ safety
                except:
                    pass
        print("Added NVIDIA DLLs to PATH")
except Exception as e:
    print(f"Could not auto-add NVIDIA DLLs: {e}")

import deeplabcut

# Config
VIDEO_PATH = os.path.abspath(r"videos_data\prueba_real_2min.mp4")
SUPERANIMAL_NAME = "superanimal_topviewmouse"

# Set HuggingFace cache to project directory to avoid re-downloading to default location
os.environ["HF_HOME"] = os.path.abspath("hf_cache")
print(f"Using HuggingFace cache at: {os.environ['HF_HOME']}")

def run_analysis():
    print(f"Starting analysis for: {VIDEO_PATH}")
    
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video not found at {VIDEO_PATH}")
        return

    try:
        # Run analysis using SuperAnimal model
        # Note: We don't need a config.yaml for SuperAnimal inference if we specify superanimal_name
        # But analyze_videos signatures usually require config.
        # For SuperAnimal, we use deeplabcut.modelzoo.analyze_videos? Or standard?
        # Standard analyze_videos with superanimal_name argument.
        
        # Run analysis using SuperAnimal model via imported video_inference
        from deeplabcut.modelzoo.api.superanimal_inference import video_inference
        from pathlib import Path

        video_inference(
            videos=[VIDEO_PATH],
            superanimal_name=SUPERANIMAL_NAME,
            videotype="mp4",
            batchsize=16,
        )
        print("Analysis complete!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set env vars for GPU if needed (already set in system usually, but good to be safe)
    os.environ["DLClight"] = "True" # Use light mode if possible? No, we have GPU.
    run_analysis()
