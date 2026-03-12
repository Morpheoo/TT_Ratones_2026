"""
Full pipeline: Analyze a new video with trained SimBA classifiers.
Steps:
  1. Trim video to 2 minutes
  2. Run DeepLabCut SuperAnimal analysis (GPU)
  3. Convert H5 to CSV for SimBA
  4. Import into SimBA project
  5. Extract features (SimBA)
  6. Run inference with trained classifiers (SimBA)
  7. Generate annotated video with behavior overlays
"""
import os
import sys

# Force Keras 2 compatibility (CRITICAL for DeepLabCut in TF 2.16+)
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import shutil
import glob
import configparser
import site
import traceback
import argparse
import subprocess

# ── Configuration ──────────────────────────────────────────────
INPUT_VIDEO = r"C:\Users\chavi\OneDrive\Desktop\dataser_tt_mejorado\R5B20_01mar24.mp4"
VIDEO_NAME = "R5B20_01mar24_full"
ZONES_JSON = "[]"

PROJECT_DIR = os.path.abspath(".")
SIMBA_PROJECT = os.path.join(PROJECT_DIR, "data", "simba_projects", "SimBA_EPM_Analysis", "project_folder")
CONFIG_PATH = os.path.join(SIMBA_PROJECT, "project_config.ini")
VIDEOS_DIR = os.path.join(SIMBA_PROJECT, "videos")
WORK_DIR = os.path.join(PROJECT_DIR, "videos_data")

TRIMMED_VIDEO = INPUT_VIDEO # Will be updated if downscaled
SUPERANIMAL_NAME = "superanimal_topviewmouse"
DOWNSCALE_FACTOR = 0.5 # 50% scale for speed (approx 4x faster)

# ── Fix NVIDIA DLLs ───────────────────────────────────────────
try:
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
        print("[OK] Added NVIDIA DLLs to PATH")
except Exception as e:
    print(f"[WARN] Could not add NVIDIA DLLs: {e}")

os.environ["HF_HOME"] = os.path.join(PROJECT_DIR, "hf_cache")

# ── Fix ptxas (CRITICAL for RTX 50-series / SM 12.0) ─────────
# Without ptxas, TF falls back to slow JIT compilation (~10x slower)
ptxas_dir = os.path.join(
    PROJECT_DIR, "venv_310", "Lib", "site-packages",
    "nvidia", "cuda_nvcc", "bin"
)
if os.path.exists(ptxas_dir):
    os.environ["PATH"] = ptxas_dir + os.pathsep + os.environ["PATH"]
    print(f"[OK] Added ptxas to PATH: {ptxas_dir}")
else:
    print(f"[WARN] ptxas not found at {ptxas_dir}")


def step1_downscale_video():
    """Downscale video for faster inference."""
    print("\n" + "="*60)
    print(f"STEP 1: Downscaling video by {DOWNSCALE_FACTOR*100}%")
    print("="*60)
    
    global TRIMMED_VIDEO
    base = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
    output_video = os.path.join(WORK_DIR, f"{base}_down-50.mp4")
    TRIMMED_VIDEO = output_video
    
    if os.path.exists(output_video):
        print(f"  Downscaled video already exists: {output_video}")
        return True
    
    ffmpeg_exe = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_exe):
        print("  ERROR: ffmpeg not found for downscaling")
        return False
        
    # Scale filter -1:-1 to keep aspect ratio if needed, or w*0.5
    cmd = [
        ffmpeg_exe, "-y", "-i", INPUT_VIDEO,
        "-vf", f"scale=iw*{DOWNSCALE_FACTOR}:ih*{DOWNSCALE_FACTOR}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        output_video
    ]
    
    print(f"  Running: {' '.join(cmd)}")
    import subprocess
    ret = subprocess.call(cmd)
    
    if ret != 0:
        print("  ERROR: Downscaling failed")
        return False
        
    print(f"  Saved downscaled video: {output_video}")
    return True


def step2_dlc_analysis():
    """Run DeepLabCut SuperAnimal inference."""
    print("\n" + "="*60)
    print("STEP 2: Running DeepLabCut analysis (GPU)")
    print("="*60)
    
    # Check if result already exists for THIS video
    base_name_no_ext = os.path.splitext(os.path.basename(TRIMMED_VIDEO))[0]
    h5_pattern = os.path.join(WORK_DIR, f"*{base_name_no_ext}*DLC*.h5") # Specific match
    print(f"  DEBUG: TRIMMED_VIDEO={TRIMMED_VIDEO}")
    print(f"  DEBUG: Searching for existing H5 with pattern: {h5_pattern}")
    existing = glob.glob(h5_pattern)
    if existing:
        print(f"  DLC results already exist: {existing[0]}")
        return True
        
    # Check TensorFlow version for GPU support (Windows Native GPU dropped after 2.10)
    try:
        import tensorflow as tf
        tf_ver = tf.__version__
        print(f"  TensorFlow Version: {tf_ver}")
        
        # If running in venv_311 (TF 2.11+) -> Respawn in venv_310 (TF 2.10)
        # Windows Native GPU support was dropped in TF 2.10.
        # Any version > 2.10 must use venv_310 for GPU.
        major, minor, patch = tf_ver.split(".")[:3]
        if int(major) == 2 and int(minor) > 10:
             print(f"  [WARN] TF {tf_ver} > 2.10 detected (No GPU on Windows). Respawning in venv_310...")
             venv_python = os.path.abspath(os.path.join(PROJECT_DIR, "venv_310", "Scripts", "python.exe"))
             if not os.path.exists(venv_python):
                 print(f"  [ERROR] venv_310 python not found at: {venv_python}")
                 return False
            
             cmd = [venv_python, os.path.abspath(__file__), "--video", INPUT_VIDEO, "--step", "2"]
             # If using downscaled video, pass that? No, Step 2 recalculates TRIMMED_VIDEO
             # Actually, main() sets TRIMMED_VIDEO = INPUT_VIDEO initially.
             # Step 1 sets TRIMMED_VIDEO = downscaled.
             # When spawning step 2 directly, we need to know if we should use downscaled.
             # Standard pipeline ALWAYS downscales if step 1 runs.
             # If running standalone step 2, we should check if downscaled exists and use it.
             
             # The spawned process will run step2_dlc_analysis.
             # We need to ensure TRIMMED_VIDEO is correct in the subprocess.
             # Let's pass a flag or handle it in main?
             # Easier: Just check for downscaled video here in the subprocess too.
             
             print(f"  Running: {' '.join(cmd)}")
             import subprocess
             ret = subprocess.call(cmd)
             if ret != 0:
                 print("  [ERROR] DLC analysis failed in venv_310")
                 return False
             return True

    except ImportError:
        pass
    
    # If we are here, we are either in venv_310 OR we decided to run anyway.
    # Check for downscaled video preference
    # In this script, Step 1 updates global TRIMMED_VIDEO. 
    # If we are in a subprocess, TRIMMED_VIDEO is just INPUT_VIDEO.
    # We should check if the downscaled version exists and prefer it.
    base = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
    downscaled = os.path.join(WORK_DIR, f"{base}_down-50.mp4")
    target_video = TRIMMED_VIDEO
    if os.path.exists(downscaled):
        print(f"  Found downscaled video: {downscaled}")
        target_video = downscaled
    
    from deeplabcut.modelzoo.api.superanimal_inference import video_inference
    
    print(f"  Analyzing (Fast Mode): {target_video}")
    print(f"  Model: {SUPERANIMAL_NAME}")
    
    video_inference(
        videos=[target_video],
        superanimal_name=SUPERANIMAL_NAME,
        videotype="mp4",
        batchsize=8,
    )
    print("  DLC analysis complete!")
    return True


def step3_convert_h5():
    """Convert H5 to SimBA-compatible CSV."""
    print("\n" + "="*60)
    print("STEP 3: Converting H5 to CSV")
    print("="*60)
    
    import pandas as pd
    
    # Matches DLC output for THIS video specifically
    base_name_no_ext = os.path.splitext(os.path.basename(TRIMMED_VIDEO))[0]
    h5_pattern = os.path.join(WORK_DIR, f"*{base_name_no_ext}*DLC*.h5")
    h5_files = glob.glob(h5_pattern)
    if not h5_files:
        print("  ERROR: No H5 file found from DLC analysis")
        return False
    
    h5_path = h5_files[0]
    csv_out = os.path.join(WORK_DIR, f"{VIDEO_NAME}_dlc.csv")
    
    if os.path.exists(csv_out):
        print(f"  CSV already exists: {csv_out}")
        return True
    
    print(f"  Reading: {h5_path}")
    df = pd.read_hdf(h5_path)
    
    # UPSCALE COORDINATES (Only if downscaled)
    if DOWNSCALE_FACTOR != 1.0:
        scale = 1.0 / DOWNSCALE_FACTOR
        print(f"  Upscaling coordinates by {scale}x to match original video...")
        
        # Iterate columns to find x/y
        for col in df.columns:
            # Col is MultiIndex (scorer, bodypart, coords)
            scorer, bp, coord = col
            if coord in ['x', 'y']:
                df[col] = df[col] * scale
            
    df.to_csv(csv_out)
    print(f"  Saved CSV: {csv_out} ({len(df)} frames)")
    return True


def step4_import_to_simba():
    """Import DLC CSV and video into SimBA project."""
    print("\n" + "="*60)
    print("STEP 4: Importing into SimBA project")
    print("="*60)
    
    import pandas as pd
    
    # Paths
    csv_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}_dlc.csv")
    if not os.path.exists(csv_pattern):
        # Try the DLC raw CSV
        csv_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}*DLC*.csv")
        csvs = glob.glob(csv_pattern)
        if not csvs:
            print("  ERROR: No CSV file found")
            return False
        csv_pattern = csvs[0]
    
    input_csv_dir = os.path.join(SIMBA_PROJECT, "csv", "input_csv")
    target_csv = os.path.join(input_csv_dir, f"{VIDEO_NAME}.csv")
    target_video = os.path.join(VIDEOS_DIR, f"{VIDEO_NAME}.mp4")
    
    # Check if already imported
    if os.path.exists(target_csv) and os.path.exists(target_video):
        print("  Already imported!")
        return True
    
    # Clean CSV (flatten multi-level headers to SimBA format)
    print(f"  Reading DLC CSV: {csv_pattern}")
    raw = pd.read_csv(csv_pattern, header=[0, 1, 2], index_col=0)
    
    # Flatten columns: bodypart_coord (e.g., nose_x, nose_y, nose_likelihood)
    new_cols = []
    for scorer, bp, coord in raw.columns:
        new_cols.append(f"{bp}_{coord}")
    raw.columns = new_cols
    
    raw.to_csv(target_csv, index=True)
    print(f"  Saved cleaned CSV: {target_csv} ({len(raw)} rows, {len(raw.columns)} cols)")
    
    # Copy video (ORIGINAL, not trimmed/downscaled)
    # We want SimBA to work on the High Quality video
    if not os.path.exists(target_video):
        shutil.copy2(INPUT_VIDEO, target_video)
        print(f"  Copied ORIGINAL video to: {target_video}")
    
    # Also copy to outlier_corrected_movement_location (skip outlier correction)
    outlier_dir = os.path.join(SIMBA_PROJECT, "csv", "outlier_corrected_movement_location")
    shutil.copy2(target_csv, os.path.join(outlier_dir, f"{VIDEO_NAME}.csv"))
    print("  Copied to outlier_corrected_movement_location (bypass outlier step)")
    
    # Update video_info.csv
    import cv2
    cap = cv2.VideoCapture(target_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    video_info_path = os.path.join(SIMBA_PROJECT, "logs", "video_info.csv")
    if os.path.exists(video_info_path):
        vi = pd.read_csv(video_info_path)
    else:
        vi = pd.DataFrame(columns=["Video", "fps", "Resolution_width", "Resolution_height",
                                     "Distance_in_mm", "pixels/mm"])
    
    # Remove old entry if exists
    vi = vi[vi["Video"] != VIDEO_NAME]
    new_entry = pd.DataFrame([{
        "Video": VIDEO_NAME,
        "fps": fps,
        "Resolution_width": w,
        "Resolution_height": h,
        "Distance_in_mm": 0,
        "pixels/mm": 1.0
    }])
    vi = pd.concat([vi, new_entry], ignore_index=True)
    vi.to_csv(video_info_path, index=False)
    print(f"  Updated video_info.csv with {VIDEO_NAME}")
    
    return True


def step5_extract_features():
    """Extract SimBA features."""
    print("\n" + "="*60)
    print("STEP 5: Extracting SimBA features")
    print("="*60)
    
    features_dir = os.path.join(SIMBA_PROJECT, "csv", "features_extracted")
    if os.path.exists(os.path.join(features_dir, f"{VIDEO_NAME}.csv")):
        print("  Features already extracted!")
        return True
    
    try:
        from simba.feature_extractors.feature_extractor_user_defined import UserDefinedFeatureExtractor
        extractor = UserDefinedFeatureExtractor(config_path=CONFIG_PATH)
        extractor.run()
        print("  Feature extraction complete!")
        return True
    except ImportError:
        print("  [WARN] SimBA not found in current environment. Respawning step with venv_310...")
        venv_python = os.path.abspath(os.path.join(PROJECT_DIR, "venv_310", "Scripts", "python.exe"))
        if not os.path.exists(venv_python):
             print(f"  [ERROR] venv_310 python not found at: {venv_python}")
             return False
        
        cmd = [venv_python, os.path.abspath(__file__), "--video", INPUT_VIDEO, "--step", "5"]
        if ZONES_JSON != "[]":
            cmd.extend(["--zones", ZONES_JSON])
            
        print(f"  Running: {' '.join(cmd)}")
        ret = subprocess.call(cmd)
        if ret != 0:
            print("  [ERROR] Feature extraction failed in venv_310")
            return False
        return True


def step6_run_inference():
    """Apply trained Grooming & Thigmotaxis classifiers."""
    print("\n" + "="*60)
    print("STEP 6: Running classifier inference")
    print("="*60)
    
    results_dir = os.path.join(SIMBA_PROJECT, "csv", "machine_results")
    if os.path.exists(os.path.join(results_dir, f"{VIDEO_NAME}.csv")):
        print("  Inference results already exist!")
        # Still show summary? Only if we can read it.
    
    try:
        from simba.model.inference_batch import InferenceBatch
        inferencer = InferenceBatch(config_path=CONFIG_PATH)
        inferencer.run()
        
        # Print summary
        import pandas as pd
        result_path = os.path.join(results_dir, f"{VIDEO_NAME}.csv")
        if os.path.exists(result_path):
            df = pd.read_csv(result_path)
            fps = 30.0
            total = len(df)
            g_frames = int(df["Grooming"].sum()) if "Grooming" in df.columns else 0
            t_frames = int(df["Thigmotaxis"].sum()) if "Thigmotaxis" in df.columns else 0
            print(f"\n  Results for {VIDEO_NAME}:")
            print(f"    Grooming:    {g_frames} frames ({g_frames/total*100:.1f}%) = {g_frames/fps:.1f}s")
            print(f"    Thigmotaxis: {t_frames} frames ({t_frames/total*100:.1f}%) = {t_frames/fps:.1f}s")
        return True
        
    except ImportError:
        print("  [WARN] SimBA not found in current environment. Respawning step with venv_310...")
        venv_python = os.path.abspath(os.path.join(PROJECT_DIR, "venv_310", "Scripts", "python.exe"))
        
        cmd = [venv_python, os.path.abspath(__file__), "--video", INPUT_VIDEO, "--step", "6"]
        if ZONES_JSON != "[]":
            cmd.extend(["--zones", ZONES_JSON])
            
        print(f"  Running: {' '.join(cmd)}")
        ret = subprocess.call(cmd)
        if ret != 0:
            print("  [ERROR] Inference failed in venv_310")
            return False
        return True


def step7_generate_video():
    """Generate annotated video with behavior overlays."""
    print("\n" + "="*60)
    print("STEP 7: Generating annotated video")
    print("="*60)
    
    import cv2
    import pandas as pd
    
    video_path = os.path.join(VIDEOS_DIR, f"{VIDEO_NAME}.mp4")
    results_path = os.path.join(SIMBA_PROJECT, "csv", "machine_results", f"{VIDEO_NAME}.csv")
    output_path = os.path.join(VIDEOS_DIR, f"{VIDEO_NAME}_behavior_annotated.mp4")
    
    # Use simba_render_video.py logic but adapted here or called as subprocess
    # Easier: Call simba_render_video.py as subprocess to reuse all logic
    import subprocess
    render_script = os.path.abspath(os.path.join("src", "scripts", "simba_render_video.py"))
    
    cmd = [
        sys.executable,
        render_script,
        "--video", video_path,
        "--csv", results_path,
        "--output", output_path,
        "--zones", ZONES_JSON
    ]
    
    print(f"  Running render script: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # The render script already re-encodes, so we just check for the output
    h264_path = output_path.replace("_annotated.mp4", "_h264.mp4") # Render script logic
    # Or strict output from render script if we passed --output?
    # Actually simba_render_video.py produces _behavior_annotated and _h264
    
    return True


def main():
    global INPUT_VIDEO, VIDEO_NAME, ZONES_JSON, TRIMMED_VIDEO
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", help="Input video path")
    parser.add_argument("--zones", help="Zones JSON string", default="[]")
    parser.add_argument("--step", help="Run specific step number (1-7)", default="")
    args = parser.parse_args()
    
    if args.video:
        INPUT_VIDEO = args.video
        base_name = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
        VIDEO_NAME = f"{base_name}_full" # Adding suffix to avoid collision
        TRIMMED_VIDEO = INPUT_VIDEO # Update global dep
        
    if args.zones:
        ZONES_JSON = args.zones

    print("="*60)
    print(f"  FULL PIPELINE: {VIDEO_NAME}")
    print(f"  Source: {INPUT_VIDEO}")
    print("="*60)
    
    steps = [
        ("Downscale video", step1_downscale_video),
        ("DLC analysis", step2_dlc_analysis),
        ("Convert H5 to CSV", step3_convert_h5),
        ("Import to SimBA", step4_import_to_simba),
        ("Extract features", step5_extract_features),
        ("Run inference", step6_run_inference),
        ("Generate annotated video", step7_generate_video),
    ]
    
    # Run specific step if requested
    if args.step:
        try:
            step_idx = int(args.step) - 1
            if 0 <= step_idx < len(steps):
                name, func = steps[step_idx]
                print(f"Running SINGLE step: {name}")
                func()
            else:
                print(f"Invalid step number: {args.step}")
        except ValueError:
            print("Step must be a number 1-7")
        return

    # Run remaining steps from detection? Or all?
    # Default behavior: Run all sequentially
    for name, func in steps:
        try:
            ok = func()
            if not ok:
                print(f"\n  FAILED at step: {name}")
                return
        except Exception as e:
            print(f"\n  ERROR at step '{name}': {e}")
            traceback.print_exc()
            return
    
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()
