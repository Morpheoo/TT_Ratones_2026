"""
Run SimBA classifier inference on features_extracted data.
Fixes config paths and thresholds, then runs InferenceBatch.
"""
import os
import sys
import configparser

CONFIG_PATH = os.path.abspath(os.path.join(
    "data", "simba_projects", "SimBA_EPM_Analysis",
    "project_folder", "project_config.ini"
))

MODELS_DIR = os.path.abspath(os.path.join(
    "data", "simba_projects", "SimBA_EPM_Analysis",
    "models", "generated_models"
))

def fix_config():
    """Update config to point to correct model paths and set thresholds."""
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    
    # Fix model paths to point to generated_models directory
    config.set("SML settings", "model_path_1", os.path.join(MODELS_DIR, "Grooming.sav"))
    config.set("SML settings", "model_path_2", os.path.join(MODELS_DIR, "Thigmotaxis.sav"))
    
    # Set thresholds (0.5 = 50% confidence required)
    config.set("threshold_settings", "threshold_1", "0.5")
    config.set("threshold_settings", "threshold_2", "0.5")
    
    # Set minimum bout lengths (in ms) - 200ms minimum to filter noise
    config.set("Minimum_bout_lengths", "min_bout_1", "200")
    config.set("Minimum_bout_lengths", "min_bout_2", "200")
    
    with open(CONFIG_PATH, "w") as f:
        config.write(f)
    print("Config updated with correct model paths and thresholds.")

def run_inference():
    fix_config()
    
    from simba.model.inference_batch import InferenceBatch
    
    print("\nRunning inference on all feature-extracted files...")
    inferencer = InferenceBatch(config_path=CONFIG_PATH)
    inferencer.run()
    
    # Print summary of results
    import pandas as pd
    import glob
    
    results_dir = os.path.join(
        "data", "simba_projects", "SimBA_EPM_Analysis",
        "project_folder", "csv", "machine_results"
    )
    
    for csv_file in glob.glob(os.path.join(results_dir, "*.csv")):
        basename = os.path.basename(csv_file)
        df = pd.read_csv(csv_file)
        total = len(df)
        
        print(f"\n{'='*60}")
        print(f"Results for: {basename}")
        print(f"{'='*60}")
        
        if "Grooming" in df.columns:
            g_count = int(df["Grooming"].sum())
            g_pct = g_count / total * 100
            print(f"  Grooming detected:    {g_count} frames ({g_pct:.1f}%)")
            
        if "Thigmotaxis" in df.columns:
            t_count = int(df["Thigmotaxis"].sum())
            t_pct = t_count / total * 100
            print(f"  Thigmotaxis detected: {t_count} frames ({t_pct:.1f}%)")
        
        # Also show probability stats
        if "Probability_Grooming" in df.columns:
            print(f"  Grooming prob (mean):    {df['Probability_Grooming'].mean():.3f}")
            print(f"  Grooming prob (max):     {df['Probability_Grooming'].max():.3f}")
        if "Probability_Thigmotaxis" in df.columns:
            print(f"  Thigmotaxis prob (mean): {df['Probability_Thigmotaxis'].mean():.3f}")
            print(f"  Thigmotaxis prob (max):  {df['Probability_Thigmotaxis'].max():.3f}")

if __name__ == "__main__":
    run_inference()
