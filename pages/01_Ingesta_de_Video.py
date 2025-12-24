import streamlit as st
import os
from moviepy.editor import VideoFileClip

# =============== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
    st.stop()

# =============== 2. SELECTOR DE TEMA =================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Oscuro"

theme_mode = st.sidebar.radio(
    "Tema de la interfaz",
    ["Claro", "Oscuro"],
    index=0 if st.session_state.theme_mode == "Claro" else 1,
)
st.session_state.theme_mode = theme_mode

# Paleta verde según tema (con colores de inputs/uploader/browse)
if theme_mode == "Claro":
    colors = {
        "page_bg": "#d1fae5",
        "card_bg": "#ecfdf5",
        "text_main": "#064e3b",
        "shadow": "rgba(15, 23, 42, 0.15)",
        "primary": "#10b981",
        "primary_hover": "#059669",
        "input_bg": "#f0fdf4",
        "input_text": "#064e3b",
        "input_border": "#6ee7b7",
        "browse_bg": "#ffffff",       # << caja blanca
        "browse_text": "#064e3b",
        "browse_border": "#6ee7b7",
    }
else:
    colors = {
        "page_bg": "#022c22",
        "card_bg": "#064e3b",
        "text_main": "#ecfdf5",
        "shadow": "rgba(0,0,0,0.6)",
        "primary": "#22c55e",
        "primary_hover": "#16a34a",
        "input_bg": "#022c22",
        "input_text": "#ecfdf5",
        "input_border": "#34d399",
        "browse_bg": "#111827",       # botón oscuro en tema oscuro
        "browse_text": "#e5e7eb",
        "browse_border": "#4b5563",
    }

# =============== 3. CSS GLOBAL PARA INGESTA =================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

    .tt-ingesta-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: {colors["text_main"]};
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }}

    .tt-ingesta-subtitle {{
        font-size: 0.95rem;
        color: {colors["text_main"]};
        opacity: 0.9;
        margin-bottom: 1.2rem;
    }}

    .tt-ingesta-card {{
        background-color: {colors["card_bg"]};
        border-radius: 18px;
        padding: 1.6rem 1.8rem;
        box-shadow: 0 14px 30px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.18);
        margin-bottom: 1.5rem;
    }}

    /* Labels y textos dentro de la tarjeta */
    .tt-ingesta-card label,
    .tt-ingesta-card p,
    .tt-ingesta-card span {{
        color: {colors["text_main"]} !important;
    }}

    /* TEXT INPUTS */
    .stTextInput input {{
        background-color: {colors["input_bg"]} !important;
        color: {colors["input_text"]} !important;
        border: 1px solid {colors["input_border"]} !important;
        border-radius: 10px;
        font-size: 0.95rem;
    }}
    .stTextInput > label {{
        color: {colors["text_main"]} !important;
        font-weight: 600;
    }}

    /* DATE INPUT */
    .stDateInput input {{
        background-color: {colors["input_bg"]} !important;
        color: {colors["input_text"]} !important;
        border: 1px solid {colors["input_border"]} !important;
        border-radius: 10px;
        font-size: 0.95rem;
    }}
    .stDateInput > label {{
        color: {colors["text_main"]} !important;
        font-weight: 600;
    }}

    /* SELECTBOX */
    div[data-baseweb="select"] > div {{
        background-color: {colors["input_bg"]} !important;
        color: {colors["input_text"]} !important;
        border: 1px solid {colors["input_border"]} !important;
        border-radius: 10px;
    }}
    .stSelectbox > label {{
        color: {colors["text_main"]} !important;
        font-weight: 600;
    }}

    /* FILE UPLOADER - zona de drop */
    div[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {{
        background-color: {colors["input_bg"]} !important;
        border-radius: 12px !important;
        border: 1px dashed {colors["input_border"]} !important;
    }}
    div[data-testid="stFileUploader"] section * {{
        color: {colors["input_text"]} !important;
    }}

    /* FILE UPLOADER - botón "Browse files" */
    div[data-testid="stFileUploader"] button {{
        background-color: {colors["browse_bg"]} !important;
        color: {colors["browse_text"]} !important;
        border: 1px solid {colors["browse_border"]} !important;
        border-radius: 8px !important;
        padding: 0.2rem 0.9rem !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }}

    /* Botones generales (Cargar Video, Confirmar, etc.) */
    .stButton > button {{
        background-color: {colors["primary"]};
        color: white;
        border: none;
        border-radius: 999px;
        padding: 0.45rem 1.3rem;
        font-size: 0.9rem;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: {colors["primary_hover"]};
    }}

    /* Slider con gradiente verde */
    [data-testid="stSlider"] > div > div > div {{
        background: linear-gradient(to right, {colors["primary"]}, {colors["primary_hover"]});
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============== 4. CONFIGURACIÓN DE CARPETA =================
CARPETA_VIDEOS = "videos_data"
if not os.path.exists(CARPETA_VIDEOS):
    os.makedirs(CARPETA_VIDEOS)

# Encabezado
st.markdown('<div class="tt-ingesta-title">📥 Ingesta de Video Experimental</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tt-ingesta-subtitle">'
    'Carga el video del experimento en el laberinto en cruz elevado y selecciona el rango a analizar.'
    '</div>',
    unsafe_allow_html=True,
)

# =============== 5. FORMULARIO DE REGISTRO + CARGA =================
st.markdown('<div class="tt-ingesta-card">', unsafe_allow_html=True)

with st.form("registro_experimento"):
    c1, c2 = st.columns(2)
    with c1:
        id_raton = st.text_input("ID del Espécimen", placeholder="Ej. MOUSE-001")
        tratamiento = st.selectbox("Tratamiento", ["Control", "Diazepam", "Buspirona"])
    with c2:
        fecha = st.date_input("Fecha del Experimento")
        responsable = st.text_input("Responsable", value="Equipo TT")
    
    video_file = st.file_uploader("Cargar Video (MP4 / MOV)", type=["mp4", "mov"])
    
    submitted = st.form_submit_button("Cargar Video")

st.markdown("</div>", unsafe_allow_html=True)

# =============== 6. PROCESAMIENTO DE LA CARGA =================
if submitted and video_file is not None:
    if not id_raton:
        st.error("⚠️ Falta el ID del ratón.")
    else:
        nombre_limpio = f"{id_raton}_{tratamiento}.mp4".replace(" ", "_")
        ruta_guardado = os.path.join("videos_data", nombre_limpio)
        
        with open(ruta_guardado, "wb") as f:
            f.write(video_file.getbuffer())
        
        st.session_state["video_en_edicion"] = ruta_guardado
        st.session_state["id_raton_actual"] = id_raton
        st.success("✅ Video subido correctamente.")

# =============== 7. EDITOR PERSISTENTE =================
if "video_en_edicion" in st.session_state:
    ruta_actual = st.session_state["video_en_edicion"]
    
    st.markdown('<div class="tt-ingesta-card">', unsafe_allow_html=True)
    st.subheader(f"✂️ Edición del video: {st.session_state['id_raton_actual']}")

    try:
        clip = VideoFileClip(ruta_actual)
        duracion = clip.duration

        rango = st.slider(
            "Selecciona el rango de análisis (segundos):",
            min_value=0.0,
            max_value=float(duracion),
            value=(0.0, float(duracion)),
            step=1.0,
            key="slider_recorte",
        )

        start, end = rango

        st.video(ruta_actual, start_time=int(start))
        st.info(f"⏱️ Se analizará del segundo **{start}** al **{end}**.")

        if st.button("💾 Confirmar recorte y procesar"):
            st.session_state["ruta_video_actual"] = ruta_actual
            st.session_state["inicio_recorte"] = start
            st.session_state["fin_recorte"] = end

            st.balloons()
            st.success("✅ ¡Datos guardados! Ahora ve a la página **Configuración Zonas**.")

        clip.close()

    except Exception as e:
        st.error(f"Error cargando el video para edición: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
