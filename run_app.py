import streamlit.web.cli as stcli
import os, sys, subprocess

def resolve_path(path):
    """
    Esta función ayuda a encontrar los archivos (Home.py) tanto si estamos
    corriendo en Python normal como si estamos dentro del .exe
    """
    if getattr(sys, '_MEIPASS', False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

def ensure_services_ready():
    """
    Levanta los servicios (Docker, BD) ANTES de que Streamlit inicie.
    Esto garantiza que todo está listo cuando el usuario abre la app.
    """
    print("\n" + "="*70)
    print("🔧 PRE-CHECK: Verificando y levantando servicios...")
    print("="*70)
    
    start_script = resolve_path("start_services.py")
    
    try:
        result = subprocess.run(
            [sys.executable, start_script],
            capture_output=False,
            timeout=120  # Máximo 2 minutos para todo
        )
        if result.returncode != 0:
            print("\n[WARN] ADVERTENCIA: Los servicios no se iniciaron correctamente.")
            print("    Streamlit continuará, pero la BD podría no estar disponible.\n")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("\n[ERROR] TIMEOUT: Los servicios tardaron demasiado en iniciar.\n")
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR al ejecutar start_services.py: {e}\n")
        return False

if __name__ == "__main__":
    # 1. Levantar servicios PRIMERO
    ensure_services_ready()
    
    # 2. Luego ejecutar Streamlit
    print("\n" + "="*70)
    print("🚀 Iniciando Streamlit...")
    print("="*70 + "\n")
    
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("Home.py"), # Apuntamos a tu archivo principal
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
