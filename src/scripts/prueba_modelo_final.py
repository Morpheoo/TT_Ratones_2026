
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
import warnings

# Ignorar advertencias de Scikit-Learn
warnings.filterwarnings('ignore')

MODEL_PATH = THIGMOTAXIS_MODEL
FEATURES_DIR = SIMBA_FEATURES_CSV

def probar_modelo():
    print(f"Cargando tu cerebro artificial (Modelo): {os.path.basename(MODEL_PATH)}...\n")
    
    # Cargar el modelo Random Forest generado por SimBA
    with open(MODEL_PATH, 'rb') as f:
        clf = pickle.load(f)
        
    print("="*50)
    print(" INICIANDO PRUEBAS EN MUNDO REAL DE TIGMOTAXIS")
    print("="*50)

    # Recorrer todos los videos procesados
    for file in os.listdir(FEATURES_DIR):
        if not file.endswith('.csv'):
            continue
            
        csv_path = os.path.join(FEATURES_DIR, file)
        
        # Leer variables matemáticas del video extrayendo el index si lo hay
        df = pd.read_csv(csv_path)
        
        # A veces Pandas lee una columna 'Unnamed: 0' que es el index, la quitamos si existe porque la IA no la usa
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
            
        # Nos aseguramos de mandar solo las columnas que aprendio el modelo
        try:
            expected_feats = clf.feature_names_in_
            df_reducido = df[expected_feats]
        except AttributeError:
            # Si la versi de sklearn es vieja y no tiene feature_names_in_
             df_reducido = df
             
        # LA MAGIA OCURRE AQUÍ: La IA decide fotograma por fotograma si hay tigmotaxis
        predictions = clf.predict(df_reducido)
        
        # Calcular el tiempo
        fps = 30 # Nuestros videos van a 30 fotogramas por segundo
        frames_thigmotaxis = sum(predictions)
        segundos_totales = frames_thigmotaxis / fps
        total_frames = len(predictions)
        
        # Resultados
        print(f"\nAnalizando: {file}")
        print(f"   -> Frames totales del video: {total_frames}")
        print(f"   -> Fotogramas marcados como Tigmotaxis por la IA: {frames_thigmotaxis}")
        print(f"   -> TIEMPO TOTAL CALCULADO: {segundos_totales:.2f} segundos")
        
        if file.startswith("R5B20"):
            print("   -> (Video Control: Recuerda que a este NO le vimos tigmotaxis, debe ser 0.0s)")

    print("\n" + "="*50)
    print("PRUEBA COMPLETADA CON EXITO!")

if __name__ == "__main__":
    probar_modelo()
