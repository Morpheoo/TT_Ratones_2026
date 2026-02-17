
import pandas as pd
import os
import shutil

# Configuration
SIMBA_PROJECT_DIR = r"data/simba_projects/SimBA_EPM_Analysis"
INPUT_CSV_PATH = r"videos_data/prueba_real_2minDLC_snapshot-200000.csv"
INPUT_VIDEO_PATH = r"videos_data/prueba_real_2min.mp4"

def import_single_video_data():
    if not os.path.exists(SIMBA_PROJECT_DIR):
        print(f"Error: SimBA project not found at {SIMBA_PROJECT_DIR}")
        return

    csv_dir = os.path.join(SIMBA_PROJECT_DIR, "project_folder", "csv", "input_csv")
    video_dir = os.path.join(SIMBA_PROJECT_DIR, "project_folder", "videos")
    
    # 1. Process and Import CSV
    print(f"Reading DLC CSV: {INPUT_CSV_PATH}")
    try:
        # Read the multi-header CSV
        df = pd.read_csv(INPUT_CSV_PATH, header=[0, 1, 2], index_col=0)
        
        # Flatten headers
        new_columns = []
        for col in df.columns:
            # col is a tuple: ('scorer', 'bodypart', 'coord')
            # changing to 'bodypart_coord' (e.g., 'nose_x', 'nose_y', 'nose_p')
            bodypart = col[1]
            coord = col[2]
            if coord == 'likelihood':
                coord = 'p'
            new_columns.append(f"{bodypart}_{coord}")
            
        df.columns = new_columns
        
        # Save to SimBA input folder
        # Filename should match video name
        output_name = "prueba_real_2min.csv"
        output_path = os.path.join(csv_dir, output_name)
        df.to_csv(output_path)
        print(f"Saved cleaned CSV to: {output_path}")
        
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return

    # 2. Import Video
    print(f"Copying video: {INPUT_VIDEO_PATH}")
    try:
        if os.path.exists(INPUT_VIDEO_PATH):
            shutil.copy(INPUT_VIDEO_PATH, video_dir)
            print(f"Video copied to: {video_dir}")
        else:
            print(f"Warning: Video file not found at {INPUT_VIDEO_PATH}")
            
    except Exception as e:
        print(f"Error copying video: {e}")

if __name__ == "__main__":
    import_single_video_data()
