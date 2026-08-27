import cv2
import time
import torch
from ultralytics import YOLO
import sys

def benchmark_gpu(video_path, model_path, num_frames=100):
    print(f"python: {sys.version}")
    print(f"torch: {torch.__version__}")
    print(f"cuda available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"device: {torch.cuda.get_device_name(0)}")
    
    print("-" * 50)
    print(f"Loading Model: {model_path}")
    # Force loading to GPU
    try:
        model = YOLO(model_path)
        print("Model loaded.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print(f"Opening Video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    print(f"Running benchmark on first {num_frames} frames...")
    print("-" * 50)

    count = 0
    start_time = time.time()
    
    # Warmup
    success, frame = cap.read()
    if success:
        # Run once to warm up GPU
        _ = model(frame, device='cuda:0', verbose=False)

    total_inference_time = 0
    
    while count < num_frames and cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        t0 = time.time()
        # Explicitly requesting device=0 (GPU)
        results = model(frame, device='cuda:0', verbose=False) 
        t1 = time.time()
        
        total_inference_time += (t1 - t0)
        count += 1
        
        if count % 20 == 0:
            print(f"Processed {count} frames...")

    end_time = time.time()
    cap.release()
    
    if count == 0:
        print("No frames processed.")
        return

    avg_fps = count / total_inference_time
    print("-" * 50)
    print(f"BENCHMARK RESULTS")
    print(f"Processed {count} frames using GPU.")
    print(f"Average Inference FPS: {avg_fps:.2f} frames/second")
    print(f"Note: This confirms successful GPU access (CUDA) for video analysis.")
    print("-" * 50)

if __name__ == "__main__":
    # Adjust paths based on local environment
    VIDEO_PATH = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\mouse-1_Control.mp4"
    MODEL_PATH = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\yolov8n.pt"
    
    benchmark_gpu(VIDEO_PATH, MODEL_PATH)
