import pandas as pd
import os

files = ["videos_data/C1-R1_full_dlc.csv", "videos_data/C2-R1_full_dlc.csv", "videos_data/C7-R1_full_dlc.csv"]

for f in files:
    if os.path.exists(f):
        try:
            df = pd.read_csv(f)
            print(f"{f}: {len(df)} rows")
        except:
            print(f"{f}: Error reading")
    else:
        print(f"{f}: Not found")
