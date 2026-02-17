import os
import shutil
import glob
from simba.utils.enums import DirNames

# Config
PROJECT_PATH = os.path.abspath(os.path.join("data", "simba_projects", "SimBA_EPM_Analysis"))
PROJECT_FOLDER = os.path.join(PROJECT_PATH, "project_folder")
INPUT_CSV_DIR = os.path.join(PROJECT_FOLDER, DirNames.CSV.value, DirNames.INPUT_CSV.value)
VIDEOS_DIR = os.path.join(PROJECT_FOLDER, DirNames.VIDEOS.value)
SOURCE_DATA = os.path.abspath("videos_data")

def import_data():
    print(f"Importing data from {SOURCE_DATA} to {PROJECT_FOLDER}...")
    
    # 1. Find all DLC CSVs
    # Pattern: *DLC_snapshot-200000.csv (or similar)
    csv_files = glob.glob(os.path.join(SOURCE_DATA, "*DLC_snapshot*.csv"))
    
    if not csv_files:
        print("No CSV files found in source directory!")
        return

    import pandas as pd
    
    print(f"Starting manual import for {len(csv_files)} files...")
    
    for csv_file in csv_files:
        try:
            basename = os.path.basename(csv_file)
            # Video name inference: control2_Control_trimmed_102_133DLC_snapshot... -> control2_Control_trimmed_102_133
            # Remove "DLC_snapshot..."
            # Simple heuristic: Split by "DLC" and take first part?
            # Or just take everything before the LAST "DLC" occurrence.
            
            # Example: control2..._trimmed_102_133DLC_snapshot.csv
            video_name_base = basename.split("DLC")[0]
            
            # SimBA expects Video and CSV to have SAME name (e.g. Video1.mp4 and Video1.csv)
            # Let's use the clean video name as the canonical name.
            
            print(f"Processing: {basename} -> {video_name_base}")
            
            # 1. Read DLC CSV
            df = pd.read_csv(csv_file, header=[0, 1, 2], index_col=0)
            
            # 2. Flatten Columns
            # DLC: (Scorer, Bodypart, Coord) -> nose_x, nose_y, nose_likelihood
            new_columns = []
            for col in df.columns:
                # col is tuple: (scorer, bodypart, coord)
                bp = col[1]
                coord = col[2] # x, y, likelihood
                
                # SimBA expects: nose_x, nose_y, nose_p
                # "likelihood" in DLC -> "p" in SimBA usually, or "likelihood" is fine.
                # Let's check SimBA docs or standard. SimBA often uses 'p'.
                
                if coord == 'likelihood':
                    suffix = 'p'
                else:
                    suffix = coord # x or y
                
                new_columns.append(f"{bp}_{suffix}")
                
            df.columns = new_columns
            
            # 3. Save to SimBA Input CSV folder
            # Filename: VideoName.csv
            dest_csv_path = os.path.join(INPUT_CSV_DIR, f"{video_name_base}.csv")
            df.to_csv(dest_csv_path)
            print(f"Saved CSV: {dest_csv_path}")
            
            # 4. Copy Video if exists
            # Look for input video with matching name
            # Pattern: video_name_base + .mp4 (or .avi etc)
            possible_videos = glob.glob(os.path.join(SOURCE_DATA, f"{video_name_base}.mp4"))
            # Filter out "labeled"
            possible_videos = [v for v in possible_videos if "labeled" not in v]

            if possible_videos:
                src_video = possible_videos[0]
                dest_video = os.path.join(VIDEOS_DIR, f"{video_name_base}.mp4")
                if not os.path.exists(dest_video):
                    shutil.copy(src_video, dest_video)
                    print(f"Copied Video: {dest_video}")
                else:
                    print(f"Video exists: {dest_video}")
            else:
                 print(f"⚠️ Video not found for {video_name_base}")
                 
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")


if __name__ == "__main__":
    import_data()
