"""
04_Analisis_Final.py  —  Análisis Conductual (YOLO Tracker + SimBA)
════════════════════════════════════════════════════════════════════════════════
Módulo rápido (~5 min). Requiere:
  ✅ Keypoints extraídos por DLC (Módulo 02)
  ✅ Zonas configuradas (Módulo 03)

Ejecuta:
  1. YOLO Tracker (tracking del centroid de la rata)
  2. SimBA Classifiers (Grooming + Thigmotaxis)
  3. Renderizado del HUD Multimodal sobre el video original
  4. Guardado de métricas en la Base de Datos

Output:
  • videos/<nombre>_STREAMLIT_MULTIMODAL.mp4   ← video con HUD
  • videos/<nombre>_STREAMLIT_MULTIMODAL_trajectory.csv
════════════════════════════════════════════════════════════════════════════════
"""
import streamlit as st
import os
import sys
import subprocess
import time
import glob
import json
import math


def _python_has_module(python_exe: str, module_name: str) -> bool:
    """Verifica si un interprete concreto puede importar un modulo."""
    if not python_exe or not os.path.exists(python_exe):
        return False

    probe_cmd = [
        python_exe,
        "-c",
        (
            "import importlib.util, sys; "
            f"sys.exit(0 if importlib.util.find_spec('{module_name}') else 1)"
        ),
    ]
    try:
        probe = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return probe.returncode == 0
    except Exception:
        return False


def _resolve_runtime_pythons() -> tuple[str | None, str | None]:
    """
    Resuelve interpretes separados para etapas incompatibles:
    - SimBA vive en venv_310
    - Ultralytics vive en venv_311
    """
    candidates: list[str] = []
    for rel_path in (
        os.path.join("venv_310", "Scripts", "python.exe"),
        os.path.join("venv_311", "Scripts", "python.exe"),
    ):
        python_exe = os.path.abspath(rel_path)
        if os.path.exists(python_exe):
            candidates.append(python_exe)

    if sys.executable not in candidates:
        candidates.append(sys.executable)

    simba_python = next((py for py in candidates if _python_has_module(py, "simba")), None)
    yolo_python = next((py for py in candidates if _python_has_module(py, "ultralytics")), None)
    return simba_python, yolo_python


def _resolve_pose_source_csv(
    work_dir: str,
    simba_input_dir: str,
    base_name: str,
    video_name_simba: str,
    fallback_feature_csvs: list[str],
) -> str:
    """
    Prioridad:
    1. CSV convertido del full pipeline (<video>_full_dlc.csv)
    2. CSV DLC crudo en videos_data
    3. CSV aplanado en SimBA input_csv
    4. features_extracted del proyecto previo como fallback de compatibilidad
    """
    candidates = [
        os.path.join(work_dir, f"{video_name_simba}_dlc.csv"),
    ]
    candidates.extend(sorted(glob.glob(os.path.join(work_dir, f"*{base_name}*DLC*.csv"))))
    candidates.append(os.path.join(simba_input_dir, f"{video_name_simba}.csv"))
    candidates.extend(fallback_feature_csvs)

    seen: set[str] = set()
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.isfile(normalized):
            return normalized
    return ""


def _resolve_preferred_simba_model(model_dir: str, candidate_names: list[str]) -> tuple[str, str]:
    for candidate_name in candidate_names:
        candidate_path = os.path.join(model_dir, candidate_name)
        if os.path.exists(candidate_path):
            return candidate_path, candidate_name
    return "", ""

# ── Path setup ────────────────────────────────────────────────────────────────
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Análisis Final (EPM)",
    page_icon="🔬",
    layout="wide",
)

# ── Sesión y login ─────────────────────────────────────────────────────────────
from session_utils import load_session, save_session
load_session()

if not st.session_state.get("logged_in"):
    st.warning("⚠️ Debes iniciar sesión en 🔐 Login primero.")
    st.stop()

from auth import check_admin_access
if check_admin_access(st.session_state.get("role")):
    st.warning("⛔ Los administradores no pueden ejecutar análisis.")
    st.stop()

# ── Tema ───────────────────────────────────────────────────────────────────────
from ui_theme import use_theme
use_theme()

# ── Componentes compartidos ────────────────────────────────────────────────────
from video_context_banner import render_video_banner

# ════════════════════════════════════════════════════════════════════════════════
# CSS LOCAL
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.af-title {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 1.9rem;
    color: var(--text-main);
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}
.af-subtitle {
    font-size: 0.95rem;
    color: var(--text-main);
    opacity: 0.85;
    margin-bottom: 1rem;
}
.af-card {
    background-color: var(--card-bg);
    border-radius: 0.5rem;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 4px 15px var(--shadow);
    border: 1px solid var(--card-border);
    border-top: 3px solid var(--primary);
    margin-bottom: 1.2rem;
    color: var(--text-main);
}
.req-ok   { color: #48bb78; font-weight: 700; }
.req-miss { color: #fc8181; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# CABECERA
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="af-title">🔬 Análisis Final (YOLO + SimBA)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="af-subtitle">Pipeline rápido (~5 min). Utiliza los keypoints de DLC '
    'y las zonas configuradas para clasificar comportamientos y generar el video HUD multimodal.</div>',
    unsafe_allow_html=True,
)

# ── Banner de video activo ─────────────────────────────────────────────────────
video_ok = render_video_banner("Video a analizar (Análisis Final)")

if not video_ok:
    st.error("⚠️ Selecciona un video en **01 · Ingesta de Video** antes de continuar.")
    st.stop()

ruta_video = st.session_state["ruta_video_actual"]
base_name  = os.path.splitext(os.path.basename(ruta_video))[0]

# ════════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE PRE-REQUISITOS
# ════════════════════════════════════════════════════════════════════════════════
WORK_DIR     = os.path.abspath("videos_data")
SIMBA_PROJECT = os.path.abspath(os.path.join(
    "data", "simba_projects", "New folder", "thigmotaxis_optimizado", "project_folder"
))
LEGACY_SIMBA_PROJECT = os.path.abspath(os.path.join(
    "data", "simba_projects", "SimBA_EPM_Analysis", "project_folder"
))
FEATURES_DIR = os.path.join(SIMBA_PROJECT, "csv", "features_extracted")
SIMBA_INPUT_DIR = os.path.join(SIMBA_PROJECT, "csv", "input_csv")
LEGACY_FEATURES_DIR = os.path.join(LEGACY_SIMBA_PROJECT, "csv", "features_extracted")

# VIDEO_NAME en SimBA: full_pipeline.py añade sufijo "_full" al base_name del video
# Ej: ruta_video = 'videos_data/mike_prueba1_Ctrl.mp4' -> base_name = 'mike_prueba1_Ctrl'
#      VIDEO_NAME en full_pipeline = 'mike_prueba1_Ctrl_full'
video_name_simba = f"{base_name}_full"

# 1. ¿Hay keypoints (H5 o CSV de features)?
h5_existentes  = glob.glob(os.path.join(WORK_DIR, f"*{base_name}*DLC*.h5"))
csv_features = glob.glob(os.path.join(FEATURES_DIR, f"{video_name_simba}.csv"))
csv_features.extend(glob.glob(os.path.join(LEGACY_FEATURES_DIR, f"{video_name_simba}.csv")))
source_pose_csv_path = _resolve_pose_source_csv(
    WORK_DIR,
    SIMBA_INPUT_DIR,
    base_name,
    video_name_simba,
    csv_features,
)
tiene_pose_source = bool(source_pose_csv_path)
tiene_keypoints = bool(h5_existentes or tiene_pose_source)
tiene_features  = bool(csv_features)

# 2. ¿Hay zonas configuradas?
zonas = st.session_state.get("zonas_configuradas", [])
tiene_zonas = bool(zonas)

# 3. ¿Modelos SimBA disponibles?
MODEL_VALIDATIONS_DIR = os.path.join(
    "data", "simba_projects", "New folder", "thigmotaxis_optimizado", "models", "validations"
)
MODEL_THIGMO, MODEL_THIGMO_NAME = _resolve_preferred_simba_model(
    MODEL_VALIDATIONS_DIR,
    ["Thigmotaxis_3.sav", "Thigmotaxis_0.sav", "Thigmotaxis_2.sav"],
)
MODEL_GROOMING, MODEL_GROOMING_NAME = _resolve_preferred_simba_model(
    MODEL_VALIDATIONS_DIR,
    ["Grooming_0.sav", "Grooming_1.sav", "Grooming_2.sav"],
)
tiene_modelos = os.path.exists(MODEL_THIGMO) and os.path.exists(MODEL_GROOMING)

with st.expander("📋 Verificación de Prerrequisitos", expanded=not (tiene_features and tiene_zonas)):
    req1, req2, req3 = st.columns(3)
    with req1:
        with st.container(border=True):
            if tiene_pose_source:
                st.markdown('<span class="req-ok">✅ Datos de pose listos</span>', unsafe_allow_html=True)
                st.caption(f"`{os.path.basename(source_pose_csv_path)}`")
            elif tiene_keypoints:
                st.markdown('<span class="req-miss">⚠️ Solo H5 (sin CSV base)</span>', unsafe_allow_html=True)
                st.caption("Falta el CSV plano de pose para SimBA. Completa el pipeline desde **02 · Keypoints**.")
            else:
                st.markdown('<span class="req-miss">❌ Sin Keypoints</span>', unsafe_allow_html=True)
                st.caption("Ve a **02 · Keypoints** para extraer los datos DLC primero.")
    with req2:
        with st.container(border=True):
            if tiene_zonas:
                nombres = [z.get("id", z.get("Nombre Zona", "?")) for z in zonas]
                st.markdown('<span class="req-ok">✅ Zonas Cargadas</span>', unsafe_allow_html=True)
                st.caption(", ".join(nombres[:4]) + ("..." if len(nombres) > 4 else ""))
            else:
                st.markdown('<span class="req-miss">❌ Sin Zonas</span>', unsafe_allow_html=True)
                st.caption("Ve a **03 · Configuración de Zonas** para definir los brazos.")
    with req3:
        with st.container(border=True):
            if tiene_modelos:
                st.markdown('<span class="req-ok">✅ Modelos SimBA</span>', unsafe_allow_html=True)
                st.caption(f"`{MODEL_THIGMO_NAME}` | `{MODEL_GROOMING_NAME}`")
            else:
                st.markdown('<span class="req-miss">❌ Modelos no encontrados</span>', unsafe_allow_html=True)
                st.caption("Revisa la ruta de los `.sav` en el proyecto SimBA.")

# ── Bloquear si no hay fuente CSV utilizable ─────────────────────────────────
if not tiene_pose_source:
    st.error(
        "🔴 **No hay un CSV de pose utilizable para este video.** "
        "Ve a **02 · Keypoints** para extraer o completar el pipeline primero."
    )
    st.stop()

if not tiene_zonas:
    st.warning("⚠️ No hay zonas configuradas. El análisis se ejecutará sin asignación de zona. "
               "Ve a **03 · Configuración de Zonas** para mayor precisión.")

# ════════════════════════════════════════════════════════════════════════════════
# PANEL DE CONFIGURACIÓN Y ACCIÓN
# ════════════════════════════════════════════════════════════════════════════════
features_csv_path = source_pose_csv_path

col_cfg, col_preview = st.columns([1, 2])

with col_cfg:
    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown("#### ⚙️ Configuración del Análisis Final")

    if tiene_pose_source:
        st.success("✅ Datos de pose listos — análisis en ~5 min")
        st.caption(f"Fuente detectada: `{os.path.basename(source_pose_csv_path)}`")
        iniciar_analisis = st.button(
            "⚡ EJECUTAR ANÁLISIS FINAL",
            type="primary",
            use_container_width=True,
        )
    else:
        st.error(
            "🔴 **No hay un CSV base de pose para este video.**\n\n"
            "Completa **02 · Keypoints** hasta generar el CSV DLC/SimBA y luego vuelve aquí."
        )
        iniciar_analisis = False  # Bloquear — no se puede ejecutar sin features

    st.markdown("---")
    st.caption("📦 **Output:** Video Multimodal MP4 + CSV de trayectoria")
    st.caption("🔬 **Clasificadores:** Thigmotaxis RF + Grooming RF (SimBA)")
    st.caption("🎯 **Tracker:** YOLO ByteTrack (centroid y bounding box)")
    st.markdown("</div>", unsafe_allow_html=True)

with col_preview:
    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown("#### 🗺️ Vista Previa de Zonas")

    if zonas and ruta_video:
        import cv2
        try:
            cap = cv2.VideoCapture(ruta_video)
            ret, frame = cap.read()
            cap.release()
            if ret:
                import numpy as np
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                overlay   = frame_rgb.copy()

                for z in zonas:
                    tipo = z.get("type", "rect")
                    name = z.get("id", z.get("Nombre Zona", "Zona"))
                    n_l  = name.lower()
                    if tipo == "line" or "muro" in n_l: continue
                    color = (200,200,200)
                    if "abierto" in n_l: color = (240,120,120)
                    elif "cerrado" in n_l: color = (0,250,255)
                    elif "centro" in n_l: color = (255,165,0)
                    x = int(z.get("x", z.get("left", 0)))
                    y = int(z.get("y", z.get("top", 0)))
                    w = int(z.get("w", z.get("width", 0)))
                    h = int(z.get("h", z.get("height", 0)))
                    cv2.rectangle(overlay, (x,y), (x+w,y+h), color, -1)

                cv2.addWeighted(overlay, 0.35, frame_rgb, 0.65, 0, frame_rgb)

                for z in zonas:
                    tipo = z.get("type", "rect")
                    name = z.get("id", z.get("Nombre Zona", "Zona"))
                    n_l  = name.lower()
                    color = (200,200,200)
                    if "abierto" in n_l: color = (240,120,120)
                    elif "cerrado" in n_l: color = (0,250,255)
                    elif "centro" in n_l: color = (255,165,0)
                    if tipo == "line" or "muro" in n_l:
                        cv2.line(frame_rgb,
                                 (int(z.get("x1",0)), int(z.get("y1",0))),
                                 (int(z.get("x2",0)), int(z.get("y2",0))),
                                 (0,255,255), 3)
                    else:
                        x,y = int(z.get("x",z.get("left",0))), int(z.get("y",z.get("top",0)))
                        w,h = int(z.get("w",z.get("width",0))), int(z.get("h",z.get("height",0)))
                        cv2.rectangle(frame_rgb, (x,y), (x+w,y+h), color, 2)
                        cv2.putText(frame_rgb, name, (x,max(0,y-8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                st.image(frame_rgb, use_container_width=True,
                         caption=f"Vista previa: {len(zonas)} zonas · {base_name}")
        except Exception:
            st.info("No se pudo renderizar la vista previa.")
    else:
        st.info("Define las zonas en **03 · Configuración de Zonas** para ver la vista previa.")

    st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DEL ANÁLISIS FINAL (Re-Análisis Acelerado)
# ════════════════════════════════════════════════════════════════════════════════
if iniciar_analisis:
    # Guardia final antes de lanzar el subproceso
    if not features_csv_path or not os.path.isfile(features_csv_path):
        st.error(
            f"⚠️ **No se puede ejecutar el análisis:** la ruta base de pose es inválida o no existe.\n\n"
            f"`{features_csv_path or '(vacío)'}`\n\n"
            "Ve a **02 · Keypoints** para extraer o regenerar el CSV DLC/SimBA."
        )
        st.stop()

    st.toast("⚡ Iniciando Análisis Final...")
    status_container = st.status(
        "Reconstruyendo video multimodal (~5 min)...", expanded=True
    )

    with status_container:
        st.markdown("#### ⏱️ Progreso Inteligente")
        smart_status = st.info("Inicializando motores...")
        progress_bar = st.progress(0, text="Calculando...")
        estado_actual = "Inicializando..."

    with st.expander("🖥️ Terminal Interna (Logs Técnicos)", expanded=True):
        log_area = st.empty()

    try:
        # Extraer parámetros de recorte de la sesión
        trim_start = st.session_state.get("inicio_recorte", 0)
        trim_end = st.session_state.get("fin_recorte", 0)
        
        video_a_procesar = ruta_video
        
        simba_python, yolo_python = _resolve_runtime_pythons()
        if not simba_python:
            raise RuntimeError(
                "No se encontro un interprete con SimBA. Revisa venv_310 o instala 'simba' en el entorno actual."
            )
        if not yolo_python:
            raise RuntimeError(
                "No se encontro un interprete con ultralytics. Revisa venv_311 o instala 'ultralytics' en el entorno actual."
            )

        log_area.code(f"[ENV] SimBA -> {simba_python}")
        log_area.code(f"[ENV] YOLO  -> {yolo_python}")

        _NO_WINDOW      = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        
        # Recortar video original ANTES de pasarlo a la IA si hay recorte configurado
        if trim_end > 0 and trim_end > trim_start:
            smart_status.info(f"✂️ Recortando video origen ({int(trim_start)}s a {int(trim_end)}s)...")
            trimmed_temp = os.path.join(WORK_DIR, f"{base_name}_temp_trimmed.mp4")
            
            trim_cmd = [
                "ffmpeg", "-y", "-i", ruta_video,
                "-ss", str(trim_start), "-to", str(trim_end),
                "-c:v", "copy", "-c:a", "copy",
                trimmed_temp
            ]
            
            subprocess.run(trim_cmd, creationflags=_NO_WINDOW, check=False)
            
            if os.path.exists(trimmed_temp):
                video_a_procesar = trimmed_temp
                log_area.code(f"[FFMPEG] Video temporal creado: {trimmed_temp}")

        # --- PASO EXTRA: CALCULAR FEATURES SIMBA PARA EL MODELO ---
        smart_status.info("🔬 Calculando 242 características SimBA (Cuerpo, Velocidad, Hull)...")
        log_area.code("[ENGINE] Generando bridge de características...")
        log_area.code(f"[ENGINE] Fuente de pose detectada: {features_csv_path}")
        
        # Ruta de salida para las features enriquecidas
        features_242_path = os.path.abspath(os.path.join(WORK_DIR, f"{base_name}_features_242.csv"))
        project_optimizado = os.path.join("data", "simba_projects", "New folder", "thigmotaxis_optimizado")
        
        # Guardar zonas a un archivo temporal para el bridge
        zonas_json_path = os.path.abspath(os.path.join(WORK_DIR, f"{base_name}_zonas_temp.json"))
        with open(zonas_json_path, "w") as f_z:
            json.dump(zonas, f_z)
            
        feat_script = os.path.abspath(os.path.join("src", "scripts", "compute_simba_features.py"))
        feat_cmd = [
            simba_python, feat_script,
            "--input",   features_csv_path,
            "--output",  features_242_path,
            "--project", os.path.abspath(project_optimizado),
            "--zonas",   zonas_json_path,
            "--video",   ruta_video,
            "--video_name", video_name_simba,
        ]
        
        ret_feat = subprocess.run(
            feat_cmd,
            creationflags=_NO_WINDOW,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        
        if ret_feat.returncode != 0 or not os.path.isfile(features_242_path):
            feat_logs = "\n".join(
                part.strip() for part in (ret_feat.stdout, ret_feat.stderr) if part and part.strip()
            )
            if feat_logs:
                log_area.code(feat_logs[-4000:], language="bash")
            if ret_feat.returncode == 0:
                log_area.code(
                    f"[ENGINE] El extractor terminó sin error, pero no generó el archivo esperado: {features_242_path}",
                    language="bash",
                )
            raise RuntimeError(
                "No se pudieron generar las 242 características de SimBA para este video. "
                "Se canceló el render final para evitar predicciones inválidas."
            )
        else:
            features_csv_path = features_242_path
            log_area.code(f"[ENGINE] Características enriquecidas generadas: {features_242_path}")

        # --- GENERAR VIDEO ---
        smart_status.info("🎥 Renderizando video multimodal con HUD...")
        script_path = os.path.abspath(os.path.join("src", "scripts", "generar_video_prediccion.py"))
        zonas_json_str = json.dumps(zonas)
        output_name    = f"{base_name}_STREAMLIT_MULTIMODAL.mp4"
        output_path    = os.path.abspath(os.path.join("videos", output_name))
        os.makedirs("videos", exist_ok=True)

        cmd = [
            yolo_python, script_path,
            "--video",          video_a_procesar,
            "--features",       features_csv_path,
            "--model_thigmo",   MODEL_THIGMO,
            "--model_grooming", MODEL_GROOMING,
            "--output",         output_path,
            "--zonas_json",     zonas_json_str,
        ]

        _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_NO_WINDOW,
        )
        assert process.stdout is not None

        import re
        logs: list = []
        for line in iter(process.stdout.readline, ""):
            clean = line.strip()
            logs.append(clean)
            log_area.code("\n".join(logs[-12:]), language="bash")

            # Interpretar estado
            if "Parallel" in clean or "Using backend" in clean:
                estado_actual = "📊 Ejecutando Inferencia SimBA..."
                smart_status.info(estado_actual)
            elif "YOLO" in clean or "Fusing" in clean or "model" in clean.lower():
                estado_actual = "👁️ Inicializando Motores IA..."
                smart_status.info(estado_actual)
                progress_bar.progress(0.10, text="Cargando modelos...")
            elif "Renderizados" in clean:
                estado_actual = "🎞️ Renderizando HUD Multimodal..."
                smart_status.info(estado_actual)
                m = re.search(r"Renderizados (\d+)/(\d+)", clean)
                if m:
                    pct = min(1.0, int(m.group(1)) / int(m.group(2)))
                    progress_bar.progress(pct, text=f"Frame {m.group(1)} de {m.group(2)} ({int(pct*100)}%)")

        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            status_container.update(label="✅ Análisis Final completado!", state="complete")
            st.success("🎉 ¡Video Multimodal generado con éxito!")

            # Cargar trayectoria para estadísticas
            traj_path = output_path.replace(".mp4", "_trajectory.csv")
            if os.path.exists(traj_path):
                import pandas as pd
                df_trayectoria = pd.read_csv(traj_path)
                st.session_state["resultados_analisis"] = df_trayectoria
                st.info("📊 Datos enviados a **05 · Resultados y Estadísticas**.")

                # --- Guardar en BD ---
                try:
                    from db.connection import get_db_engine
                    from sqlalchemy import text as sql_text
                    engine = get_db_engine()
                    if engine:
                        with engine.connect() as conn:
                            tratamiento_sesion = st.session_state.get("treatment_id", "Sin tratamiento")
                            q_exp = sql_text("""
                                INSERT INTO experiments (rat_id, treatment, experiment_date, responsible, video_path)
                                VALUES (:rid, :trt, CURRENT_DATE, :resp, :vpath)
                                RETURNING id
                            """)
                            ex_res = conn.execute(q_exp, {
                                "rid":  base_name,
                                "trt":  tratamiento_sesion,
                                "resp": st.session_state.get("user_name", "Investigador"),
                                "vpath": output_path,
                            }).fetchone()

                            if ex_res:
                                new_id = ex_res[0]
                                conn.commit()

                                res_z    = df_trayectoria.groupby("Zona")["Tiempo (s)"].count() * 0.1
                                open_t   = float(res_z.filter(like="Abierto").sum())
                                closed_t = float(res_z.filter(like="Cerrado").sum())
                                center_t = float(res_z.filter(like="Centro").sum())
                                groom_t  = float(df_trayectoria["Grooming"].sum() * 0.1 if "Grooming" in df_trayectoria.columns else 0)
                                thigmo_t = float(df_trayectoria["Thigmotaxis"].sum() * 0.1 if "Thigmotaxis" in df_trayectoria.columns else 0)

                                try:
                                    conn.execute(sql_text("ALTER TABLE analysis_results ADD COLUMN trajectory_path TEXT;"))
                                    conn.commit()
                                except Exception:
                                    conn.rollback()

                                q_an = sql_text("""
                                    INSERT INTO analysis_results
                                    (experiment_id, time_open_arms, time_closed_arms, time_center,
                                     grooming_duration, thigmotaxis_duration, status, trajectory_path)
                                    VALUES (:eid,:to,:tc,:tcen,:tg,:tt,'completed',:tp)
                                """)
                                conn.execute(q_an, {
                                    "eid": new_id, "to": open_t, "tc": closed_t,
                                    "tcen": center_t, "tg": groom_t, "tt": thigmo_t,
                                    "tp": traj_path,
                                })
                                conn.commit()
                                st.toast(f"✅ Guardado en BD (ID: #{new_id})")
                except Exception as db_err:
                    st.warning(f"No se pudo guardar en BD: {db_err}")

            st.video(output_path)
            with open(output_path, "rb") as f:
                st.download_button(
                    "⬇️ Descargar Video Multimodal",
                    data=f,
                    file_name=output_name,
                    mime="video/mp4",
                    type="primary",
                )
        else:
            status_container.update(label="❌ El análisis falló", state="error")
            st.error("El proceso terminó con errores. Revisa los logs.")

    except Exception as e:
        status_container.update(label="❌ Error Crítico", state="error")
        st.error(f"Excepción: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# NAVEGACIÓN SUGERIDA
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("---")
n1, n2 = st.columns(2)
with n1:
    st.info("**02 · Keypoints** — Volver a extraer keypoints desde cero (Prueba de Fuego)")
with n2:
    st.info("**05 · Resultados** — Ver el dashboard completo con etograma y mapas de calor")
