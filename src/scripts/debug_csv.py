import pandas as pd

csv_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\videos_data\control2_Control_trimmed_102_133DLC_snapshot-200000.csv"

try:
    df = pd.read_csv(csv_path, header=[1, 2])
    print("Columns dump:")
    print(df.columns)
    print("\nFirst bodypart columns:")
    print(df[df.columns.levels[0][0]].columns)
except Exception as e:
    print(f"Error: {e}")
