from moviepy.editor import VideoFileClip
import os

input_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133_labeled.mp4"
output_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133_labeled_h264.mp4"

print(f"Re-encoding {input_path} to H.264...")

try:
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        exit(1)

    clip = VideoFileClip(input_path)
    # Write using libx264 codec which is browser/streamlit friendly
    clip.write_videofile(output_path, codec='libx264', audio=False)
    
    # Replace original if successful (optional, but keeps things clean for the app)
    # Actually, the app looks for *labeled.mp4, so let's rename after checking.
    print(f"Success! Output at {output_path}")
    
except Exception as e:
    print(f"Error during re-encoding: {e}")
    exit(1)
