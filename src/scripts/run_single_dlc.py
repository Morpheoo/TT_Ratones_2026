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
except Exception:
    pass

from deeplabcut.modelzoo.api.superanimal_inference import video_inference
import argparse

os.environ["HF_HOME"] = os.path.abspath("hf_cache")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=str)
    args = parser.parse_args()

    video = os.path.abspath(args.video)
    if not os.path.exists(video):
        print(f"File not found: {video}")
        sys.exit(1)
        
    print(f"Iniciando Inferencia GPU aislada para: {video}")
    try:
        videotype = video.split('.')[-1].lower()
        video_inference(
            videos=[video],
            superanimal_name="superanimal_topviewmouse",
            videotype=videotype,
            batchsize=16,
        )
        print(f"Éxito extrayendo variables de {video}")
    except Exception as e:
        print(f"Falla procesando {video}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
