import os
import simba
from simba.feature_extractors.feature_extractor_user_defined import UserDefinedFeatureExtractor as FeatureExtractorUserDefined

# Config
PROJECT_PATH = os.path.abspath(os.path.join("data", "simba_projects", "SimBA_EPM_Analysis"))
PROJECT_FOLDER = os.path.join(PROJECT_PATH, "project_folder")
CONFIG_PATH = os.path.join(PROJECT_FOLDER, "project_config.ini")

def extract_features():
    print(f"Extracting features for project at {CONFIG_PATH}...")
    
    # SimBA expects files in "csv/outlier_corrected_movement_location" by default for feature extraction
    # Since we skipped outlier correction, we copy input_csv files there manually to bypass.
    input_csv_dir = os.path.join(PROJECT_FOLDER, "csv", "input_csv")
    target_dir = os.path.join(PROJECT_FOLDER, "csv", "outlier_corrected_movement_location")
    
    import shutil
    import glob
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    files = glob.glob(os.path.join(input_csv_dir, "*.csv"))
    print(f"Copying {len(files)} files to {target_dir} to skip outlier correction...")
    for f in files:
        shutil.copy(f, target_dir)
    
    try:
        # Initialize Feature Extractor for User Defined body parts
        # FeatureExtractorUserDefined(config_path=config_path)
        extractor = FeatureExtractorUserDefined(config_path=CONFIG_PATH)
        
        # Run extraction
        extractor.run()
        print("Feature extraction complete!")
        
    except Exception as e:
        print(f"Error extracting features: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found: {CONFIG_PATH}")
        # Re-derive path if needed or fail
        # My previous script used PROJECT_FOLDER logic, need to be consistent.
        # Let's verify path.
        pass
    extract_features()
