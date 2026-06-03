import tf_keras
import sys

print(f"tf_keras versión: {tf_keras.__version__}")

if hasattr(tf_keras, "legacy_tf_layers"):
    print("FOUND: tf_keras.legacy_tf_layers type:", type(tf_keras.legacy_tf_layers))
else:
    print("NOT FOUND: tf_keras.legacy_tf_layers")
    
# Check submodules
try:
    import tf_keras.legacy_tf_layers
    print("Import successful!")
except ImportError as e:
    print(f"Import failed: {e}")

# Check dir
print("tf_keras dir has legacy?", "legacy_tf_layers" in dir(tf_keras))

# Check layers
import tf_keras.layers
print("tf_keras.layers dir has legacy?", "legacy_tf_layers" in dir(tf_keras.layers))
