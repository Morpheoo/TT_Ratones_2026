import os
import pandas as pd
import cv2
import glob

# Config
PROJECT_PATH = os.path.abspath(os.path.join("data", "simba_projects", "SimBA_EPM_Analysis"))
PROJECT_FOLDER = os.path.join(PROJECT_PATH, "project_folder")
LOGS_DIR = os.path.join(PROJECT_FOLDER, "logs")
VIDEOS_DIR = os.path.join(PROJECT_FOLDER, "videos")
VIDEO_INFO_PATH = os.path.join(LOGS_DIR, "video_info.csv")

def setup_video_info():
    print(f"Setting up video_info.csv in {LOGS_DIR}...")
    
    # Columns expected by SimBA
    columns = ["Video", "fps", "Resolution_width", "Resolution_height", "Distance_in_mm", "pixels/mm", "Generated_at"]
    
    data = []
    
    # Find all videos in project
    video_files = glob.glob(os.path.join(VIDEOS_DIR, "*.mp4"))
    
    for video_file in video_files:
        basename = os.path.basename(video_file)
        name_no_ext = os.path.splitext(basename)[0]
        
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            print(f"Error opening {video_file}")
            continue
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Heuristic for pixels/mm.
        # Ideally user defines this.
        # For EPM, if we assume an arm is ~50cm (500mm), and in video it is X pixels...
        # Let's set a dummy default for now to avoid DivByZero.
        # Default: 1.0 (1 pixel = 1 mm is wrong but safe for math).
        # Better: 10 pixels / mm? 
        # Resolution 1280x720. EPM huge?
        # Let's use 1.0 to avoid crash. 
        # User can calibrate later using SimBA GUI if they want precise velocity units (mm/s).
        px_per_mm = 1.0 
        dist_mm = 1.0 # arbitrary
        
        data.append({
            "Video": name_no_ext, # SimBA uses name WITHOUT extension in video_info? check.
            "fps": fps,
            "Resolution_width": width,
            "Resolution_height": height,
            "Distance_in_mm": dist_mm,
            "pixels/mm": px_per_mm,
            "Generated_at": pd.Timestamp.now()
        })
        print(f"Added info for {name_no_ext}: {width}x{height} @ {fps}fps")
        
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(VIDEO_INFO_PATH, index=False)
    print(f"Saved video_info.csv to {VIDEO_INFO_PATH}")

if __name__ == "__main__":
    setup_video_info()
