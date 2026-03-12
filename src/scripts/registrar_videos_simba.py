import os
import shutil
import pandas as pd
import cv2

PROJECT_PATH = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder"
VIDEOS_DIR = os.path.join(PROJECT_PATH, "videos")
VIDEO_INFO_PATH = os.path.join(PROJECT_PATH, "logs", "video_info.csv")
SOURCE_DIR = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dataset_tt"

def register_video(video_path):
    video_basename = os.path.basename(video_path)
    video_name, ext = os.path.splitext(video_basename)
    
    dest_video_path = os.path.join(VIDEOS_DIR, f"{video_name}.mp4")
    
    # 1. Copiar y convertir/renombrar a .mp4 si es necesario (cv2 o shutil)
    # SimBA es mas feliz con .mp4 o .avi. Asi que simplemente copiamos y renombramos su extension
    # o mejor aun, si es mov lo copiamos tal cual pero con el formato aceptado en video_info. 
    # Generalmente no duele copiarlo nativamente, OpenCV lo leera igual.
    dest_path_real = os.path.join(VIDEOS_DIR, video_basename)
    if not os.path.exists(dest_path_real):
        print(f"Copiando {video_basename} a la carpeta videos del proyecto SimBA...")
        shutil.copy2(video_path, dest_path_real)
        
    # 2. Leer metadata del video para agregarlo a video_info.csv
    cap = cv2.VideoCapture(dest_path_real)
    if not cap.isOpened():
        print(f"Error abriendo el video {dest_path_real} con OpenCV.")
        return
        
    fps = int(round(cap.get(cv2.CAP_PROP_FPS)))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    # 3. Registrar en el archivo
    df = pd.read_csv(VIDEO_INFO_PATH)
    if video_name not in df["Video"].values:
        print(f"Registrando info de '{video_name}' en video_info.csv...")
        # Ponemos Distance_in_mm por defecto 400 y pixels/mm por defecto 2.5 (mismos valores del clip)
        new_row = {
            "Video": video_name,
            "fps": fps,
            "Resolution_width": width,
            "Resolution_height": height,
            "Distance_in_mm": 400.0,
            "pixels/mm": 2.5
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(VIDEO_INFO_PATH, index=False)
        print(f"Registrado exitosamente: {video_name}")
    else:
        print(f"El video '{video_name}' ya estaba registrado.")

def main():
    print("Sincronizando videos nativos a SimBA (Dataset TT)...")
    videos_to_check = ["DZP-R1.mov", "C1-R1.mov", "C2-R1.mov", "C56-R1.mov", "C7-R1.mov", "R5DZ_01mar24.mp4", "R5B20_01mar24.mp4"]
    
    for v in videos_to_check:
        v_path = os.path.join(SOURCE_DIR, v)
        if os.path.exists(v_path):
            register_video(v_path)
    
    print("\n¡Listo! Ahora sí puedes abrir la GUI de SimBA, ir a 'Draw ROIs' y verás los videos masivos listos para dibujar.")

if __name__ == "__main__":
    main()
