import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import deeplabcut
import pprint

print("DeepLabCut version:", deeplabcut.__version__)
print("\nTop level attributes with 'animal' or 'zoo':")
print([x for x in dir(deeplabcut) if 'animal' in x.lower() or 'zoo' in x.lower()])

try:
    import deeplabcut.modelzoo
    print("\ndeeplabcut.modelzoo attributes:")
    pprint.pprint(dir(deeplabcut.modelzoo))
except ImportError:
    print("\nCould not import deeplabcut.modelzoo")
except Exception as e:
    print(f"\nError accessing modelzoo: {e}")
