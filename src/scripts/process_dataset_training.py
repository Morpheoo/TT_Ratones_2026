import sys
import os
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import pipeline steps
from src.scripts.full_pipeline import (
    step1_downscale_video, 
    step2_dlc_analysis, 
    step3_convert_h5, 
    step4_import_to_simba,
    INPUT_VIDEO,
    VIDEO_NAME
)
# Note: Full pipeline globals need to be updated per video!
# Instead of polluting global scope, let's call the script via subprocess.

# Wait, subprocess is cleaner. Let's use THAT.
# But we need to modify full_pipeline.py to accept arguments if it doesn't already.
# Oh wait, we added argparse support yesterday! 
# We can call: python src/scripts/full_pipeline.py --video "path/to/video.mov"

import subprocess

# List of videos to process
VIDEOS = [
    # ALREADY DONE: r"dataset_tt\C1-R1.mov",
    r"dataset_tt\C2-R1.mov",
    r"dataset_tt\C7-R1.mov"
]

def process_video(video_path):
    print(f"\n{'='*60}")
    print(f"PROCESSING: {video_path}")
    print(f"{'='*60}")
    
    # We call the full pipeline. It will handle steps 1-4 (and 5-7, but we can ignore those or fix later).
    # Wait, Steps 5-7 are for inference/video generation. 
    # For training, we ONLY need Steps 1-4 (downscale -> tracking -> import to simba project).
    # Step 5 (extract features) is fine too.
    # Step 6 (inference) is useless as we don't have a model yet.
    # Step 7 (video) is useless.
    
    # We should run steps 1-4 only. But full_pipeline runs ALL.
    # It's okay. Inference will fail or run on old model (0 results), video will generate.
    # The key is getting the tracking data imported into SimBA.
    
    # The script accepts --video argument.
    cmd = [
        sys.executable,
        os.path.join("src", "scripts", "full_pipeline.py"),
        "--video", video_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"DONE: {video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {video_path} (Exit Code: {e.returncode})")

if __name__ == "__main__":
    for idx, video in enumerate(VIDEOS):
        abs_path = os.path.abspath(video)
        if not os.path.exists(abs_path):
            print(f"ERROR: Video not found: {abs_path}")
            continue
            
        print(f"\nStarting video {idx+1}/{len(VIDEOS)}...")
        process_video(abs_path)
    
    print("\nALL VIDEOS PROCESSED.")
