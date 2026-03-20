import os, sys, shutil
import pandas as pd
import traceback

config = r'C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\project_config.ini'
VIDEO_NAME = 'mike_prueba1_full'
feat_dir = r'C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\csv\features_extracted'
out_path = os.path.join(feat_dir, f'{VIDEO_NAME}.csv')

try:
    from simba.feature_extractors.feature_extractor_8bp import ExtractFeaturesFrom8BPs
    print('>>> Starting 8BP extraction...')
    extractor = ExtractFeaturesFrom8BPs(config_path=config)
    extractor.run()
    print('>>> Extractor ran.')
    if os.path.exists(out_path):
        df2 = pd.read_csv(out_path, nrows=1)
        print(f'SUCCESS! {len(df2.columns)} features generated for {VIDEO_NAME}')
    else:
        print(f'WARNING: output NOT found at {out_path}')
        print('Files in feat_dir:', os.listdir(feat_dir))
except Exception as e:
    traceback.print_exc()
