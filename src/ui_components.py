"""
ui_components.py — Componentes Reutilizables de Interfaz
TT Ratones 2026 | ESCOM - IPN
"""

import streamlit as st
import base64
import os
import time

def get_logo_b64(logo_path="logo_ria_desktop.png"):
    """Carga el logo y lo devuelve en base64."""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def render_splash_css():
    """Inyecta el CSS necesario para el Splash Screen."""
    st.markdown("""
        <style>
        .splash-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: #121212;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 999999;
            color: white;
            font-family: 'Inter', sans-serif;
        }
        .splash-logo {
            width: 150px;
            height: auto;
            animation: pulse 2s infinite ease-in-out;
            margin-bottom: 2rem;
        }
        .progress-container {
            width: 300px;
            background-color: #333;
            border-radius: 10px;
            height: 6px;
            overflow: hidden;
            border: 1px solid #444;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #800020, #a03040); /* Guinda IPN */
            width: 0%;
            transition: width 0.3s ease-out;
        }
        .status-text {
            margin-top: 1rem;
            font-size: 0.9rem;
            opacity: 0.8;
            font-weight: 500;
            text-align: center;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.05); opacity: 1; }
            100% { transform: scale(1); opacity: 0.8; }
        }
        .fade-out {
            animation: fadeOut 0.8s forwards;
        }
        @keyframes fadeOut {
            from { opacity: 1; pointer-events: all; }
            to { opacity: 0; pointer-events: none; }
        }
        </style>
    """, unsafe_allow_html=True)

def show_splash(progress, message, logo_b64=None):
    """Renderiza el HTML del Splash Screen."""
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="splash-logo">' if logo_b64 else '<div class="splash-logo" style="font-size: 80px;">🐁</div>'
    st.markdown(f"""
        <div class="splash-overlay">
            {logo_html}
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress}%;"></div>
            </div>
            <div class="status-text">{message}</div>
            <div style="margin-top: 5px; font-size: 0.7rem; opacity: 0.5;">TT 2026 - Iniciando servicios...</div>
        </div>
    """, unsafe_allow_html=True)

def generic_splash_loader(diag_generator, logo_path="logo_ria_desktop.png"):
    """
    Controlador genérico para ejecutar un splash screen.
    Recibe un generador que emite (progreso, mensaje).
    """
    render_splash_css()
    splash_placeholder = st.empty()
    logo_b64 = get_logo_b64(logo_path)
    
    try:
        while True:
            progress, msg = next(diag_generator)
            with splash_placeholder:
                show_splash(progress, msg, logo_b64)
    except StopIteration as e:
        # Animar salida
        with splash_placeholder:
            st.markdown("""
                <div class="splash-overlay fade-out">
                    <div style="font-size: 80px;">✓</div>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(0.4)
        splash_placeholder.empty()
        return e.value  # Devuelve el resultado final del generador
    except Exception as e:
        # Si ocurre un error real, debemos limpiar el splash y reportarlo
        splash_placeholder.empty()
        st.error(f"❌ Error crítico durante la carga: {str(e)}")
        # Registrar el error en el sistema si es posible
        import traceback
        st.expander("Detalles técnicos del error").code(traceback.format_exc())
        st.stop() # Detenemos la ejecución para que el usuario vea el error
