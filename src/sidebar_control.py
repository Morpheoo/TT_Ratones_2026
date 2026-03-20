"""
Control del sidebar basado en roles - Oculta/muestra páginas según el estado de login y rol
"""
import streamlit as st

def apply_sidebar_visibility():
    """
    Aplica CSS para ocultar páginas del sidebar según el rol del usuario.
    Debe llamarse en cada página después de set_page_config y antes de cualquier contenido.
    """
    logged_in = st.session_state.get("logged_in", False)
    user_role = st.session_state.get("role", None)
    
    hide_pages_css = ""
    
    if not logged_in:
        # Sin login: ocultar todas las páginas excepto Login
        hide_pages_css = """
        <style>
        /* Ocultar todas las páginas excepto Login cuando no hay sesión */
        section[data-testid="stSidebar"] a[href*="Ingesta"],
        section[data-testid="stSidebar"] a[href*="Keypoints"],
        section[data-testid="stSidebar"] a[href*="Configuracion"],
        section[data-testid="stSidebar"] a[href*="Analisis"],
        section[data-testid="stSidebar"] a[href*="Resultados"],
        section[data-testid="stSidebar"] a[href*="Admin"] {
            display: none !important;
        }
        </style>
        """
    elif user_role == "admin":
        # Admin: ocultar módulos experimentales, solo mostrar Admin Panel
        hide_pages_css = """
        <style>
        /* Ocultar módulos experimentales para administradores */
        section[data-testid="stSidebar"] a[href*="Ingesta"],
        section[data-testid="stSidebar"] a[href*="Keypoints"],
        section[data-testid="stSidebar"] a[href*="Configuracion"],
        section[data-testid="stSidebar"] a[href*="Analisis"],
        section[data-testid="stSidebar"] a[href*="Resultados"] {
            display: none !important;
        }
        </style>
        """
    else:
        # Investigador/Estudiante: ocultar Admin Panel
        hide_pages_css = """
        <style>
        /* Ocultar Admin Panel para investigadores y estudiantes */
        section[data-testid="stSidebar"] a[href*="Admin"] {
            display: none !important;
        }
        </style>
        """
    
    st.markdown(hide_pages_css, unsafe_allow_html=True)
