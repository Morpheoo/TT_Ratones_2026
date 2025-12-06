import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="TT 2026 - Sistema de Análisis EPM",
    page_icon="🐭",
    layout="wide",
)

# 2. SELECTOR DE TEMA (COMPARTIDO)
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Oscuro"

theme_mode = st.sidebar.radio(
    "Tema de la interfaz",
    ["Claro", "Oscuro"],
    index=0 if st.session_state.theme_mode == "Claro" else 1,
)
st.session_state.theme_mode = theme_mode

# Paleta VERDE según el tema
if theme_mode == "Claro":
    colors = {
        "page_bg": "#d1fae5",      # fondo
        "card_bg": "#ecfdf5",
        "text_main": "#064e3b",    # VERDE OSCURO
        "shadow": "rgba(15, 23, 42, 0.15)",
        "primary": "#10b981",
        "primary_hover": "#059669",
    }
else:  # Oscuro
    colors = {
        "page_bg": "#022c22",
        "card_bg": "#064e3b",
        "text_main": "#ecfdf5",    # texto claro en oscuro
        "shadow": "rgba(0,0,0,0.6)",
        "primary": "#22c55e",
        "primary_hover": "#16a34a",
    }

# 3. CSS GLOBAL PARA HOME
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

    .tt-home-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        color: {colors["text_main"]};
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
    }}

    .tt-home-subtitle {{
        font-size: 1.0rem;
        color: {colors["text_main"]};
        opacity: 0.9;
        margin-bottom: 1.8rem;
    }}

    .tt-home-card {{
        background-color: {colors["card_bg"]};
        border-radius: 18px;
        padding: 1.6rem 1.8rem;
        box-shadow: 0 14px 30px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.18);
        height: 100%;
    }}

    /* Título y texto dentro de las tarjetas (forzado a verde/clarito) */
    .tt-home-card-title {{
        margin-top: 0;
        margin-bottom: 0.4rem;
        font-size: 1.1rem;
        font-weight: 700;
        color: {colors["text_main"]} !important;
    }}

    .tt-home-card-text {{
        margin: 0;
        font-size: 0.9rem;
        color: {colors["text_main"]} !important;
        opacity: 0.9;
    }}

    .tt-home-footer {{
        text-align: center;
        margin-top: 2rem;
        font-size: 0.8rem;
        opacity: 0.7;
        color: {colors["text_main"]};
    }}

    .tt-home-badge {{
        display: inline-block;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        font-size: 0.75rem;
        background-color: rgba(16,185,129,0.12);
        color: {colors["text_main"]};
        margin-bottom: 0.9rem;
    }}

    .stButton > button {{
        background-color: {colors["primary"]};
        color: white;
        border: none;
        border-radius: 999px;
        padding: 0.45rem 1.1rem;
        font-size: 0.9rem;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: {colors["primary_hover"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# 4. PROTECCIÓN DE ACCESO (si quieres activarla, descomenta)
# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.warning("⚠️ Debes iniciar sesión en la página **Login** antes de usar el sistema.")
#     st.stop()

# 5. CONTENIDO DEL HOME
st.markdown(
    '<div class="tt-home-badge">TT 2026-A155 · Laberinto en cruz elevado</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="tt-home-title">Bienvenido al Sistema de Análisis EPM</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="tt-home-subtitle">'
    'Prototipo para el análisis automatizado y visualización del comportamiento '
    'de roedores en el laberinto en cruz elevado.'
    '</div>',
    unsafe_allow_html=True,
)

st.write("")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="tt-home-card">', unsafe_allow_html=True)
    st.markdown(
        "<h3 class='tt-home-card-title'>📥 Ingesta de Video</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='tt-home-card-text'>Carga videos experimentales del laberinto en cruz elevado, "
        "valida formato, duración y prepara los datos para su análisis.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    st.markdown('<div class="tt-home-card">', unsafe_allow_html=True)
    st.markdown(
        "<h3 class='tt-home-card-title'>⚙️ Configuración de Zonas</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='tt-home-card-text'>Define las regiones de interés (brazos abiertos, cerrados y zona central) "
        "para el conteo automático de entradas, tiempo de permanencia y eventos.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="tt-home-card">', unsafe_allow_html=True)
    st.markdown(
        "<h3 class='tt-home-card-title'>🧠 Análisis IA</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='tt-home-card-text'>Ejecuta los modelos de visión por computadora (detección YOLO, "
        "rastreo y análisis de comportamiento) sobre los videos seleccionados.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    st.markdown('<div class="tt-home-card">', unsafe_allow_html=True)
    st.markdown(
        "<h3 class='tt-home-card-title'>📊 Resultados y Estadísticas</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='tt-home-card-text'>Consulta métricas de ansiedad, gráficos de tiempo en brazos, "
        "tablas resumen y exportación de resultados para el reporte experimental.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="tt-home-footer">ESCOM - IPN · Prototipo académico · No usar en producción</div>',
    unsafe_allow_html=True,
)
