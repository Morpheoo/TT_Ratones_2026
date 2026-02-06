import os
import shutil
import sys

# Define locations
venv_site_packages = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\venv_311\Lib\site-packages"
keras_root = os.path.join(venv_site_packages, "tf_keras")
src_legacy = os.path.join(keras_root, "src", "legacy_tf_layers")
dst_legacy = os.path.join(keras_root, "legacy_tf_layers")

print(f"Keras Root: {keras_root}")

if not os.path.exists(src_legacy):
    print(f"Source not found: {src_legacy}")
    sys.exit(1)

print(f"Found source: {src_legacy}")

if os.path.exists(dst_legacy):
    print(f"Destination exists: {dst_legacy}")
    print("Removing old destination...")
    shutil.rmtree(dst_legacy)

print(f"Copying {src_legacy} -> {dst_legacy}")
try:
    shutil.copytree(src_legacy, dst_legacy)
    print("Copy successful!")
except Exception as e:
    print(f"Copy failed: {e}")
    sys.exit(1)

# Verify
print("Verifying import...")
try:
    import tf_keras.legacy_tf_layers
    print("'import tf_keras.legacy_tf_layers' WORKED!")
except ImportError as e:
    print(f"Verification failed: {e}")
