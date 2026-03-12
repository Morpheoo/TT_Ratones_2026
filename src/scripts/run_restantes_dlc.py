import os
import sys

try:
    import site
    site_packages = site.getsitepackages()[1]
    nvidia_path = os.path.join(site_packages, "nvidia")
    if os.path.exists(nvidia_path):
        for root, dirs, files in os.walk(nvidia_path):
            if "bin" in dirs:
                bin_path = os.path.join(root, "bin")
                os.environ["PATH"] += os.pathsep + bin_path
                try:
                    os.add_dll_directory(bin_path)
                except:
                    pass
        print("NVIDIA DLLs added to PATH")
except Exception as e:
    print(f"Failed to auto-add NVIDIA DLLs: {e}")

from deeplabcut.modelzoo.api.superanimal_inference import video_inference

os.environ["HF_HOME"] = os.path.abspath("hf_cache")

# Agregando el resto de los videos para completar el conjunto de Entrenamiendo (Train) y Prueba (Test)
VIDEOS = [
    os.path.abspath(r"dataset_tt\C2-R1.mov"),
    os.path.abspath(r"dataset_tt\C56-R1.mov"),
    os.path.abspath(r"dataset_tt\C7-R1.mov"),
    os.path.abspath(r"dataset_tt\R5DZ_01mar24.mp4"),
    os.path.abspath(r"dataset_tt\R5B20_01mar24.mp4")
]

def main():
    print("Iniciando Inferencia de los 4 videos restantes para Machine Learning...")
    for video in VIDEOS:
        if not os.path.exists(video):
            print(f"Saltando {video}, archivo no encontrado.")
            continue
        print(f"Procesando: {video}")
        
        try:
            video_inference(
                videos=[video],
                superanimal_name="superanimal_topviewmouse",
                videotype="mov",
                batchsize=16,
            )
            print(f"Éxito extrayendo variables de {video}")
        except Exception as e:
            print(f"Falla procesando {video}: {e}")

if __name__ == "__main__":
    main()
