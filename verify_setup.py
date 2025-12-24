import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

print("Checking imports...")
try:
    from src.config import DATABASE_URL
    print(f"Config loaded. DB URL: {DATABASE_URL}")
    
    from src.database.manager import db_manager
    print("Database manager initialized.")
    
    from src.analysis.behavior import BehaviorAnalyzer
    analyzer = BehaviorAnalyzer()
    print("Behavior Analyzer initialized.")
    
    from src.analysis.pose import PoseEstimator
    pose = PoseEstimator()
    print("Pose Estimator initialized.")
    
    from src.analysis.detector import RodentDetector
    # Don't load model to save time/memory in this check check, just class existence
    print("RodentDetector class found.")
    
    print("\nSUCCESS: All modules imported correctly.")
    
except ImportError as e:
    print(f"\nFAILURE: Import Error: {e}")
except Exception as e:
    print(f"\nFAILURE: General Error: {e}")
