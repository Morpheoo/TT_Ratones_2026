import os
import subprocess

def trim_video(input_path, output_path, start_time="00:00:10", duration="40"):
    print(f"[{start_time} - {duration}s] Extrayendo: {os.path.basename(input_path)}...")
    cmd = [
        "ffmpeg", "-y", 
        "-ss", start_time, 
        "-i", input_path, 
        "-t", duration, 
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", 
        "-c:a", "copy", 
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f" -> Guardado: {output_path}")

def main():
    base_dir = VIDEOS_DIR
    out_dir = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dataset_hibrido_clips"
    
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # 1. Caja Oscura
    vid1 = os.path.join(base_dir, "C1-R1.mov")
    vid1_out = os.path.join(out_dir, "C1-R1_clip.mp4")
    
    # 2. Laberinto Azul Open
    vid2 = os.path.join(base_dir, "DZP-R1.mov")
    vid2_out = os.path.join(out_dir, "DZP-R1_clip.mp4")
    
    # 3. Laberinto Azul Variado
    vid3 = os.path.join(base_dir, "R5B20_01mar24.mp4")
    vid3_out = os.path.join(out_dir, "R5B20_01mar24_clip.mp4")

    trim_video(vid1, vid1_out)
    trim_video(vid2, vid2_out)
    trim_video(vid3, vid3_out)
    
    print("\n¡Extracción Híbrida Completada! Revisa la carpeta dataset_hibrido_clips.")

if __name__ == "__main__":
    main()
