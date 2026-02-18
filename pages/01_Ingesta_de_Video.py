import streamlit as st
import os
import sys
from moviepy.editor import VideoFileClip
import re

# ================= 0. PERSISTENCIA =================
# Asegurar que podemos importar desde src
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from src.session_utils import load_session, save_session

# Cargar sesión antes de validar login
load_session()

# =============== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
    st.stop()

# Cargar sesión y establecer init_done si no está ya
if not st.session_state.get("init_done"):
    load_session()
    st.session_state.init_done = True

# GUARDIA: ADMINS NO PUEDEN USAR EL MÓDULO EXPERIMENTAL
if st.session_state.get("role") == "admin":
    st.warning("⛔ El rol de Administrador está limitado a gestión de usuarios.")
    st.info("Para cuidar la integridad de los datos, los administradores no pueden crear ni modificar experimentos.")
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
    # Intentar leer tratamientos previos desde la BD para ofrecer sugerencias
    prev_treatments = []
    try:
        from src.db.connection import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                rows = conn.execute(text("SELECT DISTINCT treatment FROM experiments ORDER BY treatment"))
                prev_treatments = [r[0] for r in rows.fetchall() if r[0]]
    except Exception:
        prev_treatments = []

    with c1:
        id_raton = st.text_input("ID del Espécimen", placeholder="Ej. MOUSE-001")
        # Campo de texto libre para tratamiento con sugerencias (autocompletado básico)
        if "tratamiento_text" not in st.session_state:
            st.session_state["tratamiento_text"] = ""

        tratamiento_input = st.text_input(
            "Tratamiento",
            value=st.session_state.get("tratamiento_text", ""),
            key="tratamiento_text",
            placeholder="Escribe o elige un tratamiento"
        )

        # Mostrar todos los tratamientos guardados como opciones clicables (además del input libre)
        if prev_treatments:
            st.markdown("**Tratamientos guardados:**")
            # Mostrar en filas de hasta 6 botones
            per_row = 6
            for i in range(0, len(prev_treatments), per_row):
                row = prev_treatments[i:i+per_row]
                cols_buttons = st.columns(len(row))
                for j, label in enumerate(row):
                    if cols_buttons[j].button(label, key=f"trat_btn_{i+j}"):
                        st.session_state["tratamiento_text"] = label
                        st.experimental_rerun()
    with c2:
        fecha = st.date_input("Fecha del Experimento")
        responsable = st.text_input("Responsable", value="Equipo TT")
    
    video_file = st.file_uploader("Cargar Video (MP4 / MOV / AVI)", type=["mp4", "mov", "avi"])
    
    submitted = st.form_submit_button("Cargar Video")

st.markdown("</div>", unsafe_allow_html=True)

# =============== 6. PROCESAMIENTO DE LA CARGA =================
if submitted and video_file is not None:
    if not id_raton:
        st.error("⚠️ Falta el ID del ratón.")
    else:
        # Preferir el texto del campo libre (guardado en session), o vacío si no existe
        tratamiento = (st.session_state.get("tratamiento_text") or "").strip()
        nombre_limpio = f"{id_raton}_{tratamiento}.mp4".replace(" ", "_")
        ruta_guardado = os.path.join("videos_data", nombre_limpio)
        
        with open(ruta_guardado, "wb") as f:
            f.write(video_file.getbuffer())
        
        st.session_state["video_en_edicion"] = ruta_guardado
        st.session_state["id_raton_actual"] = id_raton
        # Guardar tratamiento en la sesión para que el procesamiento lo persista en BD
        st.session_state["treatment"] = tratamiento
        save_session()
        st.success("✅ Video subido correctamente.")

# =============== 7. EDITOR PERSISTENTE =================
if "video_en_edicion" in st.session_state:
    ruta_actual = st.session_state["video_en_edicion"]
    
    st.markdown('<div class="tt-ingesta-card">', unsafe_allow_html=True)
    st.subheader(f"✂️ Edición del video: {st.session_state['id_raton_actual']}")

    try:
        clip = VideoFileClip(ruta_actual)
        duracion = clip.duration

        def fmt_seconds_to_mmss(s: float) -> str:
            s = max(0, int(s))
            mm = s // 60
            ss = s % 60
            return f"{mm:02d}:{ss:02d}"

        def parse_mmss_to_seconds(text: str):
            text = (text or "").strip()
            # Accept formats like mm:ss or m:ss or ss
            m = re.match(r"^(\d+):(\d{1,2})$", text)
            if m:
                minutes = int(m.group(1))
                seconds = int(m.group(2))
                return minutes * 60 + seconds
            # fallback: plain seconds number
            if re.match(r"^\d+$", text):
                return int(text)
            return None

        # Defaults for inputs
        default_start = fmt_seconds_to_mmss(0)
        default_end = fmt_seconds_to_mmss(duracion)

        c1, c2 = st.columns(2)
        with c1:
            start_text = st.text_input("Inicio (mm:ss)", value=default_start, key="inicio_recorte_text", placeholder="mm:00")

        with c2:
            end_text = st.text_input("Fin (mm:ss)", value=default_end, key="fin_recorte_text", placeholder="mm:00")

        start_seconds = parse_mmss_to_seconds(start_text)
        end_seconds = parse_mmss_to_seconds(end_text)

        # Validate inputs
        valid = True
        if start_seconds is None:
            st.error("Formato inválido para Inicio. Use mm:ss o segundos enteros.")
            valid = False
        if end_seconds is None:
            st.error("Formato inválido para Fin. Use mm:ss o segundos enteros.")
            valid = False
        if valid:
            if start_seconds < 0 or start_seconds > duracion:
                st.error("El tiempo de Inicio está fuera de rango del video.")
                valid = False
            if end_seconds < 0 or end_seconds > duracion:
                st.error("El tiempo de Fin está fuera de rango del video.")
                valid = False
            if start_seconds >= end_seconds:
                st.error("El tiempo de Inicio debe ser menor que el tiempo de Fin.")
                valid = False

        # Show video starting at parsed start time if valid, otherwise default to 0
        if valid:
            st.video(ruta_actual, start_time=int(start_seconds))
            st.info(f"⏱️ Se analizará de **{fmt_seconds_to_mmss(start_seconds)}** a **{fmt_seconds_to_mmss(end_seconds)}** ({start_seconds}–{end_seconds} s).")

            if st.button("💾 Confirmar recorte y procesar"):
                st.session_state["ruta_video_actual"] = ruta_actual
                st.session_state["inicio_recorte"] = start_seconds
                st.session_state["fin_recorte"] = end_seconds
                # Persistir sesión
                save_session()

                # Guardar/asegurar tratamiento en la base de datos para histórico/autocompletado
                try:
                    from src.db.connection import get_db_engine
                    from sqlalchemy import text
                    engine = get_db_engine()
                    if engine:
                        with engine.connect() as conn:
                            # Intentar obtener el id del usuario
                            usr_email = st.session_state.get("user", "admin")
                            res_usr = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": usr_email}).fetchone()
                            user_id = res_usr[0] if res_usr else None

                            # Si ya existe un experimento con este video_path, actualizar su treatment y marcar processed=False
                            existing = conn.execute(text("SELECT id FROM experiments WHERE video_path = :path LIMIT 1"), {"path": ruta_actual}).fetchone()
                            if existing:
                                conn.execute(text("UPDATE experiments SET treatment = :treat, processed = FALSE WHERE id = :eid"), {"treat": st.session_state.get("treatment", ""), "eid": existing[0]})
                            else:
                                # Insertar registro mínimo para preservar tratamiento en histórico
                                conn.execute(text(
                                    """
                                    INSERT INTO experiments (rat_id, treatment, experiment_date, responsible, video_path, duration_seconds, created_by, processed)
                                    VALUES (:rid, :treat, CURRENT_DATE, :resp, :path, NULL, :uid, FALSE)
                                    """), {
                                    "rid": st.session_state.get("id_raton_actual", "Unknown-Rat"),
                                    "treat": st.session_state.get("treatment", ""),
                                    "resp": st.session_state.get("user_name", "Investigador"),
                                    "path": ruta_actual,
                                    "uid": user_id
                                })
                            conn.commit()
                except Exception as e:
                    st.error(f"Error guardando tratamiento en BD: {e}")

                st.balloons()
                st.success("✅ ¡Datos guardados! Ahora ve a la página **Configuración Zonas**.")
        else:
            # still show full video preview if parsing invalid
            st.video(ruta_actual)

        clip.close()

    except Exception as e:
        st.error(f"Error cargando el video para edición: {e}")

    st.markdown("</div>", unsafe_allow_html=True)