import pandas as pd
import glob
import os

def unify_csv_headers(directory_path):
    print(f"Buscando archivos CSV en: {directory_path}")
    files = glob.glob(os.path.join(directory_path, '*.csv'))
    
    if not files:
        print("No se encontraron archivos CSV.")
        return

    all_columns = set()
    dfs = {}
    
    # 1. Leer todos los dataframes y recolectar todas las columnas únicas
    for f in files:
        df = pd.read_csv(f)
        dfs[f] = df
        all_columns.update(df.columns)
        
    all_columns = sorted(list(all_columns)) # Ordenar para consistencia
    print(f"Total de características únicas encontradas consolidadas: {len(all_columns)}")
    
    # 2. Inyectar columnas faltantes en los dataframes que no las tengan
    for f, df in dfs.items():
        missing_cols = [col for col in all_columns if col not in df.columns]
        
        if missing_cols:
            print(f"Rellenando {len(missing_cols)} columnas faltantes en: {os.path.basename(f)}")
            # Inyectamos las columnas mockeadas con 0.0 (Ausencia de comportamiento/zona)
            for col in missing_cols:
                df[col] = 0.0
            
            # Sobrescribimos el archivo arreglado
            df.to_csv(f, index=False)
        else:
            print(f"El archivo {os.path.basename(f)} ya contenía todas las {len(all_columns)} columnas.")

    print("¡Proceso de armonización de características de SimBA completado!")

if __name__ == "__main__":
    targets_dir = r"C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\csv\targets_inserted"
    unify_csv_headers(targets_dir)
