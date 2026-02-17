
import pandas as pd
import os
import glob

# Path to the specific H5 file found
H5_FILE = r"videos_data\prueba_real_2minDLC_snapshot-200000.h5"

def convert_h5_to_csv():
    if not os.path.exists(H5_FILE):
        # Try to find any H5 file matching the video name if specific one fails
        h5_files = glob.glob(r"videos_data\prueba_real_2min*.h5")
        if not h5_files:
            print("Error: No H5 file found.")
            return
        h5_path = h5_files[0]
    else:
        h5_path = H5_FILE
        
    print(f"Converting {h5_path} to CSV...")
    try:
        df = pd.read_hdf(h5_path)
        csv_path = h5_path.replace(".h5", ".csv")
        df.to_csv(csv_path)
        print(f"✅ Successfully created: {csv_path}")
    except Exception as e:
        print(f"Error converting H5 to CSV: {e}")

if __name__ == "__main__":
    convert_h5_to_csv()
