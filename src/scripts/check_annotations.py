import pandas as pd

csv_path = r"c:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\SimBA_EPM_Analysis\project_folder\csv\targets_inserted\prueba_real_2min.csv"
df = pd.read_csv(csv_path)

total = len(df)
grooming_count = int(df["Grooming"].sum())
thigmotaxis_count = int(df["Thigmotaxis"].sum())
neither_count = int(((df["Grooming"] == 0) & (df["Thigmotaxis"] == 0)).sum())

grooming_pct = grooming_count / total * 100
thigmotaxis_pct = thigmotaxis_count / total * 100

print(f"Total frames: {total}")
print(f"Grooming=1: {grooming_count} ({grooming_pct:.1f}%)")
print(f"Thigmotaxis=1: {thigmotaxis_count} ({thigmotaxis_pct:.1f}%)")
print(f"Neither: {neither_count}")
