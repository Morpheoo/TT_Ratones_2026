"""
Full pipeline: Analyze a new video with trained SimBA classifiers.
Steps:
  1. Trim video to 2 minutes
  2. Run DeepLabCut SuperAnimal analysis
  3. Convert H5 to CSV for SimBA
  4. Import into SimBA project
  5. Extract features
  6. Run inference with trained classifiers
  7. Generate annotated video with behavior overlays
"""
import os
import sys
import shutil
import glob
import configparser
import site
import traceback

import argparse

# ── Configuration ──────────────────────────────────────────────
INPUT_VIDEO = r"C:\Users\chavi\OneDrive\Desktop\dataser_tt_mejorado\R5B20_01mar24.mp4"
VIDEO_NAME = "R5B20_01mar24_full"
ZONES_JSON = "[]"
# TRIM_START = 30       # seconds to skip at the start
# TRIM_DURATION = 120   # 2 minutes

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
    
    from deeplabcut.modelzoo.api.superanimal_inference import video_inference
    
    print(f"  Analyzing (Fast Mode): {TRIMMED_VIDEO}")
    print(f"  Model: {SUPERANIMAL_NAME}")
    
    video_inference(
        videos=[TRIMMED_VIDEO],
        superanimal_name=SUPERANIMAL_NAME,
        videotype="mp4",
        batchsize=16,
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
    
    from simba.feature_extractors.feature_extractor_user_defined import UserDefinedFeatureExtractor
    
    extractor = UserDefinedFeatureExtractor(config_path=CONFIG_PATH)
    extractor.run()
    print("  Feature extraction complete!")
    return True


def step6_run_inference():
    """Apply trained Grooming & Thigmotaxis classifiers."""
    print("\n" + "="*60)
    print("STEP 6: Running classifier inference")
    print("="*60)
    
    results_dir = os.path.join(SIMBA_PROJECT, "csv", "machine_results")
    if os.path.exists(os.path.join(results_dir, f"{VIDEO_NAME}.csv")):
        print("  Inference results already exist!")
        # Still show summary
    
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
        g_frames = int(df["Grooming"].sum())
        t_frames = int(df["Thigmotaxis"].sum())
        print(f"\n  Results for {VIDEO_NAME}:")
        print(f"    Grooming:    {g_frames} frames ({g_frames/total*100:.1f}%) = {g_frames/fps:.1f}s")
        print(f"    Thigmotaxis: {t_frames} frames ({t_frames/total*100:.1f}%) = {t_frames/fps:.1f}s")
    
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


    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    
    # Pre-compute totals
    total_g_frames = int(df["Grooming"].sum())
    total_t_frames = int(df["Thigmotaxis"].sum())
    total_g_s = total_g_frames / fps
    total_t_s = total_t_frames / fps
    
    # Colors
    GREEN = (0, 200, 0)
    BLUE = (200, 100, 0)
    WHITE = (255, 255, 255)
    DARK_BG = (30, 30, 30)
    
    g_cumul = 0
    t_cumul = 0
    
    print(f"  Rendering {total_frames} frames ({w}x{h} @ {fps}fps)...")
    
    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        
        g_prob = float(df.iloc[i].get("Probability_Grooming", 0))
        t_prob = float(df.iloc[i].get("Probability_Thigmotaxis", 0))
        g_on = int(df.iloc[i].get("Grooming", 0)) == 1
        t_on = int(df.iloc[i].get("Thigmotaxis", 0)) == 1
        
        if g_on: g_cumul += 1
        if t_on: t_cumul += 1
        
        g_time = g_cumul / fps
        t_time = t_cumul / fps
        cur_time = i / fps
        total_time = total_frames / fps
        
        # Panel
        panel_w, panel_h = 340, 170
        px = w - panel_w - 10
        py = 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, py), (px+panel_w, py+panel_h), DARK_BG, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        m = int(cur_time) // 60
        s = cur_time - m * 60
        cv2.putText(frame, f"SimBA Behavior Detection  [{m}:{s:05.2f}]",
                    (px+10, py+22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1, cv2.LINE_AA)
        
        # Grooming
        by = py + 40
        color = GREEN if g_on else (80, 80, 80)
        cv2.putText(frame, "Grooming", (px+10, by+12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        bx = px + 110
        cv2.rectangle(frame, (bx, by), (bx+120, by+16), (60,60,60), -1)
        cv2.rectangle(frame, (bx, by), (bx+int(120*g_prob), by+16), GREEN, -1)
        cv2.putText(frame, f"{g_prob:.0%}", (bx+125, by+13), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)
        if g_on:
            cv2.putText(frame, "DETECTED", (px+10, by+30), cv2.FONT_HERSHEY_SIMPLEX, 0.32, GREEN, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{g_time:.1f}s", (px+panel_w-55, by+30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, GREEN, 1, cv2.LINE_AA)
        
        # Thigmotaxis
        by = py + 80
        color = BLUE if t_on else (80, 80, 80)
        cv2.putText(frame, "Thigmotaxis", (px+10, by+12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        cv2.rectangle(frame, (bx, by), (bx+120, by+16), (60,60,60), -1)
        cv2.rectangle(frame, (bx, by), (bx+int(120*t_prob), by+16), BLUE, -1)
        cv2.putText(frame, f"{t_prob:.0%}", (bx+125, by+13), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)
        if t_on:
            cv2.putText(frame, "DETECTED", (px+10, by+30), cv2.FONT_HERSHEY_SIMPLEX, 0.32, BLUE, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{t_time:.1f}s", (px+panel_w-55, by+30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLUE, 1, cv2.LINE_AA)
        
        # Summary
        g_pct = total_g_s / total_time * 100
        t_pct = total_t_s / total_time * 100
        cv2.putText(frame, f"Total: G={total_g_s:.1f}s ({g_pct:.1f}%)  T={total_t_s:.1f}s ({t_pct:.1f}%)",
                    (px+10, py+135), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180,180,180), 1, cv2.LINE_AA)
        
        # Timestamp
        m2 = int(total_time) // 60
        s2 = total_time - m2 * 60
        cv2.putText(frame, f"Frame: {i}/{total_frames}  |  {m}:{s:05.2f} / {m2}:{s2:05.2f}",
                    (10, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA)
        
        # Borders
        if g_on:
            cv2.rectangle(frame, (0,0), (w-1,h-1), GREEN, 3)
        if t_on:
            cv2.rectangle(frame, (3,3), (w-4,h-4), BLUE, 3)
        
        out.write(frame)
        if (i+1) % 600 == 0:
            print(f"    {i+1}/{total_frames} frames...")
    
    cap.release()
    out.release()
    
    # Re-encode to H.264 with ffmpeg
    h264_path = output_path.replace("_annotated.mp4", "_h264.mp4")
    ffmpeg_exe = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
    if os.path.exists(ffmpeg_exe):
        print("  Re-encoding to H.264...")
        os.system(f'"{ffmpeg_exe}" -y -i "{output_path}" -c:v libx264 -preset fast -crf 23 "{h264_path}"')
        print(f"  H.264 video: {h264_path}")
    else:
        h264_path = output_path
        print("  ffmpeg not found, using mp4v codec")
    
    print(f"\n  FINAL VIDEO: {h264_path}")
    return True


def main():
    global INPUT_VIDEO, VIDEO_NAME, ZONES_JSON, TRIMMED_VIDEO
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", help="Input video path")
    parser.add_argument("--zones", help="Zones JSON string", default="[]")
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
