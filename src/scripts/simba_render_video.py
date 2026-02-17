"""
Generate an annotated video with SimBA behavior predictions overlaid.
Shows Grooming (green) and Thigmotaxis (blue) detections with probability bars.
"""
import cv2
import pandas as pd
import numpy as np
import os
import sys

# Paths
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser(description="Render SimBA behavior video")
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--csv", required=True, help="Path to machine results CSV")
    parser.add_argument("--output", help="Path to output video (optional)")
    parser.add_argument("--zones", help="JSON string of zones configuration", default="[]")
    return parser.parse_args()

# Colors (BGR)
GREEN = (0, 200, 0)
BLUE = (200, 100, 0)
RED = (0, 0, 220)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (30, 30, 30)

def fmt_time(seconds):
    """Format seconds as M:SS.s"""
    m = int(seconds) // 60
    s = seconds - m * 60
    return f"{m}:{s:05.2f}"

def check_zone(x, y, zones):
    """Check which zone the point (x,y) is in."""
    for zone in zones:
        left = zone.get("left", 0)
        top = zone.get("top", 0)
        width = zone.get("width", 0)
        height = zone.get("height", 0)
        if left <= x <= left + width and top <= y <= top + height:
            return zone.get("Nombre Zona", "Unknown")
    return "Outside"

def draw_zone_panel(frame, current_zone, zone_times, fps):
    """Draw a panel showing time spent in each zone."""
    h, w = frame.shape[:2]
    panel_w = 340
    # Dynamic height based on number of zones
    panel_h = 60 + (len(zone_times) * 20)
    panel_x = 10
    panel_y = 10
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), DARK_BG, -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    cv2.putText(frame, "Zone Statistics", (panel_x + 10, panel_y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 2, cv2.LINE_AA) # Bold title
                
    cv2.putText(frame, f"Current: {current_zone}", (panel_x + 10, panel_y + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA) # Yellow for current
    
    y_off = panel_y + 70
    total_time = sum(zone_times.values())
    if total_time == 0: total_time = 1
    
    for zone_name, frames in zone_times.items():
        seconds = frames / fps
        pct = (frames / fps) / (total_time / fps if total_time > 0 else 1) * 100
        
        # Highlight active zone
        color = (0, 255, 0) if zone_name == current_zone else (200, 200, 200)
        font_weight = 2 if zone_name == current_zone else 1
        
        text = f"{zone_name}: {seconds:.1f}s ({pct:.1f}%)"
        cv2.putText(frame, text, (panel_x + 10, y_off),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, font_weight, cv2.LINE_AA)
        y_off += 20
        
    return frame

def draw_behavior_panel(frame, grooming_prob, thigmotaxis_prob, grooming_on, thigmotaxis_on,
                        frame_idx, total_frames, fps, grooming_time_s, thigmotaxis_time_s,
                        total_grooming_s, total_thigmotaxis_s):
    """Draw a behavior detection panel on the frame."""
    h, w = frame.shape[:2]
    
    # Semi-transparent overlay panel (top-right)
    panel_w = 340
    panel_h = 170
    panel_x = w - panel_w - 10
    panel_y = 10
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), DARK_BG, -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    # Title
    current_time = frame_idx / fps if fps > 0 else 0
    cv2.putText(frame, f"SimBA Behavior Detection  [{fmt_time(current_time)}]",
                (panel_x + 10, panel_y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1, cv2.LINE_AA)
    
    # --- Grooming ---
    bar_y = panel_y + 40
    color = GREEN if grooming_on else (80, 80, 80)
    
    cv2.putText(frame, "Grooming", (panel_x + 10, bar_y + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    
    # Probability bar
    bar_x = panel_x + 110
    bar_w = 120
    bar_h = 16
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * grooming_prob)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), GREEN, -1)
    cv2.putText(frame, f"{grooming_prob:.0%}", (bar_x + bar_w + 5, bar_y + 13),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)
    
    # Cumulative time for Grooming
    time_label = f"{grooming_time_s:.1f}s"
    if grooming_on:
        cv2.putText(frame, "DETECTED", (panel_x + 10, bar_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, GREEN, 1, cv2.LINE_AA)
    cv2.putText(frame, time_label, (panel_x + panel_w - 55, bar_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, GREEN, 1, cv2.LINE_AA)
    
    # --- Thigmotaxis ---
    bar_y = panel_y + 80
    color = BLUE if thigmotaxis_on else (80, 80, 80)
    
    cv2.putText(frame, "Thigmotaxis", (panel_x + 10, bar_y + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * thigmotaxis_prob)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), BLUE, -1)
    cv2.putText(frame, f"{thigmotaxis_prob:.0%}", (bar_x + bar_w + 5, bar_y + 13),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)
    
    # Cumulative time for Thigmotaxis
    time_label = f"{thigmotaxis_time_s:.1f}s"
    if thigmotaxis_on:
        cv2.putText(frame, "DETECTED", (panel_x + 10, bar_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, BLUE, 1, cv2.LINE_AA)
    cv2.putText(frame, time_label, (panel_x + panel_w - 55, bar_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLUE, 1, cv2.LINE_AA)
    
    # --- Summary line (total times) ---
    summary_y = panel_y + 135
    total_video_s = total_frames / fps if fps > 0 else 1
    g_pct = total_grooming_s / total_video_s * 100
    t_pct = total_thigmotaxis_s / total_video_s * 100
    cv2.putText(frame, f"Total: G={total_grooming_s:.1f}s ({g_pct:.1f}%)  T={total_thigmotaxis_s:.1f}s ({t_pct:.1f}%)",
                (panel_x + 10, summary_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)
    
    # Frame counter + timestamp (bottom-left)
    cv2.putText(frame, f"Frame: {frame_idx}/{total_frames}  |  {fmt_time(current_time)} / {fmt_time(total_video_s)}",
                (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA)
    
    # Color border when behavior detected
    if grooming_on:
        cv2.rectangle(frame, (0, 0), (w-1, h-1), GREEN, 3)
    if thigmotaxis_on:
        cv2.rectangle(frame, (3, 3), (w-4, h-4), BLUE, 3)
    
    return frame

def draw_red_dot(frame, x, y):
    """Draw a red dot at the center of the mouse."""
    if x > 0 and y > 0:
        cv2.circle(frame, (int(x), int(y)), 5, RED, -1)
    return frame

def generate_video():
    args = parse_args()
    VIDEO_PATH = args.video
    RESULTS_PATH = args.csv
    
    if args.output:
        OUTPUT_PATH = args.output
    else:
        # Auto-generate output name
        base, ext = os.path.splitext(VIDEO_PATH)
        OUTPUT_PATH = f"{base}_behavior_annotated{ext}"

    print(f"Video: {VIDEO_PATH}")
    print(f"Results: {RESULTS_PATH}")
    
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video not found: {VIDEO_PATH}")
        sys.exit(1)
    if not os.path.exists(RESULTS_PATH):
        print(f"Error: Results not found: {RESULTS_PATH}")
        sys.exit(1)
        
    # Parse zones
    try:
        zones = json.loads(args.zones)
        print(f"Loaded {len(zones)} zones configuration")
    except Exception as e:
        print(f"Warning: Could not parse zones JSON: {e}")
        zones = []
    
    # Load results
    df = pd.read_csv(RESULTS_PATH)
    total_frames = len(df)
    
    # Check for center coordinates
    has_center = "Center_x" in df.columns and "Center_y" in df.columns
    if not has_center:
        print("Warning: 'Center_x' and 'Center_y' columns not found. Red dot will be disabled.")
        # Try to find similar columns if names differ
        potential_x = [c for c in df.columns if "Center" in c and "_x" in c]
        potential_y = [c for c in df.columns if "Center" in c and "_y" in c]
        if potential_x and potential_y:
            print(f"  Found potential center columns: {potential_x[0]}, {potential_y[0]}")
            df["Center_x"] = df[potential_x[0]]
            df["Center_y"] = df[potential_y[0]]
            has_center = True

    print(f"Loaded {total_frames} frames of predictions")
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Use mp4v first, then re-encode to H.264
    temp_path = OUTPUT_PATH.replace(".mp4", "_temp.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
    
    print(f"Generating annotated video ({width}x{height} @ {fps}fps)...")
    
    # Pre-compute total behavior times for the summary line
    total_grooming_frames = int(df["Grooming"].sum()) if "Grooming" in df.columns else 0
    total_thigmotaxis_frames = int(df["Thigmotaxis"].sum()) if "Thigmotaxis" in df.columns else 0
    total_grooming_s = total_grooming_frames / fps if fps > 0 else 0
    total_thigmotaxis_s = total_thigmotaxis_frames / fps if fps > 0 else 0
    
    print(f"  Total Grooming time:    {total_grooming_s:.1f}s ({total_grooming_frames} frames)")
    print(f"  Total Thigmotaxis time: {total_thigmotaxis_s:.1f}s ({total_thigmotaxis_frames} frames)")
    
    # Cumulative counters
    grooming_cumul_frames = 0
    thigmotaxis_cumul_frames = 0
    
    # Zone counters
    zone_frames = {z["Nombre Zona"]: 0 for z in zones}
    zone_frames["Outside"] = 0
    current_zone = "Outside"
    
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame_idx >= total_frames:
            break
        
        # Get predictions for this frame
        grooming_prob = float(df.iloc[frame_idx].get("Probability_Grooming", 0))
        thigmotaxis_prob = float(df.iloc[frame_idx].get("Probability_Thigmotaxis", 0))
        grooming_on = int(df.iloc[frame_idx].get("Grooming", 0)) == 1
        thigmotaxis_on = int(df.iloc[frame_idx].get("Thigmotaxis", 0)) == 1
        
        # Update cumulative counters
        if grooming_on:
            grooming_cumul_frames += 1
        if thigmotaxis_on:
            thigmotaxis_cumul_frames += 1
        
        grooming_time_s = grooming_cumul_frames / fps if fps > 0 else 0
        thigmotaxis_time_s = thigmotaxis_cumul_frames / fps if fps > 0 else 0
        
        frame = draw_behavior_panel(frame, grooming_prob, thigmotaxis_prob,
                                     grooming_on, thigmotaxis_on,
                                     frame_idx, total_frames, fps,
                                     grooming_time_s, thigmotaxis_time_s,
                                     total_grooming_s, total_thigmotaxis_s)
        
        # Draw Red Dot
        if has_center:
            cx = float(df.iloc[frame_idx].get("Center_x", 0))
            cy = float(df.iloc[frame_idx].get("Center_y", 0))
            frame = draw_red_dot(frame, cx, cy)
            
            # Update Zone Logic
            if zones:
                current_zone = check_zone(cx, cy, zones)
                # Initialize key if not exists (e.g. if name changed or 'Outside')
                if current_zone not in zone_frames:
                    zone_frames[current_zone] = 0
                zone_frames[current_zone] += 1
                
                frame = draw_zone_panel(frame, current_zone, zone_frames, fps)
        
        out.write(frame)
        frame_idx += 1
        
        if frame_idx % 300 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames...")
    
    cap.release()
    out.release()
    
    # Re-encode to H.264 for browser/Streamlit compatibility
    print("Re-encoding to H.264...")
    cap2 = cv2.VideoCapture(temp_path)
    fourcc_h264 = cv2.VideoWriter_fourcc(*"avc1")
    out2 = cv2.VideoWriter(OUTPUT_PATH, fourcc_h264, fps, (width, height))
    
    
    if not out2.isOpened():
        # Fallback: try mp4v and rename
        print("H.264 codec not available via OpenCV, using FFmpeg subprocess for re-encoding...")
        cap2.release()
        out2.release()
        
        # Use FFmpeg command line to convert
        ffmpeg_cmd = f'ffmpeg -y -i "{temp_path}" -c:v libx264 -crf 23 -preset fast "{OUTPUT_PATH}"'
        print(f"Running: {ffmpeg_cmd}")
        os.system(ffmpeg_cmd)
        
        if os.path.exists(OUTPUT_PATH):
             os.remove(temp_path)
             print(f"Converted to H.264 using FFmpeg: {OUTPUT_PATH}")
        else:
             print("FFmpeg conversion failed. Keeping original mp4v.")
             os.rename(temp_path, OUTPUT_PATH)

    else:
        while True:
            ret, frame = cap2.read()
            if not ret:
                break
            out2.write(frame)
        cap2.release()
        out2.release()
        os.remove(temp_path)
    
    print(f"\nVideo saved to: {OUTPUT_PATH}")
    print("Done!")

if __name__ == "__main__":
    generate_video()
