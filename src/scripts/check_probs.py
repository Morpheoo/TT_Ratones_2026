
import sys
import os
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.config import (
        GROOMING_MODEL,
        THIGMOTAXIS_MODEL,
        SIMBA_PROJECT_DIR,
        SIMBA_FEATURES_CSV,
        VIDEOS_DIR,
        FFMPEG_PATH,
        YOLO_MODEL
    )
except ImportError:
    pass

import pandas as pd
import pickle
import os
import numpy as np

MODEL_PATH = THIGMOTAXIS_MODEL
FEATURES_DIR = SIMBA_FEATURES_CSV

def probar_umbrales():
    with open(MODEL_PATH, 'rb') as f:
        clf = pickle.load(f)

    file = "R5DZ_01mar24_2min.csv"
    csv_path = os.path.join(FEATURES_DIR, file)
    df = pd.read_csv(csv_path)
    if 'Unnamed: 0' in df.columns:
        df = df.drop(columns=['Unnamed: 0'])
        
    try:
        expected_feats = clf.feature_names_in_
        df_reducido = df[expected_feats]
    except AttributeError:
        df_reducido = df
             
    # Obtener probabilidades
    probs = clf.predict_proba(df_reducido)[:, 1] # Probabilidad de clase 1 (Tigmotaxis)
    
    print(f"--- ANÁLISIS DE PROBABILIDAD PARA: {file} ---")
    print(f"Probabilidad MÁXIMA detectada en el video: {np.max(probs):.4f}")
    print(f"Probabilidad MEDIA en el video: {np.mean(probs):.4f}")
    
    # Probar diferentes umbrales
    for threshold in [0.50, 0.40, 0.35, 0.30, 0.25, 0.20]:
        frames = np.sum(probs >= threshold)
        print(f"Threshold (Umbral) {threshold:.2f}: {frames} frames detectados ({(frames/30):.2f} segundos)")

if __name__ == "__main__":
    probar_umbrales()
