import os
import glob
import shutil
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from simba.feature_extractors.feature_extractor_8bp import ExtractFeaturesFrom8bps
from simba.roi_tools.ROI_feature_analyzer import ROIFeatureCreator

PROJECT_PATH = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder"
INPUT_CSV_DIR = os.path.join(PROJECT_PATH, "csv", "input_csv")
OUTLIER_CSV_DIR = os.path.join(PROJECT_PATH, "csv", "outlier_corrected_movement_location")
VIDEOS_DIR = os.path.join(PROJECT_PATH, "videos")
SOURCE_DATA = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dataset_tt"

BODY_PART_MAPPING = {
    "Nose_1": "nose",
    "Ear_left_1": "left_ear",
    "Ear_right_1": "right_ear",
    "Center_1": "mouse_center",
    "Lateral_left_1": "left_midside",
    "Lateral_right_1": "right_midside",
    "Tail_base_1": "tail_base",
    "Tail_end_1": "tail1"
}

def apply_savgol_filter(df, window=15, polyorder=3):
    smoothed_df = df.copy()
    for col in df.columns:
        if '_p' not in col:
            smoothed_df[col] = pd.to_numeric(smoothed_df[col], errors='coerce').interpolate(method='linear', limit_direction='both')
            smoothed_df[col] = savgol_filter(smoothed_df[col], window_length=window, polyorder=polyorder)
    return smoothed_df

videos_to_process = ["R5DZ_01mar24", "R5B20_01mar24"]

print("1. IMPORTANDO VIDEOS Y SIMULANDO CORRECCIÓN CON SAVGOL...")
for vname in videos_to_process:
    h5_file = os.path.join(SOURCE_DATA, f"{vname}DLC_snapshot-200000.h5")
    if not os.path.exists(h5_file):
        print(f"Skipping {vname}, H5 no encontrado.")
        continue
    
    print(f"Procesando: {vname}")
    df_dlc = pd.read_hdf(h5_file)
    scorer = df_dlc.columns.get_level_values(0)[0]
    
    new_cols = []
    for simba_bp in BODY_PART_MAPPING.keys():
        simba_bp_cleaned = simba_bp.replace('_1', '')
        new_cols.extend([f"{simba_bp_cleaned}_x", f"{simba_bp_cleaned}_y", f"{simba_bp_cleaned}_p"])
        
    df_simba = pd.DataFrame(columns=new_cols, index=df_dlc.index)
    for simba_bp, dlc_bp in BODY_PART_MAPPING.items():
        simba_bp_cleaned = simba_bp.replace('_1', '')
        df_simba[f"{simba_bp_cleaned}_x"] = df_dlc[(scorer, dlc_bp, 'x')]
        df_simba[f"{simba_bp_cleaned}_y"] = df_dlc[(scorer, dlc_bp, 'y')]
        df_simba[f"{simba_bp_cleaned}_p"] = df_dlc[(scorer, dlc_bp, 'likelihood')]
        
    df_simba_smoothed = apply_savgol_filter(df_simba)
    
    src_video = os.path.join(SOURCE_DATA, f"{vname}.mp4")
    dest_video = os.path.join(VIDEOS_DIR, f"{vname}.mp4")
    if os.path.exists(src_video) and not os.path.exists(dest_video):
        shutil.copy(src_video, dest_video)
        
    # Guardamos directo en Outlier Corrected
    out_csv = os.path.join(OUTLIER_CSV_DIR, f"{vname}.csv")
    df_simba_smoothed.to_csv(out_csv)
    print(f"-> Archivo listo en {out_csv}")

config_path = os.path.join(PROJECT_PATH, "project_config.ini")

print("\n2. EXTRAYENDO FEATURES SIMBA...")
feature_extractor = ExtractFeaturesFrom8bps(config_path=config_path)
feature_extractor.run()

print("\n3. EXTRAYENDO ROIs...")
roi_analyzer = ROIFeatureCreator(
    config_path=config_path, 
    body_parts=['Center'], 
    append_data=True
)
roi_analyzer.run()
roi_analyzer.save()

print("\nLISTO. PROCEDIENDO A PREDICCIÓN CON EL MODELO.")
