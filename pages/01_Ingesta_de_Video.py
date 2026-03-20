import streamlit as st
import os
import sys
import re
# moviepy se importa de forma LAZY dentro del bloque de edición (ver abajo)
# para evitar ~3s de overhead en cada carga de página.

# ================= 0. PERSISTENCIA =================
# REGLA #1: set_page_config SIEMPRE primero, antes de cualquier st.*
st.set_page_config(page_title="Ingesta de Video (EPM)", page_icon="📥", layout="wide")

if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

from ui_components import generic_splash_loader
from session_utils import load_session, save_session
from access_control import require_researcher
from sidebar_control import apply_sidebar_visibility

# Cargar sesión antes de validar login
load_session()

# Aplicar control de sidebar
apply_sidebar_visibility()

# =============== 1. VERIFICAR LOGIN Y ROL ==================
require_researcher()  # Solo investigadores y estudiantes, NO admins

# Cargar sesión y establecer init_done si no está ya
if not st.session_state.get("init_done"):
    load_session()
    st.session_state.init_done = True

# GUARDIA: ADMINS NO PUEDEN USAR EL MÓDULO EXPERIMENTAL
if st.session_state.get("role") == "admin":
    st.warning("⛔ El rol de Administrador está limitado a gestión de usuarios.")
    st.info("Para cuidar la integridad de los datos, los administradores no pueden crear ni modificar experimentos.")
    st.stop()

# =============== 2. TEMA Y ESTILOS =================
from ui_theme import use_theme
use_theme()

def ingestion_loading_sequence():
    """Generador para el splash screen de Ingesta."""
    yield 30, "Conectando con la base de datos..."
    from db.connection import get_db_engine
    engine = get_db_engine()
    
    yield 70, "Preparando entorno de carga..."
    # No buscamos tratamientos previos para el selector, según solicitud del usuario
    
    yield 100, "Módulo de ingesta listo."
    return []

# ================== 2. EJECUCIÓN DEL SPLASH SCREEN (INGESTA) ==================
if "ingestion_loaded" not in st.session_state:
    st.session_state["_prev_treatments_cache"] = generic_splash_loader(ingestion_loading_sequence())
    st.session_state.ingestion_loaded = True

# =============== 3. CSS GLOBAL PARA INGESTA =================
st.markdown(
    """
    <style>
    .tt-ingesta-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: var(--text-main);
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }

    .tt-ingesta-subtitle {
        font-size: 0.95rem;
        color: var(--text-main);
        opacity: 0.9;
        margin-bottom: 1.2rem;
    }

    .tt-ingesta-card {
        background-color: var(--card-bg);
        border-radius: 0.5rem;
        padding: 1.6rem 1.8rem;
        box-shadow: 0 4px 15px var(--shadow);
        border: 1px solid var(--card-border);
        border-top: 3px solid var(--primary);
        margin-bottom: 1.5rem;
    }

    /* Labels y textos dentro de la tarjeta */
    .tt-ingesta-card label,
    .tt-ingesta-card p,
    .tt-ingesta-card span {
        color: var(--text-main) !important;
    }

    /* SELECTBOX */
    div[data-baseweb="select"] > div {
        background-color: var(--input-bg) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 0.35rem;
    }
    .stSelectbox > label {
        color: var(--text-main) !important;
        font-weight: 600;
    }

    /* FILE UPLOADER - zona de drop */
    div[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {
        background-color: var(--input-bg) !important;
        border-radius: 0.5rem !important;
        border: 1px dashed var(--input-border) !important;
    }
    div[data-testid="stFileUploader"] section * {
        color: var(--text-main) !important;
    }

    /* FILE UPLOADER - botón "Browse files" */
    div[data-testid="stFileUploader"] button {
        background-color: var(--card-bg) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 0.35rem !important;
        padding: 0.2rem 0.9rem !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* Slider con gradiente IPN */
    [data-testid="stSlider"] > div > div > div {
        background: linear-gradient(to right, var(--primary), var(--primary-hover));
    }
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
        # Campo libre para el tratamiento según solicitud del usuario
        tratamiento_input = st.text_input(
            "ID del Tratamiento",
            placeholder="Ej. Diazepam 5mg, Molécula X, Vehículo...",
            key="tratamiento_text"
        )
    with c2:
        fecha = st.date_input("Fecha del Experimento")
        responsable = st.text_input("Responsable", value="Equipo TT")
    
    video_file = st.file_uploader("Cargar Video (MP4 / MOV / AVI)", type=["mp4", "mov", "avi"])
    
    submitted = st.form_submit_button("Cargar Video y Reemplazar Actual")

st.markdown("</div>", unsafe_allow_html=True)

if "video_en_edicion" in st.session_state:
    st.info(
        "Seleccionar un archivo en el formulario no cambia por sí solo el video activo. "
        "Para reemplazarlo, pulsa `Cargar Video y Reemplazar Actual` y luego confirma "
        "que el bloque azul `Video en edición` muestre el nuevo nombre."
    )

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
        
        # ── Resetear estado de análisis previo al cargar video nuevo ────────
        st.session_state["video_en_edicion"]  = ruta_guardado
        st.session_state["id_raton_actual"]   = id_raton
        st.session_state["treatment_id"]       = tratamiento   # usado por 04_Analisis_Final
        st.session_state["treatment"]          = tratamiento
        # Limpiar contexto de análisis anterior para no confundir keypoints/zonas
        for _k in ["ruta_video_actual", "inicio_recorte", "fin_recorte",
                   "pipeline_dlc_activo", "zonas_configuradas"]:
            st.session_state.pop(_k, None)
        save_session()
        st.success(f"✅ Video '**{video_file.name}**' subido correctamente. Confirma el recorte abajo.")
        st.rerun()  # Forzar rerender para mostrar el nuevo video inmediatamente

# =============== 7. EDITOR PERSISTENTE =================
if "video_en_edicion" in st.session_state:
    ruta_actual = st.session_state["video_en_edicion"]

    # ── Guardia: si el archivo ya no existe en disco, limpiar la sesión ───────
    if not os.path.exists(ruta_actual):
        st.warning("⚠️ El video en sesión ya no existe en disco. Carga uno nuevo.")
        st.session_state.pop("video_en_edicion", None)
        st.stop()

    st.markdown('<div class="tt-ingesta-card">', unsafe_allow_html=True)

    # ── Banner del video activo ──────────────────────────────────────────────
    st.warning(
        "El recorte de abajo siempre se aplica al video mostrado en `Video en edición`. "
        "Si acabas de seleccionar otro archivo arriba, primero debes cargarlo."
    )

    nombre_video = os.path.basename(ruta_actual)
    id_display   = st.session_state.get("id_raton_actual", nombre_video)
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1a1a2e,#0f3460);border-left:4px solid #63b3ed;
                    border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:1rem;">
            <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#63b3ed;">Video en edición</div>
            <div style="font-size:1.1rem;font-weight:700;color:#EDF2F7;font-family:monospace;">{nombre_video}</div>
            <div style="font-size:0.7rem;color:rgba(237,242,247,0.5);font-family:monospace;">ID: {id_display} · {ruta_actual}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader(f"✂️ Rango de análisis")

    try:
        # Lazy import: moviepy carga FFmpeg internamente; solo se importa aquí
        # donde realmente se necesita (post-upload), no al tope de la página.
        from moviepy.editor import VideoFileClip
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
        if valid and start_seconds is not None and end_seconds is not None:
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
        if valid and start_seconds is not None and end_seconds is not None:
            st.video(ruta_actual, start_time=int(start_seconds))
            st.info(f"⏱️ Se analizará de **{fmt_seconds_to_mmss(start_seconds)}** a **{fmt_seconds_to_mmss(end_seconds)}** ({start_seconds}–{end_seconds} s).")

            if st.button("💾 Confirmar recorte y continuar →", type="primary"):
                st.session_state["ruta_video_actual"] = ruta_actual
                st.session_state["inicio_recorte"]   = start_seconds
                st.session_state["fin_recorte"]       = end_seconds
                # treatment_id ya fue guardado en el submit del form
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
