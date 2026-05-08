"""
check_setup.py - Valida la configuración del proyecto
Ejecutar antes de usar el sistema por primera vez
"""

from src.config import validate_paths, PROJECT_ROOT, FFMPEG_PATH
import sys

def main():
    print("🔍 Validando configuración del proyecto...")
    print(f"Raíz: {PROJECT_ROOT}\n")
    
    issues = validate_paths()
    
    if not issues:
        print("[OK] ¡Todo está configurado correctamente!")
        print("\n🚀 Puedes ejecutar el sistema sin problemas.")
        return 0
    else:
        print("[WARN] Se encontraron los siguientes problemas:\n")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n📝 Soluciones:")
        print("  1. Verifica que los modelos estén en data/simba_projects/")
        print("  2. Instala FFmpeg: https://ffmpeg.org/download.html")
        print("  3. Configura las rutas en el archivo .env")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
