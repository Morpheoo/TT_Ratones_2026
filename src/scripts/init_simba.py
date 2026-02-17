import simba
from simba.utils.config_creator import ProjectConfigCreator
import os
from datetime import datetime

# Configuration
PROJECT_NAME = "SimBA_EPM_Analysis"
USER_NAME = "Morpheoo"
# Use a dedicated folder for SimBA projects
PROJECT_PATH = os.path.abspath(os.path.join("data", "simba_projects"))

# Ensure directory exists
os.makedirs(PROJECT_PATH, exist_ok=True)

print(f"Creating SimBA project '{PROJECT_NAME}' in {PROJECT_PATH}...")

try:
    # Initialize Project Creator with dummy body parts (we will overwrite them)
    project_creator = ProjectConfigCreator(project_path=PROJECT_PATH,
                                            project_name=PROJECT_NAME,
                                            target_list=["Grooming", "Thigmotaxis"], # Behaviors we want to classify
                                            pose_estimation_bp_cnt='user_defined', 
                                            body_part_config_idx=0, # Dummy index
                                            animal_cnt=1,
                                            file_type='csv')
    
    # 2. Overwrite project_bp_names.csv with ACTUAL SuperAnimal body parts
    # Extracted from CSV header
    superanimal_bps = [
        "nose", "left_ear", "right_ear", "left_ear_tip", "right_ear_tip", 
        "left_eye", "right_eye", "neck", "mid_back", "mouse_center", 
        "mid_backend", "mid_backend2", "mid_backend3", "tail_base", 
        "tail1", "tail2", "tail3", "tail4", "tail5", 
        "left_shoulder", "left_midside", "left_hip", 
        "right_shoulder", "right_midside", "right_hip", 
        "tail_end", "head_midpoint"
    ]
    
    bp_names_path = os.path.join(PROJECT_PATH, PROJECT_NAME, "project_folder", "logs", "measures", "pose_configs", "bp_names", "project_bp_names.csv")
    
    print(f"Overwriting body parts in {bp_names_path}...")
    with open(bp_names_path, "w") as f:
        for bp in superanimal_bps:
            f.write(bp + "\n")
            
    print("✅ SimBA project initialized and body parts configured!")

except Exception as e:
    print(f"Error initializing SimBA project: {e}")
    import traceback
    traceback.print_exc()

# 3. Import Video and CSV (TODO: Can be added here using FileImporter)

