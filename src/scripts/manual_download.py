import os
import shutil
from huggingface_hub import hf_hub_download
import tarfile

def clean_download():
    # Define flat target directory
    target_dir = os.path.abspath(r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\models\topview")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    print(f"Target Directory: {target_dir}")

    repo_id = "mwmathis/DeepLabCutModelZoo-SuperAnimal-TopViewMouse"
    filename = "DLC_ma_supertopview5k_resnet_50_iteration-0_shuffle-1.tar.gz"

    print(f"Downloading {filename} from {repo_id}...")
    
    # Download directly to a temp file first to avoid cache nesting hell if possible, 
    # but hf_hub_download enforces cache. 
    # Solution: Download to cache (which we redirected mostly) but then COPY to our flat dir immediately.
    # Actually, let's use local_dir to force it?
    # No, local_dir limits symlinks.
    # Let's trust the cache but get the path and copy it.
    
    try:
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            # We use the shortened cache dir we created earlier just to be safe
            cache_dir=r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\dlc_weights"
        )
        print(f"Downloaded to cache: {cached_path}")
        
        # Now extract to our flat target
        print("Extracting...")
        with tarfile.open(cached_path, "r:gz") as tar:
            tar.extractall(path=target_dir)
            
        print("Extraction Complete!")
        
        # Verify contents
        print("\nFiles in target:")
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                print(os.path.join(root, f))
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_download()
