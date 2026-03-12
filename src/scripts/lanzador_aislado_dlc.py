import os
import subprocess

VIDEOS = [
    r"dataset_tt\C1-R1.mov",
    r"dataset_tt\C2-R1.mov",
    r"dataset_tt\C56-R1.mov",
    r"dataset_tt\C7-R1.mov",
    r"dataset_tt\R5DZ_01mar24.mp4",
    r"dataset_tt\R5B20_01mar24.mp4"
]

def main():
    print("Iniciando batch de inferencias DLC con aislamiento de memoria (GPU VRAM)...")
    for vid in VIDEOS:
        if not os.path.exists(vid):
            print(f"Video no encontrado: {vid}. Saltando...")
            continue
        
        print("-" * 60)
        print(f"Lanzando proceso aislado para: {vid}")
        print("-" * 60)
        
        # We run the python interpreter that has DLC installed
        cmd = [r"venv_310\Scripts\python.exe", r"src\scripts\run_single_dlc.py", "--video", vid]
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print(f"Error procesando {vid}. Revisa los logs.")
        else:
            print(f"Proceso finalizado limpiamente para {vid}. Memoria liberada.")
            
if __name__ == "__main__":
    main()
