
import cv2
import os

INPUT_VIDEO = r"videos_data\prueba_2min_Control.mp4"
OUTPUT_VIDEO = r"videos_data\prueba_real_2min.mp4"
START_SEC = 30
DURATION_SEC = 120  # 2 minutes

def trim_video():
    if not os.path.exists(INPUT_VIDEO):
        print(f"Error: Input video not found: {INPUT_VIDEO}")
        return

    cap = cv2.VideoCapture(INPUT_VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Calculate max frames and start frame
    start_frame = int(fps * START_SEC)
    max_frames = int(fps * DURATION_SEC)
    print(f"Trimming video from {START_SEC}s to {START_SEC+DURATION_SEC}s ({max_frames} frames).")

    # Define codec and create VideoWriter object
    # mp4v for mp4
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))

    # set starting frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    count = 0
    while cap.isOpened() and count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        count += 1
        if count % 100 == 0:
            print(f"Processed {count} frames...", end='\r')

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"\n[OK] Created trimmed video: {OUTPUT_VIDEO} ({count} frames)")

if __name__ == "__main__":
    trim_video()
