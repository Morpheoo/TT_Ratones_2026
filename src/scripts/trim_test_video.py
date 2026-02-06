from moviepy.video.io.VideoFileClip import VideoFileClip
import os

input_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\diazepam_Control.mp4"
output_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\test_short_gpu.mp4"

if not os.path.exists(input_path):
    print(f"Error: Input file not found at {input_path}")
    exit(1)

print(f"Trimming {input_path} to 10 seconds...")
try:
    with VideoFileClip(input_path) as video:
        # Trim from 0 to 10 seconds
        new_video = video.subclip(0, 10)
        new_video.write_videofile(output_path, codec="libx264", audio=False)
    print(f"Success! Saved to {output_path}")
except Exception as e:
    print(f"Error trimming video: {e}")
