import os
import glob
import shutil
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

# Directorios
PROJECT_PATH = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\thigmotaxis_optimizado\project_folder"
INPUT_CSV_DIR = os.path.join(PROJECT_PATH, "csv", "input_csv")
VIDEOS_DIR = os.path.join(PROJECT_PATH, "videos")
SOURCE_DATA = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dataset_hibrido_clips"

# Mapeo de 27 body parts de SuperAnimal a 8 body parts de SimBA Classic
# SimBA 1 animal 8 parts espera:
# Ear_left_1, Ear_right_1, Nose_1, Center_1, Lateral_left_1, Lateral_right_1, Tail_base_1, Tail_end_1

BODY_PART_MAPPING = {
    "Nose_1": "nose",
    "Ear_left_1": "left_ear",
    "Ear_right_1": "right_ear",
    "Center_1": "mouse_center",
    "Lateral_left_1": "left_midside",
    "Lateral_right_1": "right_midside",
    "Tail_base_1": "tail_base",
    "Tail_end_1": "tail1" # Usamos tail1 en vez de tail_end para Evitar el JITTER EXTREMO mencionado en el paper
}

def apply_savgol_filter(df, window=15, polyorder=3):
    """Aplica filtro Savitzky-Golay (suavizado) para eliminar micromovimientos (Jitter)"""
    smoothed_df = df.copy()
    for col in df.columns:
        if '_p' not in col: # No suavizar las probabilidades
            # Interpolar NaNs antes del filtro
            smoothed_df[col] = smoothed_df[col].interpolate(method='linear', limit_direction='both')
            # Aplicar suavizado
            smoothed_df[col] = savgol_filter(smoothed_df[col], window_length=window, polyorder=polyorder)
    return smoothed_df

def process_and_import():
    print(f"Importando datos y aplicando filtro anti-jitter...")
    
    # 1. Asegurar directorios
    os.makedirs(INPUT_CSV_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # 2. Buscar archivos H5/CSV generados de DeepLabCut
    h5_files = glob.glob(os.path.join(SOURCE_DATA, "*.h5"))
    
    for h5_file in h5_files:
        basename = os.path.basename(h5_file)
        video_name_base = basename.split("DLC")[0]
        
        print(f"\nProcesando: {video_name_base}")
        
        # Leer dataframe multiposicional
        df_dlc = pd.read_hdf(h5_file)
        scorer = df_dlc.columns.get_level_values(0)[0]
        
        # Crear nuevo dataframe para SimBA
        new_cols = []
        for simba_bp in BODY_PART_MAPPING.keys():
            new_cols.extend([f"{simba_bp}_x", f"{simba_bp}_y", f"{simba_bp}_p"])
            
        df_simba = pd.DataFrame(columns=new_cols, index=df_dlc.index)
        
        # Extraer coordenadas de SuperAnimal a columnas de SimBA
        for simba_bp, dlc_bp in BODY_PART_MAPPING.items():
            df_simba[f"{simba_bp}_x"] = df_dlc[(scorer, dlc_bp, 'x')]
            df_simba[f"{simba_bp}_y"] = df_dlc[(scorer, dlc_bp, 'y')]
            df_simba[f"{simba_bp}_p"] = df_dlc[(scorer, dlc_bp, 'likelihood')]
            
        # APLICAR ANTIDOTO DEL PAPER: Suavizado Savitzky-Golay + Interpolación 
        df_simba_smoothed = apply_savgol_filter(df_simba)
        
        # Guardar CSV en formato que le gusta a SimBA
        dest_csv_path = os.path.join(INPUT_CSV_DIR, f"{video_name_base}.csv")
        df_simba_smoothed.to_csv(dest_csv_path)
        print(f" -> Guardado CSV Suavizado (8-puntos): {os.path.basename(dest_csv_path)}")
        
        # Copiar video MP4 a la carpeta de proyecto
        src_video = os.path.join(SOURCE_DATA, f"{video_name_base}.mp4")
        if os.path.exists(src_video):
            dest_video = os.path.join(VIDEOS_DIR, f"{video_name_base}.mp4")
            shutil.copy(src_video, dest_video)
            print(f" -> Copiado Video: {os.path.basename(dest_video)}")
            
    print("\n¡Proceso Completado con Éxito! El Jitter ha sido eliminado.")

if __name__ == "__main__":
    process_and_import()
