import pandas as pd
import numpy as np

csv_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133DLC_snapshot-200000.csv"

try:
    df = pd.read_csv(csv_path, header=[1, 2])
    print("Data loaded successfully.")
    
    # We want to see where the "good" detections are versus the "bad" ones.
    # Assuming garbage is on the left, we look at the distribution of X coordinates.
    
    all_x = []
    
    bodyparts = df.columns.levels[0].unique()
    
    for bp in bodyparts:
        if bp == 'bodyparts': continue
        
        try:
            x_col = df[bp]['x']
            likelihood_col = df[bp]['likelihood']
        
        except KeyError:
            continue
            
        # Filter for somewhat confident detections to see where the model "thinks" the mouse is
        confident_detections = x_col[likelihood_col > 0.5]
        all_x.extend(confident_detections.dropna().tolist())

    s = pd.Series(all_x)
    print("\nX Coordinate Statistics (Likelihood > 0.5):")
    print(s.describe())
    
    print("\nQuantiles:")
    print(s.quantile([0.05, 0.1, 0.2, 0.3, 0.4, 0.5]))

except Exception as e:
    print(f"Error: {e}")
