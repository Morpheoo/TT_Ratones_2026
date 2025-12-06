import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    """
    Esta función ayuda a encontrar los archivos (Home.py) tanto si estamos
    corriendo en Python normal como si estamos dentro del .exe
    """
    if getattr(sys, '_MEIPASS', False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

if __name__ == "__main__":
    # Truco: Simulamos que alguien escribió el comando en la terminal
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("Home.py"), # Apuntamos a tu archivo principal
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())