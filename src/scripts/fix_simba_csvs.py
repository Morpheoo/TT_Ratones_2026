import pandas as pd
import os
import glob

def fix_missing_columns(directory):
    print(f"Revisando archivos en: {directory}")
    missing_cols = [
        'pared23 Animal_1 facing', 
        'pared23 Animal_1 Center in zone', 
        'pared23 Animal_1 Center distance'
    ]
    
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    
    for file in csv_files:
        print(f"Checando {os.path.basename(file)}...")
        df = pd.read_csv(file)
        modified = False
        
        for col in missing_cols:
            if col not in df.columns:
                df[col] = 0.0  # Asumimos valor por defecto
                modified = True
        
        if modified:
            df.to_csv(file, index=False)
            print(f"  ¡Reparado! Columnas faltantes añadidas y archivo guardado.")
        else:
            print("  Todo correcto, no requiere cambios.")

if __name__ == "__main__":
    targets_dir = r"data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\csv\targets_inserted"
    features_dir = r"data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\csv\features_extracted"
    
    fix_missing_columns(targets_dir)
    print("--------------------------------------------------")
    fix_missing_columns(features_dir)
    print("¡Proceso terminado exhaustivamente!")
