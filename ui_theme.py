# ui_theme.py
import streamlit as st

def _get_theme_name() -> str:
    # Tema por defecto
    default = st.session_state.get("theme_name", "Claro")

    option = st.sidebar.radio(
        "Tema de la interfaz",
        ["Claro", "Oscuro"],
        index=0 if default == "Claro" else 1,
        key="theme_radio",
    )
    st.session_state["theme_name"] = option
    return option


def use_theme():
    """
    Aplica el CSS global según el tema seleccionado (Claro/Oscuro)
    y devuelve el diccionario de colores por si lo quieres usar.
    """
    theme_name = _get_theme_name()

    if theme_name == "Oscuro":
        colors = {
            "page_bg": "#020617",
            "banner_bg": "#0f172a",
            "banner_text": "#e5e7eb",
            "card_bg": "#020617",
            "card_border": "#1f2937",
            "primary": "#22c55e",
            "primary_hover": "#16a34a",
            "input_bg": "#020617",
            "input_border": "#374151",
            "text_main": "#e5e7eb",
        }
    else:  # CLARO (el del mockup)
        colors = {
            "page_bg": "#dcefee",        # fondo verde-agua clarito
            "banner_bg": "#53b5ac",      # banda superior verde-azulada
            "banner_text": "#ffffff",
            "card_bg": "#ffffff",
            "card_border": "#bcd6d3",
            "primary": "#26a69a",        # botón verde-agua
            "primary_hover": "#1f8e84",
            "input_bg": "#ffffff",
            "input_border": "#9ca3af",
            "text_main": "#064e3b",
        }

    css = f"""
    <style>
    :root {{
      --page-bg: {colors['page_bg']};
      --banner-bg: {colors['banner_bg']};
      --banner-text: {colors['banner_text']};
      --card-bg: {colors['card_bg']};
      --card-border: {colors['card_border']};
      --primary: {colors['primary']};
      --primary-hover: {colors['primary_hover']};
      --input-bg: {colors['input_bg']};
      --input-border: {colors['input_border']};
      --text-main: {colors['text_main']};
    }}

    .main {{
      background-color: var(--page-bg);
    }}

    /* Contenedor principal */
    .block-container {{
      padding-top: 2.5rem;
      padding-bottom: 2.5rem;
    }}

    /* Banda superior del título (como en tu mockup) */
    .tt-banner {{
      background-color: var(--banner-bg);
      color: var(--banner-text);
      padding: 1.4rem 1rem;
      text-align: center;
      font-weight: 700;
      letter-spacing: 0.04em;
      font-size: 1rem;
      margin-bottom: 2.2rem;
      border-radius: 0.4rem;
    }}

    /* Tarjeta central (login, formularios, etc.) */
    .tt-card {{
      background-color: var(--card-bg);
      border-radius: 0.75rem;
      padding: 2rem 2.5rem;
      border: 1px solid var(--card-border);
      box-shadow: 0 18px 35px rgba(15,23,42,0.18);
    }}

    .tt-card-title {{
      text-align: center;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 1.5rem;
    }}

    /* Botones principales */
    .stButton > button {{
      background-color: var(--primary);
      color: white;
      border-radius: 0.4rem;
      border: none;
      padding: 0.45rem 1.5rem;
      font-weight: 600;
    }}
    .stButton > button:hover {{
      background-color: var(--primary-hover);
    }}

    /* Inputs de texto */
    .stTextInput > div > input {{
      background-color: var(--input-bg);
      border-radius: 0.4rem;
      border: 1px solid var(--input-border);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return colors


def render_header():
    """
    Muestra la banda superior con el título largo del prototipo.
    """
    st.markdown(
        """
        <div class="tt-banner">
            PROTOTIPO PARA ANÁLISIS AUTOMATIZADO Y VISUALIZACIÓN DE COMPORTAMIENTO
            DE ESPECÍMENES EN MODELOS DE ANSIEDAD
        </div>
        """,
        unsafe_allow_html=True,
    )
