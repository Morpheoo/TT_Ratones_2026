import streamlit as st
import json
import os

SESSION_FILE = ".streamlit_session.json"

def save_session():
    """Guarda las variables críticas del state en un archivo local."""
    # Lista de variables a persistir
    keys_to_save = [
        "logged_in", "user", "role", "user_name", 
        "ruta_video_actual", "inicio_recorte", "fin_recorte", 
        "dlc_device_opt", "theme_mode", "zonas_configuradas",
        "video_en_edicion", "id_raton_actual"
    ]
    
    data = {}
    for key in keys_to_save:
        if key in st.session_state:
            data[key] = st.session_state[key]

    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error guardando sesión: {e}")

def load_session():
    """Carga el estado previo si existe."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
            for key, value in data.items():
                # Forzamos la carga si el valor actual es nulo o no existe
                if key not in st.session_state or st.session_state[key] is None or st.session_state[key] == False:
                    st.session_state[key] = value
        except Exception as e:
            print(f"Error cargando sesión: {e}")

def clear_session():
    """Limpia el archivo de sesión."""
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except:
            pass
