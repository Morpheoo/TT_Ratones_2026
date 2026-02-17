import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import steps from full_pipeline
from src.scripts.full_pipeline import step6_run_inference, step7_generate_video

if __name__ == "__main__":
    print("=== Running SimBA Inference & Video Only (Skip DLC) ===")
    
    # Run Inference (Step 6)
    print("\nRunning Inference...")
    if step6_run_inference():
        print("Inference Complete.")
        
        # Run Video Generation (Step 7)
        print("\nGenerating Video...")
        if step7_generate_video():
            print("Video Generation Complete.")
        else:
            print("Video Generation Failed.")
    else:
        print("Inference Failed.")
        
    print("\n=== All Done ===")
