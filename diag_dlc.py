import sys
import os

print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    import deeplabcut
    print("SUCCESS: DeepLabCut imported correctly.")
    print(f"File: {deeplabcut.__file__}")
except Exception as e:
    print(f"FAILURE: Could not import DeepLabCut.")
    print(f"Error type: {type(e)}")
    print(f"Error message: {e}")
    import traceback
    traceback.print_exc()
