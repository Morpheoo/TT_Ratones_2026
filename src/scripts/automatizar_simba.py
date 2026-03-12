import argparse
import os
import sys

# Add numpy/pandas/simba imports
from simba.feature_extractors.feature_extractor_8bp import ExtractFeaturesFrom8bps
from simba.roi_tools.ROI_feature_analyzer import ROIFeatureCreator

def main():
    parser = argparse.ArgumentParser(description="Automatiza la extracción de features y ROIs en SimBA sin abrir la GUI.")
    parser.add_argument("--config", type=str, required=True, help="Ruta al archivo project_config.ini del proyecto SimBA.")
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    if not os.path.exists(config_path):
        print(f"Error: No se encontró el archivo de configuración en {config_path}")
        sys.exit(1)

    print("="*60)
    print(" INICIANDO AUTOMATIZACIÓN DE EXTRACCIÓN DE FEATURES - SIMBA")
    print("="*60)

    try:
        print("\n[1/2] Extrayendo features (8 body-parts)...")
        feature_extractor = ExtractFeaturesFrom8bps(config_path=config_path)
        feature_extractor.run()
        print("-> Extracción de features completada.")
        
        print("\n[2/2] Añadiendo datos de ROI (Region of Interest - Bordes/Paredes)...")
        roi_analyzer = ROIFeatureCreator(
            config_path=config_path, 
            body_parts=['Center'], 
            append_data=True
        )
        roi_analyzer.run()
        roi_analyzer.save()
        print("-> Datos de ROI añadidos exitosamente a las features.")
        
        print("\n¡Pipeline de extracción completado! Los CSV están listos para ser usados en la pestaña 'Label Behavior' o para entrenamiento.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error en el pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
