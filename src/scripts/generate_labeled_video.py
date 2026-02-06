import cv2
import pandas as pd
import numpy as np
import os

video_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133.mp4"
csv_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133DLC_snapshot-200000.csv"
output_path = video_path.replace(".mp4", "_labeled.mp4")

print(f"Generating labeled video manually...")
print(f"Video: {video_path}")
print(f"CSV: {csv_path}")

# Load Data
try:
    df = pd.read_csv(csv_path, header=[1, 2]) # Skip row 0 (scorer), use rows 1 (bodyparts) and 2 (coords) as header
    # Row 2 in file is header[1] in pandas which contains x,y,likelihood
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit(1)

# Bodyparts list (unique from level 0 of columns)
bodyparts = df.columns.levels[0].unique()
print(f"Bodyparts: {bodyparts}")

# Define Skeleton (Approximate for TopView Mouse)
skeleton = [
    ('nose', 'left_ear'), ('nose', 'right_ear'), ('left_ear', 'neck'), ('right_ear', 'neck'),
    ('neck', 'mid_back'), ('mid_back', 'tail_base'),
    ('tail_base', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail_end')
]

# Open Video
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error opening video stream")
    exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

frame_idx = 0
colors = {} # Color cache per bodypart

# Zone Definitions (Canvas Coordinates from Screenshot)
CANVAS_WIDTH = 800
VALID_ZONES_CANVAS = [
    # Top Arm (Brazo Abierto 1) - TIGHTENED: y=16->40 to avoid top edge
    {'x': 377, 'y': 40, 'w': 43, 'h': 155},   
    
    # Bottom Arm (Brazo Cerrado 2)
    {'x': 374, 'y': 248, 'w': 40, 'h': 184}, 
    
    # Left Arm (Centro 3) - TIGHTENED: x=131->180 to avoid black bag
    {'x': 180, 'y': 189, 'w': 191, 'h': 60}, 
    
    # Right Arm (Centro 4)
    {'x': 422, 'y': 199, 'w': 241, 'h': 52},
    
    # Center (Intersection)
    {'x': 376, 'y': 198, 'w': 43, 'h': 47}, 
]

# Calculate Scale Factor
scale_factor = width / CANVAS_WIDTH
print(f"Video Width: {width}, Canvas Width: {CANVAS_WIDTH}, Scale Factor: {scale_factor}")

# Scale Zones to Video Resolution
VALID_ZONES_REAL = []
for z in VALID_ZONES_CANVAS:
    VALID_ZONES_REAL.append({
        'x': int(z['x'] * scale_factor),
        'y': int(z['y'] * scale_factor),
        'w': int(z['w'] * scale_factor),
        'h': int(z['h'] * scale_factor)
    })

def is_in_valid_zone_real(x, y, margin=20):
    for zone in VALID_ZONES_REAL:
        x1 = zone['x'] - margin
        y1 = zone['y'] - margin
        x2 = zone['x'] + zone['w'] + margin
        y2 = zone['y'] + zone['h'] + margin
        if x1 <= x <= x2 and y1 <= y <= y2:
            return True
    return False

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    if frame_idx >= len(df):
        break

    # VISUALIZE ZONES: Draw rectangles for debugging
    for z in VALID_ZONES_REAL:
        margin = 20
        # Draw the effective zone (including margin) in faint green/blue
        cv2.rectangle(frame, 
                      (z['x'] - margin, z['y'] - margin), 
                      (z['x'] + z['w'] + margin, z['y'] + z['h'] + margin), 
                      (100, 255, 100), 1)

    # 1. Draw Skeleton Lines
    for bp1, bp2 in skeleton:
        if bp1 in bodyparts and bp2 in bodyparts:
            try:
                x1 = df.iloc[frame_idx][(bp1, 'x')]
                y1 = df.iloc[frame_idx][(bp1, 'y')]
                lk1 = df.iloc[frame_idx][(bp1, 'likelihood')]
                
                x2 = df.iloc[frame_idx][(bp2, 'x')]
                y2 = df.iloc[frame_idx][(bp2, 'y')]
                lk2 = df.iloc[frame_idx][(bp2, 'likelihood')]
                
                min_confidence = 0.65
                valid_p1 = (lk1 > min_confidence) and is_in_valid_zone_real(x1, y1)
                valid_p2 = (lk2 > min_confidence) and is_in_valid_zone_real(x2, y2)
                
                if valid_p1 and valid_p2:
                    if not (np.isnan(x1) or np.isnan(y1) or np.isnan(x2) or np.isnan(y2)):
                        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 1) 
            except KeyError:
                pass 

    # 2. Draw Points
    for i, bp in enumerate(bodyparts):
        try:
            x = df.iloc[frame_idx][(bp, 'x')]
            y = df.iloc[frame_idx][(bp, 'y')]
            like = df.iloc[frame_idx][(bp, 'likelihood')]
            
            # REFINEMENT: Apply same filters
            if like > 0.65 and is_in_valid_zone_real(x, y) and not np.isnan(x) and not np.isnan(y):
                # Unique color for each bodypart
                if bp not in colors:
                    np.random.seed(i)
                    colors[bp] = (int(np.random.randint(0, 255)), int(np.random.randint(0, 255)), int(np.random.randint(0, 255)))
                
                cv2.circle(frame, (int(x), int(y)), 4, colors[bp], -1)
        except KeyError:
            pass

    out.write(frame)
    frame_idx += 1
    if frame_idx % 50 == 0:
        print(f"Processed frame {frame_idx}")

cap.release()
out.release()
print(f"Done! Saved to {output_path}")
