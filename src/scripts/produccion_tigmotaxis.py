import os
import glob
import shutil
import pandas as pd
import numpy as np
import subprocess
import pickle
import argparse
from scipy.signal import savgol_filter
import warnings

warnings.filterwarnings('ignore')

PROJECT_PATH = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder"
CONFIG_PATH = os.path.join(PROJECT_PATH, "project_config.ini")
INPUT_CSV_DIR = os.path.join(PROJECT_PATH, "csv", "input_csv")
OUTLIER_CSV_DIR = os.path.join(PROJECT_PATH, "csv", "outlier_corrected_movement_location")
FEATURES_DIR = os.path.join(PROJECT_PATH, "csv", "features_extracted")
MODEL_PATH = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\models\Thigmotaxis.sav"

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
            smoothed_df[col] = smoothed_df[col].interpolate(method='linear', limit_direction='both')
            smoothed_df[col] = savgol_filter(smoothed_df[col], window_length=window, polyorder=polyorder)
    return smoothed_df

def run_test_pipeline(h5_file):
    print("="*60)
    print(" INICIANDO PIPELINE DE PRODUCCIÓN DE TIGMOTAXIS")
    print("="*60)
    
    basename = os.path.basename(h5_file)
    video_name_base = basename.split("DLC")[0]
    
    print(f"[1/4] Suavizando posiciones de: {video_name_base} (Anti-Jitter)...")
    
    df_dlc = pd.read_hdf(h5_file)
    scorer = df_dlc.columns.get_level_values(0)[0]
    
    new_cols = []
    for simba_bp in BODY_PART_MAPPING.keys():
        new_cols.extend([f"{simba_bp}_x", f"{simba_bp}_y", f"{simba_bp}_p"])
        
    df_simba = pd.DataFrame(columns=new_cols, index=df_dlc.index)
    for simba_bp, dlc_bp in BODY_PART_MAPPING.items():
        df_simba[f"{simba_bp}_x"] = df_dlc[(scorer, dlc_bp, 'x')]
        df_simba[f"{simba_bp}_y"] = df_dlc[(scorer, dlc_bp, 'y')]
        df_simba[f"{simba_bp}_p"] = df_dlc[(scorer, dlc_bp, 'likelihood')]
        
    df_simba_smoothed = apply_savgol_filter(df_simba)
    
    # Simular paso en SimBA: Escribirlo en la carpeta que espera la extracci de features
    dest_csv_path = os.path.join(OUTLIER_CSV_DIR, f"{video_name_base}.csv")
    df_simba_smoothed.to_csv(dest_csv_path)
    
    # --- DESPUES DE ESTO, EL USUARIO DEBE DIBUJAR ROIs EN SIMBA GUI ---
    print(f"\n[2/4] CSV alisado con Savitzky-Golay guardado en {os.path.basename(dest_csv_path)}")
    print("\n   [ACCIÓN REQUERIDA (ROI)]: Tienes que ir al GUI de SimBA ('Region of Interest' -> 'Draw ROIs')")
    print("   para definir el cuadro central o los bordes de la caja de estos videos nuevos de 5 minutos.")
    print("\n[3/4] Una vez dibujados los ROIs, ejecuta el script `automatizar_simba.py` para calcular cinemática y distancias de golpe, sin picar el GUI.")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Savitzky-Golay para Tigmotaxis")
    parser.add_argument("--h5_file", required=True, help="Ruta al archivo H5 devuelto por DeepLabCut", type=str)
    args = parser.parse_args()
    
    if os.path.exists(args.h5_file):
        run_test_pipeline(args.h5_file)
    else:
        print(f"Error: El archivo {args.h5_file} no existe. Esperando a que termine la GPU...")

