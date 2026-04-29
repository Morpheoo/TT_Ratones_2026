"""
ui_components.py — Componentes Reutilizables de Interfaz
TT Ratones 2026 | ESCOM - IPN
"""

import base64
import html
import os
import time
import traceback

import streamlit as st

DEFAULT_SPLASH_LOGO_PATH = os.path.join("assets", "logos", "logo_ria_desktop.png")
_ACTIVE_PAGE_KEY = "_tt_active_page"


def resolve_logo_path(logo_path=None):
    """Resuelve el logo del splash usando la ruta oficial del proyecto."""
    candidate = logo_path or DEFAULT_SPLASH_LOGO_PATH
    if os.path.isabs(candidate):
        return candidate
    if os.path.exists(candidate):
        return candidate
    return os.path.join(os.getcwd(), candidate)


def get_logo_b64(logo_path=None):
    """Carga el logo y lo devuelve en base64."""
    resolved_logo = resolve_logo_path(logo_path)
    if os.path.exists(resolved_logo):
        with open(resolved_logo, "rb") as file_handle:
            return base64.b64encode(file_handle.read()).decode()
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
            background-color: #f6f4f5;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 999999;
            color: #2b2230;
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
            background-color: #e7dde1;
            border-radius: 10px;
            height: 6px;
            overflow: hidden;
            border: 1px solid #d4c5cb;
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
            opacity: 0.9;
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

def show_splash(progress, message, logo_b64=None, subtitle="TT 2026 - Inicializando módulo..."):
    """Renderiza el HTML del Splash Screen."""
    safe_message = html.escape(str(message))
    safe_subtitle = html.escape(str(subtitle))
    progress_value = max(0, min(int(progress), 100))
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="splash-logo">'
        if logo_b64
        else '<div class="splash-logo" style="font-size: 80px;">🐁</div>'
    )
    st.markdown(f"""
        <div class="splash-overlay">
            {logo_html}
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress_value}%;"></div>
            </div>
            <div class="status-text">{safe_message}</div>
            <div style="margin-top: 5px; font-size: 0.7rem; opacity: 0.5;">{safe_subtitle}</div>
        </div>
    """, unsafe_allow_html=True)


def generic_splash_loader(diag_generator, logo_path=None, subtitle="TT 2026 - Inicializando módulo..."):
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
                show_splash(progress, msg, logo_b64, subtitle=subtitle)
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
        st.error(f"[ERROR] Error crítico durante la carga: {str(e)}")
        st.expander("Detalles técnicos del error").code(traceback.format_exc())
        st.stop()  # Detenemos la ejecución para que el usuario vea el error


def page_splash_sequence(messages, step_delay=0.18):
    """Convierte una lista de mensajes en una secuencia progresiva de splash."""
    if not messages:
        messages = ["Inicializando interfaz..."]

    total_steps = len(messages)
    for index, message in enumerate(messages, start=1):
        progress = int((index / total_steps) * 100)
        yield progress, message
        time.sleep(step_delay)


def run_page_splash(page_id, messages, logo_path=None, subtitle="TT 2026 - Cargando módulo..."):
    """Muestra el splash una sola vez por navegación entre páginas."""
    current_page = st.session_state.get(_ACTIVE_PAGE_KEY)
    if current_page == page_id:
        return

    generic_splash_loader(
        page_splash_sequence(messages),
        logo_path=logo_path,
        subtitle=subtitle,
    )
    st.session_state[_ACTIVE_PAGE_KEY] = page_id


def load_resource_with_splash(
    page_id,
    state_key,
    generator_factory,
    dependency_signature=None,
    logo_path=None,
    subtitle="TT 2026 - Cargando módulo...",
):
    """
    Ejecuta una carga bajo splash al entrar a una página o cuando cambian sus dependencias.
    """
    signature_key = f"{state_key}__splash_signature"
    previous_page = st.session_state.get(_ACTIVE_PAGE_KEY)
    should_reload = (
        previous_page != page_id
        or state_key not in st.session_state
        or st.session_state.get(signature_key) != dependency_signature
    )

    if should_reload:
        st.session_state[state_key] = generic_splash_loader(
            generator_factory(),
            logo_path=logo_path,
            subtitle=subtitle,
        )
        st.session_state[signature_key] = dependency_signature

    st.session_state[_ACTIVE_PAGE_KEY] = page_id
    return st.session_state.get(state_key)
