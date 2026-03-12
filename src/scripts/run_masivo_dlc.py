import os
import sys

# Configure environment for NVIDIA DLLs needed by TF on Windows
try:
    import site
    site_packages = site.getsitepackages()[1]
    nvidia_path = os.path.join(site_packages, "nvidia")
    if os.path.exists(nvidia_path):
        for root, dirs, files in os.walk(nvidia_path):
            if "bin" in dirs:
                bin_path = os.path.join(root, "bin")
                os.environ["PATH"] += os.pathsep + bin_path
                try:
                    os.add_dll_directory(bin_path)
                except:
                    pass
        print("NVIDIA DLLs added to PATH")
except Exception as e:
    print(f"Failed to auto-add NVIDIA DLLs: {e}")

from deeplabcut.modelzoo.api.superanimal_inference import video_inference

os.environ["HF_HOME"] = os.path.abspath("hf_cache")

VIDEOS = [
    os.path.abspath(r"dataset_tt\DZP-R1.mov"),
    os.path.abspath(r"dataset_tt\C1-R1.mov")
]

def main():
    print("Starting Massive GPU Inference with SuperAnimal TopViewMouse...")
    for video in VIDEOS:
        if not os.path.exists(video):
            print(f"Skipping {video}, not found.")
            continue
        print(f"Processing: {video}")
        
        try:
            video_inference(
                videos=[video],
                superanimal_name="superanimal_topviewmouse",
                videotype="mov",
                batchsize=16,
            )
            print(f"Successfully finished model evaluation for {video}")
        except Exception as e:
            print(f"Failed to process {video}: {e}")

if __name__ == "__main__":
    main()
