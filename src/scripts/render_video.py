import cv2
import pandas as pd
import numpy as np
import os
import argparse
import json
from moviepy.editor import VideoFileClip

def render_labeled_video(video_path, csv_path, zones_json_str=None, min_confidence=0.65):
    """
    Generates a labeled video with skeleton and zone filtering, then re-encodes to H.264.
    """
    print(f"[RENDER] Starting for: {video_path}")
    print(f"[RENDER] CSV Source: {csv_path}")
    
    # Output paths
    temp_output_path = video_path.replace(".mp4", "_temp_labeled.mp4")
    final_output_path = video_path.replace(".mp4", "_labeled.mp4")

    # Load Data
    try:
        # Load DLC output (header=[1,2] for bodyparts/coords)
        df = pd.read_csv(csv_path, header=[1, 2])
        bodyparts = df.columns.levels[0].unique()
    except Exception as e:
        print(f"[RENDER] Error loading CSV: {e}")
        return False

    # Define Skeleton (Standard TopView Mouse)
    skeleton = [
        ('nose', 'left_ear'), ('nose', 'right_ear'), ('left_ear', 'neck'), ('right_ear', 'neck'),
        ('neck', 'mid_back'), ('mid_back', 'tail_base'),
        ('tail_base', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail_end')
    ]

    # Parse Zones
    valid_zones = []
    if zones_json_str:
        try:
            valid_zones = json.loads(zones_json_str)
            print(f"[RENDER] Loaded {len(valid_zones)} validation zones.")
        except Exception as e:
            print(f"[RENDER] Warning: Failed to parse zones JSON: {e}")

    # Helper: Check if point is in any valid zone
    def is_in_valid_zone(x, y, zones, margin=0):
        if not zones: return True # If no zones defined, everything is valid
        for z in zones:
            # Check for different possible key names depending on where JSON came from
            zx = z.get('Real X', z.get('x', z.get('left', 0)))
            zy = z.get('Real Y', z.get('y', z.get('top', 0)))
            zw = z.get('Real W', z.get('w', z.get('width', 0)))
            zh = z.get('Real H', z.get('h', z.get('height', 0)))
            
            x1 = zx - margin
            y1 = zy - margin
            x2 = zx + zw + margin
            y2 = zy + zh + margin
            
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        return False

    # Open Video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[RENDER] Error opening video stream")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Use mp4v for intermediate writing (OpenCV default)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    frame_idx = 0
    colors = {} 

    print("[RENDER] Processing frames...")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx >= len(df):
            break
            
        # Draw Zones (Visual Debugging)
        for z in valid_zones:
            zx = z.get('Real X', z.get('x', z.get('left', 0)))
            zy = z.get('Real Y', z.get('y', z.get('top', 0)))
            zw = z.get('Real W', z.get('w', z.get('width', 0)))
            zh = z.get('Real H', z.get('h', z.get('height', 0)))
            cv2.rectangle(frame, (zx, zy), (zx+zw, zy+zh), (100, 255, 100), 1)

        # Draw Skeleton
        for bp1, bp2 in skeleton:
            if bp1 in bodyparts and bp2 in bodyparts:
                try:
                    x1 = df.iloc[frame_idx][(bp1, 'x')]
                    y1 = df.iloc[frame_idx][(bp1, 'y')]
                    lk1 = df.iloc[frame_idx][(bp1, 'likelihood')]
                    
                    x2 = df.iloc[frame_idx][(bp2, 'x')]
                    y2 = df.iloc[frame_idx][(bp2, 'y')]
                    lk2 = df.iloc[frame_idx][(bp2, 'likelihood')]
                    
                    # Validate
                    valid_p1 = (lk1 > min_confidence) and is_in_valid_zone(x1, y1, valid_zones)
                    valid_p2 = (lk2 > min_confidence) and is_in_valid_zone(x2, y2, valid_zones)
                    
                    if valid_p1 and valid_p2:
                        if not (np.isnan(x1) or np.isnan(y1) or np.isnan(x2) or np.isnan(y2)):
                            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 1) 
                except KeyError:
                    pass

        # Draw Points
        for i, bp in enumerate(bodyparts):
            try:
                x = df.iloc[frame_idx][(bp, 'x')]
                y = df.iloc[frame_idx][(bp, 'y')]
                like = df.iloc[frame_idx][(bp, 'likelihood')]
                
                if like > min_confidence and is_in_valid_zone(x, y, valid_zones) and not np.isnan(x) and not np.isnan(y):
                    if bp not in colors:
                        np.random.seed(i)
                        colors[bp] = (int(np.random.randint(0, 255)), int(np.random.randint(0, 255)), int(np.random.randint(0, 255)))
                    cv2.circle(frame, (int(x), int(y)), 4, colors[bp], -1)
            except KeyError:
                pass

        out.write(frame)
        frame_idx += 1
        if frame_idx % 500 == 0:
            print(f"  Frame {frame_idx}")

    cap.release()
    out.release()
    print(f"[RENDER] Intermediate video saved: {temp_output_path}")

    # Re-encode to H.264 for Web Compatibility
    print(f"[RENDER] Re-encoding to H.264...")
    try:
        clip = VideoFileClip(temp_output_path)
        clip.write_videofile(final_output_path, codec='libx264', audio=False, logger=None)
        clip.close()
        
        # Cleanup temp
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            
        print(f"[RENDER] Final video ready: {final_output_path}")
        return True
    except Exception as e:
        print(f"[RENDER] Encoding failed: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--csv", required=True, help="Path to DLC CSV file")
    parser.add_argument("--zones", help="JSON string of valid zones")
    
    args = parser.parse_args()
    
    zones_json = None
    if args.zones:
        # Decode if passed as argument
        zones_json = args.zones

    render_labeled_video(args.video, args.csv, zones_json)
