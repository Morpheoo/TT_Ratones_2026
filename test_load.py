import sys
import traceback
import pickle
import warnings
warnings.filterwarnings('ignore') # remove sklearn warnings that garble output

try:
    path = r"data\simba_projects\New folder\thigmotaxis_optimizado\models\generated_models\Grooming.sav"
    with open(path, 'rb') as f:
        clf = pickle.load(f)
    print("SUCCESS: Model loaded cleanly.")
except Exception as e:
    print("FAILED TO LOAD:")
    traceback.print_exc()
