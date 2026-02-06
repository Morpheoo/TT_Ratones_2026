import cv2

video_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133.mp4"
cap = cv2.VideoCapture(video_path)

if cap.isOpened():
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Resolution: {width}x{height}")
else:
    print("Failed to open video")

cap.release()
