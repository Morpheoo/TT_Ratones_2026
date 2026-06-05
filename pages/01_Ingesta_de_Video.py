import os
import sys

import streamlit as st

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session, save_session
from ui_components import run_page_splash
import importlib
import ui_theme

importlib.reload(ui_theme)
from ui_theme import render_topbar, use_theme, inject_sidebar_profile

# Importar sistema de tratamientos
from treatments import initialize_treatments_table, get_all_treatments, add_treatment, delete_treatment

st.set_page_config(page_title="Ingesta de vídeo", page_icon="assets/logos/logo_ria.png", layout="wide")

load_session()
colors = use_theme()

# CSS para traducir file_uploader completamente a español
st.markdown("""
<style>
/* Ocultar textos originales en inglés y reemplazar por español */
[data-testid="stFileUploader"] section small {
    font-size: 0;
}

[data-testid="stFileUploader"] section small::before {
    content: "Límite 4GB por archivo • MP4, MOV, AVI, MPEG4";
    font-size: 0.875rem;
}

[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] div div {
    font-size: 0;
}

[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] div div::before {
    content: "Arrastra y suelta el archivo aquí";
    font-size: 1rem;
}

[data-testid="stFileUploader"] button[kind="secondary"] {
    font-size: 0;
}

[data-testid="stFileUploader"] button[kind="secondary"]::before {
    content: "Examinar archivos";
    font-size: 0.875rem;
}
</style>
""", unsafe_allow_html=True)

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

run_page_splash(
    "page_ingesta",
    [
        "Inicializando módulo de ingesta...",
        "Verificando almacenamiento local...",
        "Habilitando captura experimental...",
    ],
    subtitle="Preparando ingesta de vídeo...",
)

# ================= SIDEBAR =================
with st.sidebar:
    # Perfil usuario al tope
    st.markdown(f"""
<div style="display:flex; align-items:center; gap: 10px; margin-bottom: 12px; margin-top: 10px;">
    <div style="width: 36px; height: 36px; border-radius: 50%; background: {colors['primary_dark']}; display:flex; align-items:center; justify-content:center; font-weight: 700; font-size: 1rem; border: 1px solid rgba(255,255,255,0.2);">
        {st.session_state.get('user_name', 'U')[0].upper()}
    </div>
    <div style="overflow: hidden;">
        <div style="font-weight: 600; font-size: 0.85rem; white-space: nowrap; text-overflow: ellipsis;">{st.session_state.get('user_name')}</div>
        <div style="font-size: 0.7rem; opacity: 0.7; white-space: nowrap; text-overflow: ellipsis; letter-spacing: 0.2px;">{st.session_state.get('user', '')}</div>
    </div>
</div>
""", unsafe_allow_html=True)
    if st.button("Cerrar sesión", key="logout_btn", use_container_width=True):
        from session_utils import clear_session
        clear_session()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Sidebar con navegación
    inject_sidebar_profile(show_admin_button=True)


def format_mm_ss(total_seconds):
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def set_trim_widget_values(start_seconds, end_seconds):
    st.session_state["trim_start_min"] = max(0, int(start_seconds)) // 60
    st.session_state["trim_start_sec"] = max(0, int(start_seconds)) % 60
    st.session_state["trim_end_min"] = max(0, int(end_seconds)) // 60
    st.session_state["trim_end_sec"] = max(0, int(end_seconds)) % 60


@st.cache_data(show_spinner=False)
def get_video_metadata(video_path, modified_time):
    import cv2

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("No se pudo abrir el video para calcular su duración.")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    capture.release()

    if fps <= 0 or frame_count <= 0:
        raise RuntimeError("No se pudo obtener la duración del video.")

    duration_seconds = int(round(frame_count / fps))
    return {
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": max(duration_seconds, 1),
    }


def reset_trim_context():
    for session_key in [
        "ruta_video_actual",
        "inicio_recorte",
        "fin_recorte",
        "pipeline_dlc_activo",
        "zonas_configuradas",
        "_zones_cache",
        "_zones_cache__splash_signature",
        "trim_start_min",
        "trim_start_sec",
        "trim_end_min",
        "trim_end_sec",
        "_trim_video_source",
        "ultimo_video_analizado",
        "ultimo_pose_file",
        "ultimo_pose_filtrado",
        "ultimo_overlay_path",
        "ultimo_bbox_video",
        "ultimo_feature_file",
        "ultimo_multimodal_video",
        "ultimo_trajectory_file",
        "ultimo_grooming_timelog",
        "ultimo_thigmotaxis_timelog",
        "analysis_db_notice",
        "analysis_last_logs",
        "analysis_last_status",
        "analysis_last_progress",
        "keypoints_last_logs",
        "keypoints_last_status",
        "keypoints_last_progress",
    ]:
        st.session_state.pop(session_key, None)


def stage_video_for_edit(video_file, rat_id, treatment, experiment_date, responsible_name):
    extension = os.path.splitext(video_file.name)[1].lower() or ".mp4"
    clean_name = f"{rat_id}_{treatment}{extension}".replace(" ", "_")
    save_path = os.path.join(CARPETA_VIDEOS, clean_name)

    with open(save_path, "wb") as file_handle:
        file_handle.write(video_file.getbuffer())

    st.session_state["video_en_edicion"] = save_path
    st.session_state["id_raton_actual"] = rat_id
    st.session_state["treatment"] = treatment
    st.session_state["ingesta_fecha_actual"] = str(experiment_date)
    st.session_state["ingesta_responsable_actual"] = responsible_name
    st.session_state["ingesta_video_source"] = clean_name
    reset_trim_context()
    save_session()
    return clean_name


# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Módulo 01: Ingesta de video")
st.markdown(
    """
    Cargue el registro experimental en formato de video para iniciar el proceso de análisis conductual.
    Defina los parámetros básicos del espécimen y el tratamiento administrado.
    """
)

st.divider()

# ================= 3. CARPETA DE VIDEOS =================
CARPETA_VIDEOS = "videos_data"
if not os.path.exists(CARPETA_VIDEOS):
    os.makedirs(CARPETA_VIDEOS)

# ================= 3.1 INICIALIZAR TRATAMIENTOS =================
if "treatments_initialized" not in st.session_state:
    initialize_treatments_table()
    st.session_state.treatments_initialized = True

# Obtener rol del usuario
user_role = st.session_state.get("role", "estudiante")

# ================= 4. FORMULARIO DE CARGA =================
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("#### Parámetros del registro")
c1, c2 = st.columns(2)
with c1:
    id_raton = st.text_input(
        "ID del espécimen",
        placeholder="Ej. MOUSE-001",
        key="ingesta_id_raton",
    ).strip()
    
    # ===== SISTEMA DE TRATAMIENTOS CON ROLES =====
    # Obtener lista de tratamientos disponibles
    treatments_list = get_all_treatments()
    treatment_names = [t["name"] for t in treatments_list]
    
    if not treatment_names:
        treatment_names = ["Control"]  # Fallback si no hay tratamientos
    
    # Selectbox de tratamientos (todos los roles)
    tratamiento_seleccionado = st.selectbox(
        "ID del tratamiento",
        options=treatment_names,
        index=0,
        key="ingesta_tratamiento_select",
        help="Selecciona el tratamiento aplicado al espécimen"
    )
    
    # UI adicional según el rol
    if user_role in ["investigador", "admin"]:
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        
        # Expander para añadir nuevo tratamiento
        with st.expander("Añadir nuevo tratamiento"):
            nuevo_tratamiento = st.text_input(
                "Nombre del tratamiento",
                placeholder="Ej. Midazolam 2mg",
                key="nuevo_tratamiento_input"
            )
            descripcion_tratamiento = st.text_area(
                "Descripción (opcional)",
                placeholder="Detalles del tratamiento...",
                key="nueva_descripcion_input",
                height=80
            )
            
            if st.button("Añadir tratamiento", key="btn_add_treatment", type="primary", use_container_width=True):
                if nuevo_tratamiento.strip():
                    success, msg = add_treatment(
                        name=nuevo_tratamiento.strip(),
                        description=descripcion_tratamiento.strip(),
                        created_by=st.session_state.get("user_id")
                    )
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Ingresa un nombre válido para el tratamiento.")
    
    # Solo admin puede eliminar tratamientos
    if user_role == "admin":
        with st.expander("Gestionar tratamientos"):
            tratamiento_a_eliminar = st.selectbox(
                "Selecciona tratamiento a eliminar.",
                options=treatment_names,
                key="tratamiento_eliminar_select"
            )
            
            col_warn, col_del = st.columns([2, 1])
            with col_warn:
                st.caption("Esta acción desactivará el tratamiento si está en uso.")
            with col_del:
                if st.button("Eliminar", key="btn_delete_treatment", type="secondary", use_container_width=True):
                    # Obtener ID del tratamiento
                    treatment_to_delete = next((t for t in treatments_list if t["name"] == tratamiento_a_eliminar), None)
                    if treatment_to_delete:
                        success, msg = delete_treatment(treatment_to_delete["id"])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    
    # Variable final para usar en el procesamiento
    tratamiento_input = tratamiento_seleccionado
    
with c2:
    fecha_exp = st.date_input("Fecha del experimento", key="ingesta_fecha")
    responsable = st.text_input(
        "Responsable",
        value=st.session_state.get("user_name", "Investigador"),
        key="ingesta_responsable",
    ).strip()

video_file = st.file_uploader(
    "Cargar video (MP4 / MOV / AVI)",
    type=["mp4", "mov", "avi"],
    key="ingesta_video_file",
)

st.markdown("---")
button_cols = st.columns([1, 2])
with button_cols[0]:
    preparar_video = st.button("Preparar video y recortar", type="primary", use_container_width=True)
with button_cols[1]:
    if video_file is not None:
        st.caption("Después de preparar el video podrás definir el minuto y segundo exactos a analizar.")
st.markdown("</div>", unsafe_allow_html=True)

# ================= 5. PROCESAMIENTO INICIAL =================
if preparar_video:
    if video_file is None:
        st.error("Carga un vídeo antes de preparar el recorte.")
    elif not id_raton:
        st.error("Ingrese un ID válido para el espécimen.")
    else:
        tratamiento = tratamiento_input or "Control"
        nombre_guardado = stage_video_for_edit(
            video_file=video_file,
            rat_id=id_raton,
            treatment=tratamiento,
            experiment_date=fecha_exp,
            responsible_name=responsable or st.session_state.get("user_name", "Investigador"),
        )
        st.success(f"Video cargado para edición como: `{nombre_guardado}`.")
        st.rerun()

# ================= 6. RECORTE DE VIDEO =================
if "video_en_edicion" in st.session_state:
    ruta_actual = st.session_state["video_en_edicion"]
    if os.path.exists(ruta_actual):
        st.markdown('<div class="content-card" style="border-top: 4px solid #6F1D46;">', unsafe_allow_html=True)
        st.markdown(f"#### Edición de registro: `{os.path.basename(ruta_actual)}`")
        st.info("Selecciona el tramo exacto a analizar. Por ejemplo, de `00:00` a `05:00` aunque el video dure `05:11`.")

        try:
            metadata = get_video_metadata(ruta_actual, os.path.getmtime(ruta_actual))
            duration_seconds = metadata["duration_seconds"]
            max_minute = max(0, duration_seconds // 60)

            if st.session_state.get("_trim_video_source") != ruta_actual:
                default_start = 0
                default_end = duration_seconds
                if st.session_state.get("ruta_video_actual") == ruta_actual:
                    default_start = int(st.session_state.get("inicio_recorte", 0) or 0)
                    default_end = int(st.session_state.get("fin_recorte", duration_seconds) or duration_seconds)
                default_end = min(max(default_end, 1), duration_seconds)
                set_trim_widget_values(default_start, default_end)
                st.session_state["_trim_video_source"] = ruta_actual

            st.markdown(
                f"**Duración detectada:** `{format_mm_ss(duration_seconds)}`  \n"
                f"**Archivo listo para análisis:** `{os.path.basename(ruta_actual)}`"
            )

            quick_cols = st.columns(3)
            with quick_cols[0]:
                if st.button("Usar vídeo completo", use_container_width=True, key="trim_full_video"):
                    set_trim_widget_values(0, duration_seconds)
                    st.rerun()
            with quick_cols[1]:
                if st.button(
                    "Recortar a 05:00",
                    use_container_width=True,
                    key="trim_first_5min",
                    disabled=duration_seconds < 300,
                ):
                    set_trim_widget_values(0, 300)
                    st.rerun()
            with quick_cols[2]:
                st.caption("La previsualización empieza desde el punto inicial que selecciones.")

            trim_cols = st.columns(2)
            with trim_cols[0]:
                st.markdown("##### Inicio de interés")
                start_min = st.number_input(
                    "Minuto inicial",
                    min_value=0,
                    max_value=max_minute,
                    step=1,
                    key="trim_start_min",
                )
                start_sec = st.number_input(
                    "Segundo inicial",
                    min_value=0,
                    max_value=59,
                    step=1,
                    key="trim_start_sec",
                )

            with trim_cols[1]:
                st.markdown("##### Fin de interés")
                end_min = st.number_input(
                    "Minuto final",
                    min_value=0,
                    max_value=max_minute,
                    step=1,
                    key="trim_end_min",
                )
                end_sec = st.number_input(
                    "Segundo final",
                    min_value=0,
                    max_value=59,
                    step=1,
                    key="trim_end_sec",
                )

            start_seconds = int(start_min) * 60 + int(start_sec)
            end_seconds = int(end_min) * 60 + int(end_sec)
            valid_range = 0 <= start_seconds < end_seconds <= duration_seconds

            summary_col, preview_col = st.columns([1.05, 1.45])
            with summary_col:
                if valid_range:
                    st.success(
                        f"Se analizará de `{format_mm_ss(start_seconds)}` a `{format_mm_ss(end_seconds)}` "
                        f"({format_mm_ss(end_seconds - start_seconds)} efectivos)."
                    )
                else:
                    st.error("El rango no es válido. El inicio debe ser menor que el fin y ambos deben quedar dentro de la duración total.")

                active_start = st.session_state.get("inicio_recorte")
                active_end = st.session_state.get("fin_recorte")
                if st.session_state.get("ruta_video_actual") == ruta_actual and active_start is not None and active_end is not None:
                    st.caption(
                        f"Recorte activo actual: {format_mm_ss(active_start)} -> {format_mm_ss(active_end)}"
                    )

            with preview_col:
                preview_start = min(start_seconds, max(duration_seconds - 1, 0))
                st.video(ruta_actual, start_time=preview_start)

            action_cols = st.columns(2)
            with action_cols[0]:
                guardar_recorte = st.button(
                    "Guardar recorte y activar",
                    type="primary",
                    use_container_width=True,
                    disabled=not valid_range,
                    key="guardar_recorte_ingesta",
                )
            with action_cols[1]:
                guardar_y_keypoints = st.button(
                    "Guardar y pasar a keypoints",
                    use_container_width=True,
                    disabled=not valid_range,
                    key="guardar_recorte_keypoints",
                )

            if guardar_recorte or guardar_y_keypoints:
                st.session_state["ruta_video_actual"] = ruta_actual
                st.session_state["inicio_recorte"] = start_seconds
                st.session_state["fin_recorte"] = end_seconds
                save_session()
                if guardar_y_keypoints:
                    st.switch_page("pages/02_Keypoints.py")
                else:
                    st.success("Parámetros de recorte guardados. Ya puedes continuar con Keypoints o Configuración de zonas.")
        except Exception as error:
            st.warning(f"Error al preparar el editor de recorte: {error}")
        st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align: center; color: {colors['text_sub']}; font-size: 0.8rem;">
        IPN - Unidad de Investigación de Comportamiento Animal 2026
    </div>
    """,
    unsafe_allow_html=True,
)
