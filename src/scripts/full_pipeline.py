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
import sys
import os
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path para poder importar 'src'
PROJECT_ROOT_PATH = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_PATH))

from src.config import PROJECT_ROOT, VIDEOS_DIR, FFMPEG_PATH

if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
    INPUT_VIDEO = sys.argv[1]
else:
    import glob
    videos = glob.glob(str(VIDEOS_DIR / "*.mp4"))
    if videos:
        INPUT_VIDEO = str(videos[0])
        print(f"[INFO] Usando video: {INPUT_VIDEO}")
    else:
        INPUT_VIDEO = ""
VIDEO_NAME = "R5B20_01mar24_full"
ZONES_JSON = "[]"

PROJECT_DIR = os.path.abspath(".")
SIMBA_PROJECT = os.path.join(
    PROJECT_DIR,
    "data",
    "simba_projects",
    "New folder",
    "thigmotaxis_optimizado",
    "project_folder",
)
CONFIG_PATH = os.path.join(SIMBA_PROJECT, "project_config.ini")
VIDEOS_DIR = os.path.join(SIMBA_PROJECT, "videos")
WORK_DIR = os.path.join(PROJECT_DIR, "videos_data")

TRIMMED_VIDEO    = INPUT_VIDEO  # Will be updated if a trimmed working copy is created
SUPERANIMAL_NAME = "superanimal_topviewmouse"
DOWNSCALE_FACTOR = 1.0          # Keep original resolution for DLC accuracy

# ── Hyperparámetros de inferencia (sobreescribibles con --batchsize / --video_adapt) ──
DLC_BATCHSIZE    = 32           # Default optimizado para 12GB VRAM (RTX 5070 Ti)
DLC_VIDEO_ADAPT  = False        # False = más rápido; True = mayor precisión en iluminación irregular

# ── Parámetros de Recorte Temporizado (Streamlit Pestaña 01) ─────────
TRIM_START = 0.0
TRIM_END   = 0.0

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
                    getattr(os, "add_dll_directory")(bin_path)
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


def step1_prepare_video():
    """Create a trimmed working copy when requested, without changing resolution."""
    print("\n" + "="*60)
    print("STEP 1: Preparing source video for DLC")
    print("="*60)
    
    global TRIMMED_VIDEO
    base = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
    trim_suffix = f"_trim{int(TRIM_START)}-{int(TRIM_END)}" if (TRIM_END > 0 and TRIM_END > TRIM_START) else ""
    if not trim_suffix:
        TRIMMED_VIDEO = INPUT_VIDEO
        print("  No temporal trim requested. DLC will use the original-resolution source video.")
        return True

    output_video = os.path.join(WORK_DIR, f"{base}{trim_suffix}.mp4")
    TRIMMED_VIDEO = output_video
    
    if os.path.exists(output_video):
        print(f"  Trimmed video already exists: {output_video}")
        return True
    
    if not FFMPEG_PATH:
        print("❌ ERROR: FFmpeg no encontrado. Instálalo o configura FFMPEG_PATH en .env")
        return False

    ffmpeg_exe = str(FFMPEG_PATH)
        
    cmd = [ffmpeg_exe, "-y"]
    
    # Inyectar recorte de video temporizado rápido preventivo (Rendimiento O(1))
    print(f"  [TIMELINE CUT] Recortando de {TRIM_START} a {TRIM_END} segundos")
    cmd.extend(["-ss", str(TRIM_START), "-to", str(TRIM_END)])

    cmd.extend([
        "-i", INPUT_VIDEO,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        output_video
    ])
    
    print(f"  Running: {' '.join(cmd)}")
    import subprocess
    ret = subprocess.call(cmd)
    
    if ret != 0:
        print("  ERROR: Video preparation failed")
        return False

    print(f"  Saved trimmed full-resolution video: {output_video}")
    return True


# Backward compatibility for older helpers that still import the previous name.
step1_downscale_video = step1_prepare_video


def resolve_prepared_video_path():
    base = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
    trim_suffix = f"_trim{int(TRIM_START)}-{int(TRIM_END)}" if (TRIM_END > 0 and TRIM_END > TRIM_START) else ""
    if trim_suffix:
        candidate = os.path.join(WORK_DIR, f"{base}{trim_suffix}.mp4")
        if os.path.exists(candidate):
            return candidate
    if TRIMMED_VIDEO and os.path.exists(TRIMMED_VIDEO):
        return TRIMMED_VIDEO
    return INPUT_VIDEO


def step2_dlc_analysis():
    """Run DeepLabCut SuperAnimal inference."""
    print("\n" + "="*60)
    print("STEP 2: Running DeepLabCut analysis (GPU)")
    print("="*60)

    global TRIMMED_VIDEO
    TRIMMED_VIDEO = resolve_prepared_video_path()
    
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
            
             cmd = [
                 venv_python,
                 os.path.abspath(__file__),
                 "--video", INPUT_VIDEO,
                 "--step", "2",
                 "--batchsize", str(DLC_BATCHSIZE),
                 "--trim_start", str(TRIM_START),
                 "--trim_end", str(TRIM_END),
             ]
             if DLC_VIDEO_ADAPT:
                 cmd.append("--video_adapt")
             print(f"  Running: {' '.join(cmd)}")
             import subprocess
             ret = subprocess.call(cmd)
             if ret != 0:
                 print("  [ERROR] DLC analysis failed in venv_310")
                 return False
             return True

    except ImportError:
        pass
    
    target_video = TRIMMED_VIDEO
    print("  DLC will analyze the original-resolution working copy.")
    
    from deeplabcut.modelzoo.api.superanimal_inference import video_inference
    
    print(f"  Analyzing (Fast Mode): {target_video}")
    print(f"  Model: {SUPERANIMAL_NAME}")
    
    video_inference(
        videos=[target_video],
        superanimal_name=SUPERANIMAL_NAME,
        videotype="mp4",
        batchsize=DLC_BATCHSIZE,    # Controlado por --batchsize (default 32)
    )
    print(f"  DLC analysis complete! [batchsize={DLC_BATCHSIZE}]")
    return True


def step3_convert_h5():
    """Convert H5 to SimBA-compatible CSV."""
    print("\n" + "="*60)
    print("STEP 3: Converting H5 to CSV")
    print("="*60)
    
    import pandas as pd

    global TRIMMED_VIDEO
    TRIMMED_VIDEO = resolve_prepared_video_path()
    
    # Matches DLC output for THIS video specifically
    base_name_no_ext = os.path.splitext(os.path.basename(TRIMMED_VIDEO))[0]
    h5_pattern = os.path.join(WORK_DIR, f"*{base_name_no_ext}*DLC*.h5")
    h5_files = glob.glob(h5_pattern)
    if not h5_files:
        print("  ERROR: No H5 file found from DLC analysis")
        return False
    
    h5_path = h5_files[0]
    csv_out = os.path.join(WORK_DIR, f"{VIDEO_NAME}_dlc.csv")

    bbox_h5 = os.path.join(WORK_DIR, f"{VIDEO_NAME}_bbox_constrained.h5")
    bbox_csv = os.path.join(WORK_DIR, f"{VIDEO_NAME}_bbox_constrained.csv")
    bbox_overlay = os.path.join(WORK_DIR, f"{VIDEO_NAME}_bbox_constraint.mp4")
    bbox_script = os.path.abspath(os.path.join("src", "scripts", "apply_dlc_bbox_constraint.py"))
    venv_311_python = os.path.abspath(os.path.join(PROJECT_DIR, "venv_311", "Scripts", "python.exe"))

    yolo_model_path = os.path.join(PROJECT_DIR, "yolo_tracker.pt")
    bbox_inputs = [path for path in (h5_path, TRIMMED_VIDEO, bbox_script, yolo_model_path) if os.path.exists(path)]
    bbox_needs_refresh = (not os.path.exists(bbox_h5))
    if not bbox_needs_refresh and bbox_inputs:
        bbox_needs_refresh = os.path.getmtime(bbox_h5) < max(os.path.getmtime(path) for path in bbox_inputs)

    if os.path.exists(csv_out) and os.path.exists(bbox_h5) and not bbox_needs_refresh:
        if os.path.getmtime(csv_out) >= os.path.getmtime(bbox_h5):
            print(f"  CSV already exists: {csv_out}")
            return True

    if not os.path.exists(venv_311_python):
        print(f"  ERROR: venv_311 python not found at {venv_311_python}")
        return False

    if bbox_needs_refresh:
        bbox_cmd = [
            venv_311_python,
            bbox_script,
            "--video", TRIMMED_VIDEO,
            "--pose", h5_path,
            "--output_pose", bbox_h5,
            "--output_video", bbox_overlay,
            "--output_csv", bbox_csv,
        ]
        print(f"  Running bbox constraint: {' '.join(bbox_cmd)}")
        ret = subprocess.call(bbox_cmd)
        if ret != 0 or not os.path.exists(bbox_h5):
            print("  ERROR: YOLO bbox constraint failed")
            return False
    else:
        print(f"  Reusing bbox-constrained pose: {bbox_h5}")

    h5_path = bbox_h5
    
    print(f"  Reading: {h5_path}")
    df = pd.read_hdf(h5_path)
    
    # Kept for compatibility if a scaled intermediary is ever reintroduced.
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

    csv_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}_dlc.csv")
    if not os.path.exists(csv_pattern):
        glob_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}*DLC*.csv")
        csvs = glob.glob(glob_pattern)
        if not csvs:
            print(f"  ERROR: No CSV file found (buscando '{glob_pattern}')")
            return False
        csv_pattern = csvs[0]

    if not csv_pattern or not os.path.isfile(csv_pattern):
        print(f"  ERROR: csv_pattern resolvió a una ruta inválida: '{csv_pattern}'")
        return False

    print(f"  Fuente DLC confirmada para SimBA: {csv_pattern}")
    print("  La sincronización real de pose/video/ROI se hará en el paso 5.")
    return True


def step5_extract_features():
    """Extract SimBA features."""
    print("\n" + "="*60)
    print("STEP 5: Extracting SimBA features")
    print("="*60)

    features_dir = os.path.join(SIMBA_PROJECT, "csv", "features_extracted")
    target_feature_path = os.path.join(features_dir, f"{VIDEO_NAME}.csv")
    if os.path.exists(target_feature_path):
        print("  Features already extracted!")
        return True

    csv_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}_dlc.csv")
    if not os.path.exists(csv_pattern):
        glob_pattern = os.path.join(WORK_DIR, f"{VIDEO_NAME}*DLC*.csv")
        csvs = glob.glob(glob_pattern)
        if not csvs:
            print(f"  ERROR: No CSV pose source found (buscando '{glob_pattern}')")
            return False
        csv_pattern = csvs[0]

    zones_path = ""
    if ZONES_JSON and ZONES_JSON != "[]":
        zones_path = os.path.join(WORK_DIR, f"{VIDEO_NAME}_zonas_temp.json")
        with open(zones_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(ZONES_JSON)

    bridge_script = os.path.abspath(os.path.join("src", "scripts", "compute_simba_features.py"))
    cmd = [
        sys.executable,
        bridge_script,
        "--input", csv_pattern,
        "--output", target_feature_path,
        "--project", os.path.dirname(SIMBA_PROJECT),
        "--video", INPUT_VIDEO,
        "--video_name", VIDEO_NAME,
    ]
    if zones_path:
        cmd.extend(["--zonas", zones_path])

    print(f"  Running bridge script: {' '.join(cmd)}")
    ret = subprocess.call(cmd)
    if ret != 0 or not os.path.exists(target_feature_path):
        print("  [ERROR] Feature extraction bridge failed")
        return False

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
    global DLC_BATCHSIZE, DLC_VIDEO_ADAPT

    parser = argparse.ArgumentParser(description="EPM Full Analysis Pipeline")
    parser.add_argument("--video",       help="Input video path")
    parser.add_argument("--zones",       help="Zones JSON string", default="[]")
    parser.add_argument("--step",        help="Run specific step number (1-7)", default="")
    parser.add_argument("--batchsize",   help="DLC inference batch size (default 32)",
                        type=int, default=32)
    parser.add_argument("--video_adapt", help="Enable DLC video adaptation (slower, more accurate)",
                        action="store_true", default=False)
    parser.add_argument("--trim_start",  help="Video trimming start boundary in seconds", type=float, default=0.0)
    parser.add_argument("--trim_end",    help="Video trimming end boundary in seconds", type=float, default=0.0)
    args = parser.parse_args()

    # Sobreescribir globales con valores de CLI
    DLC_BATCHSIZE   = args.batchsize
    DLC_VIDEO_ADAPT = args.video_adapt
    
    global TRIM_START, TRIM_END
    TRIM_START = args.trim_start
    TRIM_END   = args.trim_end

    if args.video:
        INPUT_VIDEO = args.video.strip()
        if not INPUT_VIDEO:
            print("[FATAL] --video recibió una ruta vacía. Abortando.")
            sys.exit(1)
        if not os.path.exists(INPUT_VIDEO):
            print(f"[FATAL] El video no existe en disco: '{INPUT_VIDEO}'. Abortando.")
            sys.exit(1)
        base_name = os.path.splitext(os.path.basename(INPUT_VIDEO))[0]
        VIDEO_NAME = f"{base_name}_full"  # Adding suffix to avoid collision
        TRIMMED_VIDEO = INPUT_VIDEO       # Update global dep
    else:
        # No --video provided; validate the hardcoded default
        if not INPUT_VIDEO or not os.path.exists(INPUT_VIDEO):
            print(f"[FATAL] INPUT_VIDEO hardcoded no existe o está vacío: '{INPUT_VIDEO}'. Abortando.")
            sys.exit(1)

    if args.zones:
        ZONES_JSON = args.zones

    print("="*60)
    print(f"  FULL PIPELINE: {VIDEO_NAME}")
    print(f"  Source: {INPUT_VIDEO}")
    print(f"  DLC Config: batchsize={DLC_BATCHSIZE}, video_adapt={DLC_VIDEO_ADAPT}")
    print(f"  VRAM Estimada: {'~10GB' if DLC_BATCHSIZE >= 32 else '~6GB'}")
    print("="*60)
    
    steps = [
        ("Prepare source video", step1_prepare_video),
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
    done_path = os.path.join(PROJECT_DIR, "logs", "pipeline_dlc.done")
    os.makedirs(os.path.join(PROJECT_DIR, "logs"), exist_ok=True)

    exit_code = 1  # Default: error
    for name, func in steps:
        try:
            ok = func()
            if not ok:
                print(f"\n  FAILED at step: {name}")
                with open(done_path, "w") as f: f.write("1")
                return
        except Exception as e:
            print(f"\n  ERROR at step '{name}': {e}")
            traceback.print_exc()
            with open(done_path, "w") as f: f.write("1")
            return

    exit_code = 0
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE!")
    print("="*60)

    # Señalizar a Streamlit que el proceso terminó exitosamente
    with open(done_path, "w") as f:
        f.write(str(exit_code))


if __name__ == "__main__":
    main()
