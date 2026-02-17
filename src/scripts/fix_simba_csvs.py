import sys
import os
import glob
import cv2
import pandas as pd

# Path to SimBA inputs
PROJECT_DIR = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\SimBA_EPM_Analysis\project_folder"
CSV_DIR = os.path.join(PROJECT_DIR, "csv", "input_csv")
VIDEO_DIR = os.path.join(PROJECT_DIR, "videos")

def fix_csv(video_path, csv_path):
    print(f"\nChecking: {os.path.basename(video_path)}")
    
    # 1. Get video frame count
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ERROR: Could not open video: {video_path}")
        return
    
    video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    print(f"  Video Frames: {video_frames}")
    
    # 2. Get CSV row count
    # Note: SimBA CSVs usually have a header row (or multi-header).
    # DLC output usually has 3 header rows. SimBA import might stripped them?
    # Let's check format. usually index_col=0 if frame numbers are there.
    
    try:
        df = pd.read_csv(csv_path, header=[0,1,2], index_col=0)
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        # Try without multi-index if already imported to SimBA format?
        # SimBA inputs usually keep DLC format.
        try:
            df = pd.read_csv(csv_path)
        except:
            return

    csv_frames = len(df)
    print(f"  CSV Frames:   {csv_frames}")
    
    diff = video_frames - csv_frames
    
    if diff == 0:
        print("  MATCH: No fix needed.")
        return
        
    if diff < 0:
        print(f"  WARNING: CSV has MORE frames than video ({abs(diff)}). Trimming...")
        df = df.iloc[:video_frames]
        # Save
        df.to_csv(csv_path)
        print("  Fixed (Trimmed).")
        return

    print(f"  MISMATCH: Video has {diff} more frames. Padding CSV...")
    
    # Pad with last row
    last_row = df.iloc[-1]
    new_rows = pd.DataFrame([last_row] * diff)
    
    # Concatenate
    df_fixed = pd.concat([df, new_rows], ignore_index=True)
    
    # Fix index if it was frame numbers
    # Actually, let's just write keeping index/header structure roughly correct.
    # If read with header=[0,1,2], writing it back matches DLC format.
    
    df_fixed.to_csv(csv_path)
    print(f"  Fixed (Padded {diff} rows). New length: {len(df_fixed)}")

def main():
    # Find all videos in SimBA project
    videos = glob.glob(os.path.join(VIDEO_DIR, "*.mp4"))
    
    # List of CSV subdirectories to check
    csv_subdirs = [
        "input_csv",
        "outlier_corrected_movement_location",
        "features_extracted",
        "targets_inserted"
    ]

    for video_path in videos:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Check all possible CSV locations
        for subdir in csv_subdirs:
            csv_path = os.path.join(PROJECT_DIR, "csv", subdir, f"{base_name}.csv")
            
            if os.path.exists(csv_path):
                print(f"Checking {subdir}: {base_name}")
                fix_csv(video_path, csv_path)
            # else:
            #     print(f"Skipping {subdir}/{base_name} (Not found)")

if __name__ == "__main__":
    main()
