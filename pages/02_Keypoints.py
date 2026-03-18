"""
02_Keypoints.py  —  Módulo de Extracción de Keypoints
════════════════════════════════════════════════════════════════════════════════
Motor de pose estimation. Responsabilidad ÚNICA: extraer los keypoints del
espécimen frame a frame y guardar el resultado como .h5 / .csv.

Motores soportados:
  • DeepLabCut SuperAnimal TopViewMouse  (actual, lento pero muy preciso)
  • YOLO Pose Estimation                 (futuro — botón visible, "próximamente")

Output generado:
  • videos_data/<nombre_video>DLC_*.h5     ← coords crudas
  • videos_data/<nombre_video>DLC_*.csv    ← coords planas (para SimBA)

Al terminar, el usuario puede ir a:
  03 · Configuración de Zonas  →  define ROIs
  04 · Análisis Final           →  YOLO Tracker + SimBA + métricas
════════════════════════════════════════════════════════════════════════════════
"""
import streamlit as st
import os
import sys
import subprocess
import time
import glob

# ── Path setup ───────────────────────────────────────────────────────────────
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

# ── Page config (PRIMERO, antes de cualquier st.*) ───────────────────────────
st.set_page_config(
    page_title="Extracción de Keypoints",
    page_icon="🦴",
    layout="wide",
)

# ── Sesión y login ────────────────────────────────────────────────────────────
from session_utils import load_session, save_session
load_session()

if not st.session_state.get("logged_in"):
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login primero.")
    st.stop()

from auth import check_admin_access
if check_admin_access(st.session_state.get("role")):
    st.warning("⛔ Los administradores no pueden ejecutar análisis.")
    st.stop()

# ── Tema ─────────────────────────────────────────────────────────────────────
from ui_theme import use_theme
use_theme()

# ── Banner y componente de video ──────────────────────────────────────────────
from video_context_banner import render_video_banner, render_video_banner_mini

# ════════════════════════════════════════════════════════════════════════════════
# CSS local del módulo
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.kp-title {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 1.9rem;
    color: var(--text-main);
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}
.kp-subtitle {
    font-size: 0.95rem;
    color: var(--text-main);
    opacity: 0.85;
    margin-bottom: 1rem;
}
.kp-card {
    background-color: var(--card-bg);
    border-radius: 0.5rem;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 4px 15px var(--shadow);
    border: 1px solid var(--card-border);
    border-top: 3px solid var(--primary);
    margin-bottom: 1.2rem;
    color: var(--text-main);
}
.kp-engine-badge {
    display: inline-block;
    padding: 0.25rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-right: 0.5rem;
}
.badge-dlc  { background: rgba(72,187,120,0.18); color: #48bb78; border: 1px solid rgba(72,187,120,0.4); }
.badge-yolo { background: rgba(237,137,54,0.18);  color: #ed8936; border: 1px solid rgba(237,137,54,0.4); }
.badge-soon { background: rgba(160,174,192,0.18); color: #a0aec0; border: 1px solid rgba(160,174,192,0.4); }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# CABECERA
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="kp-title">🦴 Extracción de Keypoints</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="kp-subtitle">Detecta y extrae las coordenadas corporales de la rata '
    'frame por frame. Este paso es el más largo del pipeline (~40 min). '
    'Puedes navegar a otras pestañas sin interrumpir el proceso.</div>',
    unsafe_allow_html=True,
)

# ── Banner de video activo ────────────────────────────────────────────────────
video_ok = render_video_banner("Video a procesar (Keypoints)")

if not video_ok:
    st.error("⚠️ Selecciona un video en **01 · Ingesta de Video** antes de continuar.")
    st.stop()

ruta_video = st.session_state["ruta_video_actual"]

# Guardia extra: la ruta debe ser válida en disco (por si la sesión tiene basura)
if not ruta_video or not os.path.exists(ruta_video):
    st.error(
        f"⚠️ La ruta del video no es válida o ya no existe en disco: `{ruta_video or '(vacío)'}`.\n\n"
        "Ve a **01 · Ingesta de Video** y vuelve a confirmar el recorte."
    )
    st.stop()

base_name  = os.path.splitext(os.path.basename(ruta_video))[0]

# ════════════════════════════════════════════════════════════════════════════════
# ESTADO DEL PIPELINE (¿ya hay keypoints para este video?)
# ════════════════════════════════════════════════════════════════════════════════
WORK_DIR     = os.path.abspath("videos_data")
PIPELINE_LOG  = os.path.abspath("logs/pipeline_dlc.log")
PIPELINE_PID  = os.path.abspath("logs/pipeline_dlc.pid")
PIPELINE_DONE = os.path.abspath("logs/pipeline_dlc.done")

def _pipeline_is_running() -> bool:
    if not os.path.exists(PIPELINE_PID):
        return False
    try:
        pid_text = open(PIPELINE_PID).read().strip()
        if not pid_text: return False
        pid = int(pid_text)
        # En Windows, pulsamos el proceso para ver si responde
        import subprocess
        output = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}"], encoding="utf-8")
        return str(pid) in output
    except Exception:
        return False

def _force_cleanup():
    """Borra todos los archivos de control de forma manual."""
    for f in [PIPELINE_PID, PIPELINE_DONE, PIPELINE_LOG]:
        if os.path.exists(f): 
            try: os.remove(f)
            except: pass
    st.session_state["pipeline_dlc_activo"] = False


def _resolve_dlc_source_video(pose_path: str, fallback_video: str) -> str:
    if not pose_path:
        return fallback_video

    pose_stem = os.path.splitext(os.path.basename(pose_path))[0]
    pose_prefix = pose_stem.split("DLC", 1)[0]
    for extension in (".mp4", ".avi", ".mov"):
        candidate = os.path.join(WORK_DIR, f"{pose_prefix}{extension}")
        if os.path.exists(candidate):
            return candidate
    return fallback_video

def _launch_detached_pipeline(cmd: list) -> int:
    os.makedirs("logs", exist_ok=True)
    for f in [PIPELINE_LOG, PIPELINE_PID, PIPELINE_DONE]:
        if os.path.exists(f): os.remove(f)

    log_file = open(PIPELINE_LOG, "w", encoding="utf-8", buffering=1)
    _DETACHED  = 0x00000008
    _NEW_PG    = 0x00000200
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        close_fds=True,
        creationflags=_DETACHED | _NEW_PG | _NO_WINDOW,
    )
    with open(PIPELINE_PID, "w") as f:
        f.write(str(proc.pid))
    return proc.pid

# ── Detección de keypoints existentes ────────────────────────────────────────
os.makedirs(WORK_DIR, exist_ok=True)
h5_existentes  = glob.glob(os.path.join(WORK_DIR, f"*{base_name}*DLC*.h5"))
csv_existentes = glob.glob(os.path.join(WORK_DIR, f"*{base_name}*DLC*.csv"))
tiene_keypoints = bool(h5_existentes or csv_existentes)
pose_render_source = h5_existentes[0] if h5_existentes else (csv_existentes[0] if csv_existentes else "")
dlc_video_source = _resolve_dlc_source_video(pose_render_source, ruta_video)
dlc_overlay_output = os.path.splitext(dlc_video_source)[0] + "_dlc_overlay.mp4"
tiene_dlc_overlay = os.path.exists(dlc_overlay_output)

# ── Detección de features SimBA (paso posterior al H5) ───────────────────────
# full_pipeline añade sufijo "_full" al base_name del video
SIMBA_PROJECT  = os.path.abspath(os.path.join(
    "data", "simba_projects", "New folder", "thigmotaxis_optimizado", "project_folder"
))
FEATURES_DIR   = os.path.join(SIMBA_PROJECT, "csv", "features_extracted")
video_name_simba = f"{base_name}_full"
features_csv   = glob.glob(os.path.join(FEATURES_DIR, f"{video_name_simba}.csv"))
tiene_features = bool(features_csv)

# ════════════════════════════════════════════════════════════════════════════════
# LAYOUT: Selección de motor + Estado
# ════════════════════════════════════════════════════════════════════════════════
col_cfg, col_status = st.columns([1, 2])

with col_cfg:
    st.markdown('<div class="kp-card">', unsafe_allow_html=True)
    st.markdown("#### 🔬 Motor de Análisis de Pose")

    motor_kp = st.radio(
        "Selecciona el motor",
        [
            "🧬 DeepLabCut SuperAnimal (Activo)",
            "⚡ YOLO Pose Estimation (Próximamente)",
        ],
        index=0,
        help="DeepLabCut extrae 27 keypoints usando el modelo SuperAnimal TopViewMouse."
    )

    st.markdown("---")

    if "DeepLabCut" in motor_kp:
        st.markdown(
            '<span class="kp-engine-badge badge-dlc">DLC v2.3+</span>'
            '<span class="kp-engine-badge badge-dlc">GPU</span>',
            unsafe_allow_html=True,
        )
        st.caption("⏱ Tiempo estimado: **25–50 min** por video de 5 min en RTX 5070 Ti")
        st.caption("📦 Output: `.h5` + `.csv` de 27 keypoints por frame")
        st.caption("🧠 Modelo: `superanimal_topviewmouse`")

        # Opciones avanzadas
        with st.expander("⚙️ Opciones Avanzadas"):
            # Mapeo de Batch Size a consumo de VRAM estimado
            vram_info = {
                8:  "~4GB VRAM (Seguro / GPUs antiguas)",
                16: "~6GB VRAM (Recomendado para RTX 3060/4060)",
                32: "~9GB VRAM (Máximo recomendado para 12GB VRAM)"
            }

            batch_size = st.select_slider(
                "Batch Size (frames/pasada)",
                options=[8, 16, 32],
                value=32,
                help="Mayor batch size = más velocidad, pero requiere más memoria de video (VRAM)."
            )
            st.caption(f"💡 **Consumo estimado:** {vram_info[batch_size]}")

            skip_video_adapt = st.toggle(
                "Saltar Video Adaptation",
                value=True,
                help="Desactivar acelera 2x pero puede reducir precisión en videos con iluminación muy irregular."
            )
            
            device_opt = st.selectbox(
                "Dispositivo de Procesamiento",
                ["GPU (RTX 5070 Ti) - Máxima Velocidad", "CPU (Solo RAM) - ⚠️ Muy Lento"],
                index=0,
            )
            
            if "CPU" in device_opt:
                st.warning("⚠️ **Alerta:** En CPU el análisis tomará HORAS o DÍAS en lugar de minutos. Solo úsalo si tu GPU no es compatible.")
                st.session_state["dlc_device_opt"] = "CPU"
            else:
                st.session_state["dlc_device_opt"] = "GPU"

    else:  # YOLO Pose
        st.markdown(
            '<span class="kp-engine-badge badge-soon">PRÓXIMAMENTE</span>',
            unsafe_allow_html=True,
        )
        st.info("🔜 YOLO Pose reducirá el tiempo de extracción a **< 5 minutos** por video. "
                "Actualmente en fase de entrenamiento personalizado con datos de ratas.")
        st.stop()

    st.markdown("</div>", unsafe_allow_html=True)

# ── Columna de estado y acciones ─────────────────────────────────────────────
with col_status:
    st.markdown('<div class="kp-card">', unsafe_allow_html=True)

    if tiene_keypoints:
        st.success("✅ **Keypoints detectados para este video**")
        if h5_existentes:
            st.caption(f"📄 H5: `{os.path.basename(h5_existentes[0])}`")
        if csv_existentes:
            st.caption(f"📄 CSV DLC: `{os.path.basename(csv_existentes[0])}`")

        st.markdown("---")
        st.markdown("#### 🎬 Inspección Visual DLC")
        st.caption(
            "Renderiza un MP4 con el overlay de puntos y esqueleto sobre el video "
            f"realmente analizado por DLC: `{os.path.basename(dlc_video_source)}`."
        )

        render_cols = st.columns([1, 1])
        with render_cols[0]:
            if st.button(
                "🎥 Renderizar video con keypoints DLC",
                use_container_width=True,
                disabled=_pipeline_is_running(),
                help="Genera un MP4 de inspección visual usando el H5/CSV actual.",
            ):
                renderer_script = os.path.abspath(os.path.join("src", "scripts", "render_dlc_keypoints_video.py"))
                venv_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))
                render_cmd = [
                    venv_python,
                    renderer_script,
                    "--video", dlc_video_source,
                    "--pose", pose_render_source,
                    "--output", dlc_overlay_output,
                ]

                with st.spinner("Renderizando overlay DLC..."):
                    render_run = subprocess.run(
                        render_cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )

                if render_run.returncode == 0 and os.path.exists(dlc_overlay_output):
                    st.success("✅ Video de keypoints DLC generado correctamente.")
                    st.rerun()
                else:
                    render_log = (render_run.stdout or "") + "\n" + (render_run.stderr or "")
                    st.error("❌ No se pudo generar el video con keypoints DLC.")
                    if render_log.strip():
                        with st.expander("Ver log del renderer DLC"):
                            st.code(render_log[-4000:], language="bash")

        with render_cols[1]:
            if tiene_dlc_overlay:
                st.success("✅ Overlay DLC disponible")
                st.caption(f"📄 `{os.path.basename(dlc_overlay_output)}`")
            else:
                st.info("Aún no se ha generado el overlay visual de DLC para este video.")

        if tiene_dlc_overlay:
            st.video(dlc_overlay_output)

        st.markdown("---")

        # ── Sub-estado: ¿Ya hay features SimBA? ─────────────────────
        if tiene_features:
            st.success("✅ **Features SimBA listas** — puedes proceder al Análisis Final")
            st.caption(f"📄 Features: `{os.path.basename(features_csv[0])}`")
            st.markdown(
                "> ➡️ Ahora ve a **04 · Análisis Final** para generar el video multimodal.",
                unsafe_allow_html=False,
            )
        else:
            st.warning(
                "⚡ **H5 de keypoints listo, pero faltan las features de SimBA.**\n\n"
                "Este paso toma aproximadamente **5 min** y produce el archivo necesario "
                "para que **04 · Análisis Final** pueda clasificar comportamientos."
            )

            completar_pipeline = st.button(
                "▶️ COMPLETAR PIPELINE SIMBA (Pasos 4–6, ~5 min)",
                type="primary",
                use_container_width=True,
                disabled=_pipeline_is_running(),
                help="Ejecuta import → feature extraction → inference. NO re-corre DLC (H5 ya existe).",
            )

            if completar_pipeline:
                script_path = os.path.abspath(os.path.join("src", "scripts", "full_pipeline.py"))
                venv_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))

                if not os.path.exists(venv_python):
                    st.error("❌ No se encontró `venv_310`. Verifica que el entorno DLC esté instalado.")
                    st.stop()

                # full_pipeline.py auto-salta los pasos ya hechos (DLC, Convert H5, etc.)
                # Solo correrá los pasos que falten (4: Import, 5: Features, 6: Inference)
                cmd = [
                    venv_python, script_path,
                    "--video", ruta_video,
                ]
                
                # Pasar trims si los hay
                trim_inicio = st.session_state.get("inicio_recorte", 0.0)
                trim_fin    = st.session_state.get("fin_recorte", 0.0)
                if trim_fin > 0 and trim_fin > trim_inicio:
                    cmd.extend(["--trim_start", str(trim_inicio), "--trim_end", str(trim_fin)])
                    
                pid = _launch_detached_pipeline(cmd)
                st.session_state["pipeline_dlc_activo"] = True
                st.toast(f"🚀 Pipeline SimBA iniciado (PID {pid}) — los pasos DLC se saltarán automáticamente")
                st.rerun()

        with st.expander("🔁 Re-extraer desde cero (borra el H5 existente)"):
            st.warning("⚠️ Esto eliminará el H5 actual y relanzará DLC desde el frame 0. "
                       "Úsalo para la **Prueba de Fuego** del Dr. Sandino.")
            if st.button("🗑️ Borrar Keypoints y Re-analizar", type="secondary"):
                for f in h5_existentes + csv_existentes:
                    os.remove(f)
                if os.path.exists(PIPELINE_DONE): os.remove(PIPELINE_DONE)
                st.session_state["pipeline_dlc_activo"] = False
                st.rerun()
    else:
        st.warning("⏳ **No hay keypoints para este video.**")
        st.write("El análisis DLC procesará el video frame a frame y generará los archivos de coordenadas corporales.")

        iniciar_keypoints = st.button(
            "▶️ INICIAR EXTRACCIÓN DE KEYPOINTS",
            type="primary",
            use_container_width=True,
            disabled=_pipeline_is_running(),
        )

        if iniciar_keypoints:
            script_path = os.path.abspath(os.path.join("src", "scripts", "full_pipeline.py"))
            venv_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))

            if not os.path.exists(venv_python):
                st.error("❌ No se encontró `venv_310`. Verifica que el entorno DLC esté instalado.")
                st.stop()

            cmd = [
                venv_python, script_path,
                "--video",     ruta_video,
                "--batchsize", str(batch_size),  # desde el slider de la UI
            ]
            
            # Pasar trims para que full_pipeline prepare el clip de trabajo
            trim_inicio = st.session_state.get("inicio_recorte", 0.0)
            trim_fin    = st.session_state.get("fin_recorte", 0.0)
            if trim_fin > 0 and trim_fin > trim_inicio:
                cmd.extend(["--trim_start", str(trim_inicio), "--trim_end", str(trim_fin)])
                
            if not skip_video_adapt:
                # El flag --video_adapt activa la adaptación (por defecto está OFF = más rápido)
                cmd.append("--video_adapt")

            pid = _launch_detached_pipeline(cmd)
            st.session_state["pipeline_dlc_activo"] = True
            st.toast(f"🚀 Extracción iniciada (PID {pid}) · batchsize={batch_size} · video_adapt={not skip_video_adapt}")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# PANEL DE MONITOREO (si el pipeline está corriendo o terminó recientemente)
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.get("pipeline_dlc_activo") or _pipeline_is_running() or os.path.exists(PIPELINE_DONE):

    corriendo = _pipeline_is_running()
    terminado = os.path.exists(PIPELINE_DONE) and not corriendo

    if corriendo:
        st.session_state["pipeline_dlc_activo"] = True
        st.info(f"🔄 **DLC corriendo en segundo plano** para `{base_name}` — puedes navegar libremente")
    elif terminado:
        st.session_state["pipeline_dlc_activo"] = False
        status_code = open(PIPELINE_DONE).read().strip()
        
        # 🟢 CAMBIO: Si existen keypoints, el mensaje es verde por defecto
        if tiene_keypoints:
            st.success("✅ **Keypoints extraídos correctamente.**")
            st.info("Ya puedes proceder a la **Configuración de Zonas** y posteriormente al análisis de **YOLO + SimBA**.")
            
            if status_code != "0":
                with st.expander("ℹ️ Detalle de finalización (Error menor detectado)"):
                    st.warning("El pipeline principal terminó los keypoints pero tuvo un detalle al cerrar los logs de SimBA. No afecta tu análisis.")
                    if os.path.exists(PIPELINE_LOG):
                        try:
                            with open(PIPELINE_LOG, "r", encoding="utf-8", errors="replace") as f:
                                last_line = f.readlines()[-1]
                                st.code(last_line, language="bash")
                        except: pass
        
        elif status_code == "0":
            # Caso ideal (todo en orden)
            st.success("✅ **Keypoints extraídos.** Procede a la configuración de zonas y posteriormente al análisis de YOLO + SimBA.")
        
        else:
            # Caso de falla real (sin keypoints)
            st.error("❌ **Error en la extracción:** No se pudieron generar los keypoints.")
            if os.path.exists(PIPELINE_LOG):
                with st.expander("🔍 Ver detalle del error técnico"):
                    try:
                        lineas = open(PIPELINE_LOG, encoding="utf-8", errors="replace").readlines()
                        st.code("".join(lineas[-20:]), language="bash")
                    except: st.write("No se pudo leer el log.")

    with st.expander("📋 Terminal DLC (Log en Vivo)", expanded=corriendo):
        if os.path.exists(PIPELINE_LOG):
            try:
                lineas = open(PIPELINE_LOG, encoding="utf-8", errors="replace").readlines()
                st.code("".join(lineas[-35:]), language="bash")
            except Exception:
                st.warning("Leyendo log...")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if corriendo and st.button("🔁 Refrescar Log", use_container_width=True):
            st.rerun()
    with col_m2:
        if corriendo:
            if st.button("⛔ Cancelar Extracción", use_container_width=True, type="secondary"):
                try:
                    pid = int(open(PIPELINE_PID).read().strip())
                    import subprocess
                    # Usar taskkill /F /T para matar todo el árbol de procesos en Windows
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                    _force_cleanup()
                    st.toast("Proceso detenido y archivos de control limpiados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al cancelar: {e}. Prueba 'Limpiar Estado Manual'.")
        else:
            # Si no está corriendo pero hay basura en los logs, permitir limpiar
            if st.button("🧹 Limpiar Estado Manual", use_container_width=True, help="Usa esto si el botón de cancelar falla o el log se quedó trabado"):
                _force_cleanup()
                st.success("Estado limpiado correctamente.")
                st.rerun()

    if corriendo:
        time.sleep(5)
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# NAVEGACIÓN SUGERIDA
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### ¿Qué sigue?")
n1, n2, n3 = st.columns(3)
with n1:
    st.info("**03 · Configuración de Zonas**\nDefine los brazos, centro y paredes del laberinto. Puedes hacerlo mientras DLC corre.")
with n2:
    st.info("**04 · Análisis Final**\nCuando DLC termine, ven aquí para correr YOLO Tracker + SimBA y obtener las métricas conductuales.")
with n3:
    st.info("**05 · Resultados**\nVisualiza el dashboard completo con etograma, heatmap y estadísticas.")
