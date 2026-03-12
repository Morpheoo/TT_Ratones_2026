
import os
import sys
import glob
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
try:
    from simba.model.inference_batch import InferenceBatch
except ImportError:
    # If simba not in global path, maybe add src to path?
    # SimBA is usually installed as a package.
    pass

# Paths
PROJECT_DIR = os.path.abspath(os.path.join("data", "simba_projects", "SimBA_EPM_Analysis", "project_folder"))
CONFIG_PATH = os.path.join(PROJECT_DIR, "project_config.ini")
FEATURES_DIR = os.path.join(PROJECT_DIR, "csv", "features_extracted")
RESULTS_DIR = os.path.join(PROJECT_DIR, "csv", "machine_results")
TARGETS_DIR = os.path.join(PROJECT_DIR, "csv", "targets_inserted")

VIDEO_NAME = "prueba_real_2min"

def run_test_inference():
    print(f"Running inference for: {VIDEO_NAME}")
    
    # 1. Run Inference
    try:
        inferencer = InferenceBatch(config_path=CONFIG_PATH)
        inferencer.run()
    except Exception as e:
        print(f"Inference failed (or maybe partially succeeded?): {e}")

    # 2. Results Analysis
    res_path = os.path.join(RESULTS_DIR, f"{VIDEO_NAME}.csv")
    gt_path = os.path.join(TARGETS_DIR, f"{VIDEO_NAME}.csv")
    
    if os.path.exists(res_path):
        pred_df = pd.read_csv(res_path)
        total = len(pred_df)
        print(f"\n--- Prediction Results for {VIDEO_NAME} ---")
        
        behaviors = ["Grooming", "Thigmotaxis"]
        
        # Check if Ground Truth exists
        if os.path.exists(gt_path):
            gt_df = pd.read_csv(gt_path)
            # Ensure lengths match
            if len(gt_df) != len(pred_df):
                print(f"Warning: Length mismatch (GT={len(gt_df)}, Pred={len(pred_df)}). Trimming to min.")
                min_len = min(len(gt_df), len(pred_df))
                gt_df = gt_df.iloc[:min_len]
                pred_df = pred_df.iloc[:min_len]
            
            print(f"\n--- Performance Metrics (vs Ground Truth) ---")
            for b in behaviors:
                if b in pred_df.columns and b in gt_df.columns:
                    y_true = gt_df[b].astype(int)
                    y_pred = pred_df[b].astype(int)
                    
                    precision = precision_score(y_true, y_pred, zero_division=0)
                    recall = recall_score(y_true, y_pred, zero_division=0)
                    f1 = f1_score(y_true, y_pred, zero_division=0)
                    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
                    
                    print(f"\n{b.upper()}:")
                    print(f"  Precision: {precision:.2%}")
                    print(f"  Recall:    {recall:.2%}")
                    print(f"  F1-Score:  {f1:.2%}")
                    print(f"  Counts:    TP={tp}, FP={fp}, FN={fn}")
        else:
            print(f"\nNo Ground Truth found at {gt_path}. Only showing detection counts.")
            for b in behaviors:
                if b in pred_df.columns:
                    count = pred_df[b].sum()
                    print(f"  {b}: {count} frames ({count/total*100:.1f}%)")

if __name__ == "__main__":
    run_test_inference()
