import glob
import json
import os
import re
import subprocess
import sys
import time

import streamlit as st

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session, save_session
from ui_components import run_page_splash
import importlib
import ui_theme

importlib.reload(ui_theme)
from ui_theme import render_topbar, use_theme
from video_context_banner import render_video_banner

st.set_page_config(page_title="Keypoints | IPN", page_icon="assets/logos/logo_ria.png", layout="wide")

load_session()
colors = use_theme()

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.warning("Debes iniciar sesion antes de usar el sistema.")
    st.stop()

run_page_splash(
    "page_keypoints",
    [
        "Inicializando motor de keypoints...",
        "Validando contexto de video...",
        "Preparando panel de inferencia...",
    ],
    subtitle="TT 2026 - Cargando extraccion de keypoints...",
)


def format_mm_ss(total_seconds):
    total_seconds = max(0, int(total_seconds or 0))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def get_trim_summary():
    start_seconds = int(st.session_state.get("inicio_recorte", 0) or 0)
    end_seconds = st.session_state.get("fin_recorte")
    if end_seconds is None:
        return f"{format_mm_ss(start_seconds)} -> fin del video"
    return f"{format_mm_ss(start_seconds)} -> {format_mm_ss(end_seconds)}"


def ensure_logs_dir():
    log_dir = os.path.join("logs", "keypoints")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_extract_log_path():
    return os.path.abspath(os.path.join(ensure_logs_dir(), "keypoints_extract.log"))


def get_render_log_path():
    return os.path.abspath(os.path.join(ensure_logs_dir(), "keypoints_overlay.log"))


def get_extract_process_state_path():
    return os.path.abspath(os.path.join(ensure_logs_dir(), "keypoints_extract.process.json"))


def read_log_lines(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as file_handle:
        return [line.rstrip() for line in file_handle.readlines()]


def trim_log_text(lines, max_lines=120):
    if not lines:
        return "[INFO] Aun no hay logs de ejecucion."
    return "\n".join(lines[-max_lines:])


def collect_output_markers(lines):
    outputs = {}
    for line in lines:
        if not line.startswith("[OUTPUT] "):
            continue
        payload = line[len("[OUTPUT] ") :]
        if "=" not in payload:
            continue
        key, value = payload.split("=", 1)
        outputs[key.strip().lower()] = value.strip()
    return outputs


def path_if_exists(candidate):
    if candidate and os.path.exists(candidate):
        return os.path.abspath(candidate)
    return None


def append_log_line(log_path, message):
    with open(log_path, "a", encoding="utf-8") as file_handle:
        file_handle.write(message.rstrip() + "\n")


def load_process_meta():
    state_path = get_extract_process_state_path()
    if not os.path.exists(state_path):
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        return None


def save_process_meta(meta):
    state_path = get_extract_process_state_path()
    with open(state_path, "w", encoding="utf-8") as file_handle:
        json.dump(meta, file_handle, indent=2, ensure_ascii=False)


def is_pid_alive(pid):
    try:
        pid = int(pid)
    except Exception:
        return False

    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return False
    return str(pid) in (result.stdout or "")


def infer_extract_outcome(lines):
    for line in reversed(lines):
        if "[STEP] COMPLETE" in line:
            return "completed"
        if "[STEP] CANCELLED" in line:
            return "cancelled"
        if "[STEP] ERROR" in line or line.startswith("[ERROR]"):
            return "error"
    return "stopped"


def parse_extract_progress(lines, current_progress):
    progress = max(current_progress, 0.02)
    status = "Preparando extraccion y postproceso..."

    is_yolo = any("[STEP] YOLO_POSE" in line for line in lines)

    for line in lines:
        if "[STEP] YOLO_POSE" in line:
            progress = max(progress, 0.08)
            status = "Extrayendo keypoints con YOLO Pose..."
        elif "[STEP] DLC" in line:
            progress = max(progress, 0.05)
            status = "Preparando entorno DLC..."
        elif "[STEP] BOOT" in line:
            progress = max(progress, 0.08)
            status = "Preparando entorno DLC..." if not is_yolo else "Iniciando pipeline YOLO Pose..."
        elif "[STEP] TRIM" in line:
            progress = max(progress, 0.12)
            status = "Aplicando recorte seleccionado..."
        elif "[STEP] IMPORT_DLC" in line:
            progress = max(progress, 0.18)
            status = "Cargando DeepLabCut y TensorFlow..."
        elif "[STEP] INFERENCE" in line:
            progress = max(progress, 0.36)
            status = "Extrayendo keypoints con SuperAnimal..."
        elif "[STEP] BBOX" in line:
            progress = max(progress, 0.62)
            status = "Aplicando filtro bbox a los keypoints..."
        elif "[STEP] SIMBA_FEATURES" in line:
            progress = max(progress, 0.65 if is_yolo else 0.82)
            status = "Sincronizando pose y features en SimBA..."
        elif "[STEP] ERROR" in line or line.startswith("[ERROR]"):
            status = "La extraccion termino con error."

    for line in reversed(lines):
        trim_match = re.search(r"\[TRIM\]\s+(\d+)/(\d+)", line)
        if trim_match:
            current = int(trim_match.group(1))
            total = max(int(trim_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.12 + (0.18 * ratio))
            status = f"Recortando video... {int(ratio * 100)}%"
            break

        heartbeat_match = re.search(r"\[HEARTBEAT\]\s+inference\s+elapsed=(\d+)s", line)
        if heartbeat_match:
            elapsed = int(heartbeat_match.group(1))
            progress = min(max(progress + 0.02, 0.42), 0.88)
            status = f"Extrayendo keypoints... {format_mm_ss(elapsed)} transcurridos"
            break

        import_match = re.search(r"\[HEARTBEAT\]\s+import_dlc\s+elapsed=(\d+)s", line)
        if import_match:
            elapsed = int(import_match.group(1))
            progress = min(max(progress + 0.015, 0.18), 0.32)
            status = f"Importando DeepLabCut... {format_mm_ss(elapsed)} transcurridos"
            break

        bbox_match = re.search(r"\[BBOX\]\s+(\d+)/(\d+)", line)
        if bbox_match:
            current = int(bbox_match.group(1))
            total = max(int(bbox_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.62 + (0.12 * ratio))
            status = f"Aplicando filtro bbox... {int(ratio * 100)}%"
            break

        bbox_render_match = re.search(r"\[RENDER\]\s+(\d+)/(\d+)", line)
        if bbox_render_match:
            current = int(bbox_render_match.group(1))
            total = max(int(bbox_render_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.74 + (0.08 * ratio))
            status = f"Renderizando validacion bbox... {int(ratio * 100)}%"
            break

        if "[ENGINE] EXITO: metricas generadas" in line or "[OUTPUT] FEATURE_CSV=" in line:
            progress = max(progress, 0.94)
            status = "Bridge SimBA listo."
            break

    if any("SUCCESS: Keypoints prep pipeline complete." in line for line in lines) or any(
        line.startswith("[OUTPUT] FINAL_FEATURE_CSV=") for line in lines
    ):
        progress = 1.0
        status = "Keypoints, filtro bbox y bridge SimBA listos."

    return progress, status, collect_output_markers(lines)


def parse_render_progress(lines, current_progress):
    progress = max(current_progress, 0.05)
    status = "Preparando render del overlay..."

    total_frames = None
    for line in lines:
        if "[RENDER] Frames to render:" in line:
            try:
                total_frames = max(int(line.rsplit(":", 1)[-1].strip()), 1)
            except ValueError:
                total_frames = None
        if "[RENDER] Done" in line:
            progress = 1.0
            status = "Overlay de keypoints completado."
        elif line.startswith("[OUTPUT] OVERLAY_VIDEO="):
            progress = max(progress, 0.96)
            status = "Finalizando archivo de vista previa..."

    for line in reversed(lines):
        render_match = re.search(r"\[RENDER\]\s+(\d+)/(\d+)", line)
        if render_match:
            current = int(render_match.group(1))
            total = max(int(render_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.10 + (0.85 * ratio))
            status = f"Renderizando overlay... {int(ratio * 100)}%"
            break

    return progress, status, collect_output_markers(lines)


def run_logged_process(command, log_path, parser, success_status, error_status):
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    log_placeholder = st.empty()

    progress = 0.02
    status = "Inicializando proceso..."
    outputs = {}

    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path, "w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            creationflags=no_window,
        )

        while process.poll() is None:
            lines = read_log_lines(log_path)
            progress, status, outputs = parser(lines, progress)
            progress_placeholder.progress(min(max(progress, 0.0), 0.99), text=status)
            status_placeholder.info(status)
            log_placeholder.code(trim_log_text(lines), language="bash")
            time.sleep(1)

    return_code = process.wait()
    lines = read_log_lines(log_path)
    progress, status, outputs = parser(lines, progress)

    if return_code == 0:
        progress_placeholder.progress(1.0, text=success_status)
        status_placeholder.success(success_status)
        final_status = success_status
        final_progress = 1.0
    else:
        final_progress = min(max(progress, 0.1), 0.95)
        progress_placeholder.progress(final_progress, text=error_status)
        status_placeholder.error(error_status)
        final_status = error_status

    log_placeholder.code(trim_log_text(lines), language="bash")
    st.session_state["keypoints_last_logs"] = trim_log_text(lines, max_lines=160)
    st.session_state["keypoints_last_status"] = final_status
    st.session_state["keypoints_last_progress"] = final_progress

    return return_code, lines, outputs


def sync_extract_outputs(outputs):
    output_map = {
        "analyzed_video": "ultimo_video_analizado",
        "filtered_pose": "ultimo_pose_filtrado",
        "filtered_pose_file": "ultimo_pose_filtrado",
        "filtered_csv": "ultimo_pose_filtrado_csv",
        "bbox_video": "ultimo_bbox_video",
        "bbox_validation_video": "ultimo_bbox_video",
        "feature_csv": "ultimo_feature_file",
        "final_feature_csv": "ultimo_feature_file",
        "yolo_keypoints_video": "ultimo_yolo_kp_video",
    }
    for output_key, session_key in output_map.items():
        candidate = outputs.get(output_key)
        if candidate and os.path.exists(candidate):
            st.session_state[session_key] = candidate

    raw_pose_candidate = outputs.get("raw_pose_file") or outputs.get("pose_file")
    if raw_pose_candidate and os.path.exists(raw_pose_candidate):
        st.session_state["ultimo_pose_crudo_file"] = raw_pose_candidate

    analyzed_video = (
        st.session_state.get("ultimo_video_analizado")
        or outputs.get("analyzed_video")
        or st.session_state.get("ruta_video_actual")
    )
    pose_file = (
        st.session_state.get("ultimo_pose_filtrado")
        or st.session_state.get("ultimo_pose_file")
        or outputs.get("pose_file")
        or outputs.get("raw_pose_file")
        or find_pose_file(analyzed_video)
    )

    if analyzed_video and os.path.exists(analyzed_video):
        st.session_state["ultimo_video_analizado"] = analyzed_video
    if pose_file and os.path.exists(pose_file):
        st.session_state["ultimo_pose_file"] = pose_file
    save_session()


def launch_log_viewer_console(log_path, title):
    powershell = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    safe_log_path = os.path.abspath(log_path).replace("'", "''")
    safe_title = title.replace("'", "''")

    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as file_handle:
            file_handle.write("[INFO] Esperando logs...\n")

    command = (
        f"$host.UI.RawUI.WindowTitle = '{safe_title}'; "
        f"Write-Host 'Monitoreando: {safe_log_path}'; "
        f"Get-Content -Path '{safe_log_path}' -Wait -Tail 40"
    )
    subprocess.Popen(
        [powershell, "-NoExit", "-Command", command],
        cwd=os.getcwd(),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )


def launch_background_extract(command):
    log_path = get_extract_log_path()
    wrapper_script = os.path.abspath(os.path.join("src", "scripts", "run_with_live_log.py"))

    with open(log_path, "w", encoding="utf-8") as file_handle:
        file_handle.write("[INFO] Lanzando extraccion de keypoints en segundo plano...\n")

    wrapper_command = [
        sys.executable,
        wrapper_script,
        "--log",
        log_path,
        "--label",
        "TT 2026 - DLC Keypoints",
        "--",
    ] + command

    process = subprocess.Popen(
        wrapper_command,
        cwd=os.getcwd(),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )

    meta = {
        "pid": process.pid,
        "status": "running",
        "log_path": log_path,
        "started_at": time.time(),
        "video_path": st.session_state.get("ruta_video_actual"),
        "outputs_imported": False,
        "completion_handled": False,
        "command": wrapper_command,
    }
    save_process_meta(meta)
    st.session_state["keypoints_show_completion_toast"] = False
    st.session_state["keypoints_last_status"] = "Extraccion y preparacion bbox/SimBA lanzadas en segundo plano."
    st.session_state["keypoints_last_progress"] = 0.03
    st.session_state["keypoints_last_logs"] = trim_log_text(read_log_lines(log_path))
    st.session_state["ultimo_overlay_path"] = None
    save_session()


def cancel_background_extract(meta):
    if not meta:
        return

    log_path = meta.get("log_path") or get_extract_log_path()
    append_log_line(log_path, "[STEP] CANCELLED")
    append_log_line(log_path, "[INFO] Cancellation requested from Streamlit.")

    pid = meta.get("pid")
    if pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )

    meta["status"] = "cancelled"
    meta["completed_at"] = time.time()
    meta["completion_handled"] = False
    save_process_meta(meta)
    st.session_state["keypoints_last_status"] = "Extraccion cancelada por el usuario."
    st.session_state["keypoints_last_progress"] = 0.12
    st.session_state["keypoints_last_logs"] = trim_log_text(read_log_lines(log_path), max_lines=160)
    save_session()


def get_extract_snapshot():
    meta = load_process_meta()
    log_path = meta.get("log_path") if meta else get_extract_log_path()
    lines = read_log_lines(log_path)
    starting_progress = (
        float(meta.get("last_progress", 0.0) or 0.0)
        if meta
        else float(st.session_state.get("keypoints_last_progress", 0.0) or 0.0)
    )
    progress, status, outputs = parse_extract_progress(lines, starting_progress)
    needs_rerun = False

    if meta:
        is_running = bool(meta.get("pid") and is_pid_alive(meta.get("pid")) and meta.get("status") == "running")
        if is_running:
            meta["last_progress"] = progress
            meta["last_status"] = status
            save_process_meta(meta)
        else:
            outcome = meta.get("status") if meta.get("status") != "running" else infer_extract_outcome(lines)
            meta["status"] = outcome
            meta["completed_at"] = meta.get("completed_at") or time.time()

            if outcome == "completed":
                progress = 1.0
                status = "Keypoints, filtro bbox y bridge SimBA listos."
                if not meta.get("outputs_imported"):
                    sync_extract_outputs(outputs)
                    meta["outputs_imported"] = True
                if not meta.get("completion_handled"):
                    st.session_state["keypoints_show_completion_toast"] = True
            elif outcome == "cancelled":
                progress = min(max(progress, 0.1), 0.95)
                status = "Extraccion cancelada por el usuario."
            else:
                progress = min(max(progress, 0.1), 0.95)
                status = "La extraccion de keypoints termino con error."

            meta["last_progress"] = progress
            meta["last_status"] = status
            if not meta.get("completion_handled"):
                meta["completion_handled"] = True
                needs_rerun = True
            save_process_meta(meta)
    else:
        is_running = False
        if lines:
            inferred_outcome = infer_extract_outcome(lines)
            if inferred_outcome == "completed":
                progress = 1.0
                status = "Keypoints, filtro bbox y bridge SimBA listos."
            elif inferred_outcome == "cancelled":
                progress = min(max(progress, 0.1), 0.95)
                status = "Extraccion cancelada por el usuario."
            elif inferred_outcome in {"error", "stopped"}:
                progress = min(max(progress, 0.1), 0.95)
                status = "La extraccion de keypoints termino con error."

    st.session_state["keypoints_last_logs"] = trim_log_text(lines, max_lines=160)
    st.session_state["keypoints_last_status"] = status
    st.session_state["keypoints_last_progress"] = progress

    return {
        "meta": meta,
        "is_running": is_running,
        "progress": progress,
        "status": status,
        "lines": lines,
        "outputs": outputs,
        "log_path": log_path,
        "needs_rerun": needs_rerun,
    }


def find_pose_file(video_path):
    if not video_path:
        return None

    video_dir = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    patterns = [
        f"{base_name}*filtered*.csv",
        f"{base_name}*filtered*.h5",
        f"{base_name}*_bbox_constrained.csv",
        f"{base_name}*_bbox_constrained.h5",
        f"{base_name}*DLC*.csv",
        f"{base_name}*DLC*.h5",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(video_dir, pattern)))
        if matches:
            return os.path.abspath(matches[-1])
    return None


def collect_generated_files():
    files = []
    for key in [
        "ultimo_pose_file",
        "ultimo_pose_filtrado",
        "ultimo_overlay_path",
        "ultimo_bbox_video",
        "ultimo_feature_file",
        "ultimo_video_analizado",
    ]:
        candidate = st.session_state.get(key)
        if candidate and os.path.exists(candidate) and candidate not in files:
            files.append(candidate)

    analyzed_video = st.session_state.get("ultimo_video_analizado") or st.session_state.get("ruta_video_actual")
    if analyzed_video:
        video_dir = os.path.dirname(analyzed_video)
        base_name = os.path.splitext(os.path.basename(analyzed_video))[0]
        patterns = [
            f"{base_name}*filtered*.csv",
            f"{base_name}*filtered*.h5",
            f"{base_name}*_bbox_constrained.csv",
            f"{base_name}*_bbox_constrained.h5",
            f"{base_name}*_bbox_constraint.mp4",
            f"{base_name}*DLC*.csv",
            f"{base_name}*DLC*.h5",
            f"{base_name}*_dlc_overlay.mp4",
            f"{base_name}*labeled*.mp4",
        ]
        for pattern in patterns:
            for match in sorted(glob.glob(os.path.join(video_dir, pattern))):
                abs_match = os.path.abspath(match)
                if abs_match not in files:
                    files.append(abs_match)

    return files


def build_keypoints_main_outputs():
    candidates = [
        ("Video analizado", st.session_state.get("ultimo_video_analizado")),
        ("Pose DLC cruda (H5)", st.session_state.get("ultimo_pose_crudo_file")),
        ("Pose filtrada bbox (H5)", st.session_state.get("ultimo_pose_filtrado")),
        ("CSV filtrado bbox", st.session_state.get("ultimo_pose_filtrado_csv")),
        ("Video de validacion bbox", st.session_state.get("ultimo_bbox_video")),
        ("Features SimBA (CSV)", st.session_state.get("ultimo_feature_file")),
        ("Vista previa HUD", st.session_state.get("ultimo_overlay_path")),
    ]

    outputs = []
    for label, candidate in candidates:
        resolved = path_if_exists(candidate)
        if resolved:
            outputs.append((label, resolved))
    return outputs


def is_extract_completed(snapshot=None):
    if snapshot:
        if snapshot.get("is_running"):
            return False
        meta = snapshot.get("meta") or {}
        if meta.get("status") == "completed":
            return True
        status = str(snapshot.get("status", ""))
        return status == "Keypoints, filtro bbox y bridge SimBA listos."

    return st.session_state.get("keypoints_last_status") == "Keypoints, filtro bbox y bridge SimBA listos."


def render_output_panel(snapshot=None):
    generated_files = collect_generated_files()
    main_outputs = build_keypoints_main_outputs()
    overlay_path = st.session_state.get("ultimo_overlay_path")
    if overlay_path and not os.path.exists(overlay_path):
        overlay_path = None

    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Resumen de salida")
    st.caption(
        "Este modulo deja lista la pose cruda, aplica el filtro bbox y sincroniza el bridge hacia SimBA. "
        "La vista previa HUD es un overlay de control de calidad y prioriza la pose filtrada si ya existe. "
        "El video multimodal final sigue viviendo en el Modulo 04."
    )

    if is_extract_completed(snapshot) and main_outputs:
        st.success(
            "Proceso completado correctamente. Los keypoints, el filtro bbox y la sincronizacion hacia SimBA ya estan listos."
        )
        st.markdown("##### Archivos principales")
        st.caption("Estas son las rutas utiles para encontrar rapidamente los resultados del proceso.")
        for label, file_path in main_outputs:
            st.markdown(f"**{label}**")
            st.code(file_path, language=None)
    elif generated_files:
        st.markdown("##### Archivos detectados")
        for file_path in generated_files:
            st.write(f"- `{os.path.basename(file_path)}`")
    else:
        st.info("Todavia no hay archivos de keypoints generados para este video.")

    if generated_files:
        with st.expander("Ver todos los archivos detectados", expanded=False):
            for file_path in generated_files:
                st.code(file_path, language=None)

    yolo_kp_video = st.session_state.get("ultimo_yolo_kp_video")
    if yolo_kp_video and not os.path.exists(yolo_kp_video):
        yolo_kp_video = None

    if yolo_kp_video:
        st.markdown("---")
        st.markdown("##### Vista previa YOLO Pose")
        st.video(yolo_kp_video)
    elif overlay_path:
        st.markdown("---")
        st.markdown("##### Vista previa disponible")
        st.video(overlay_path)

    keypoints_yolo_dir = os.path.abspath("keypoints_yolo")
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("ABRIR CARPETA KEYPOINTS YOLO", use_container_width=True, key="btn_open_kp_folder"):
            os.makedirs(keypoints_yolo_dir, exist_ok=True)
            subprocess.Popen(["explorer", keypoints_yolo_dir])
            st.toast(f"Abriendo: {keypoints_yolo_dir}")
    with col_btn2:
        if yolo_kp_video:
            st.code(yolo_kp_video, language=None)
        else:
            st.caption("Los videos de keypoints YOLO se guardan en `keypoints_yolo/`.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_log_panel(snapshot=None):
    st.markdown("#### Estado y Logs")
    if snapshot:
        last_progress = float(snapshot.get("progress", 0.0) or 0.0)
        last_status = snapshot.get("status", "Aun no se inicia una ejecucion real de keypoints.")
        last_logs = trim_log_text(snapshot.get("lines", []), max_lines=160)
    else:
        last_progress = float(st.session_state.get("keypoints_last_progress", 0.0) or 0.0)
        last_status = st.session_state.get("keypoints_last_status", "Aun no se inicia una ejecucion real de keypoints.")
        last_logs = st.session_state.get("keypoints_last_logs", "[INFO] Aun no hay logs de ejecucion.")

    st.progress(min(max(last_progress, 0.0), 1.0), text=last_status)
    st.code(last_logs, language="bash")


def build_extract_command(batch_size, device_option, yolo_mode=False):
    script_path = os.path.abspath(os.path.join("src", "scripts", "run_behavior_pipeline.py"))
    video_path = os.path.abspath(st.session_state["ruta_video_actual"])
    start_seconds = int(st.session_state.get("inicio_recorte", 0) or 0)
    end_seconds = st.session_state.get("fin_recorte")
    zones = st.session_state.get("zonas_configuradas") or []

    command = [
        sys.executable,
        script_path,
        "--video",
        video_path,
        "--batch-size",
        str(int(batch_size)),
        "--start-seconds",
        str(start_seconds),
        "--skip-final-video",
    ]
    if yolo_mode:
        command.extend(["--backend", "yolo"])
    else:
        if end_seconds is not None:
            command.extend(["--end-seconds", str(int(end_seconds))])
        if device_option == "CPU (Forzar)":
            command.append("--force-cpu")
    if zones:
        zones_path = os.path.join(ensure_logs_dir(), "keypoints_zonas_activas.json")
        with open(zones_path, "w", encoding="utf-8") as file_handle:
            json.dump(zones, file_handle, indent=2, ensure_ascii=False)
        command.extend(["--zones-file", os.path.abspath(zones_path)])
    return command


def build_render_command():
    pose_path = st.session_state.get("ultimo_pose_file") or find_pose_file(
        st.session_state.get("ultimo_video_analizado") or st.session_state.get("ruta_video_actual")
    )
    if not pose_path:
        raise FileNotFoundError("No se encontro un archivo de pose DLC para renderizar.")

    analysis_video = st.session_state.get("ultimo_video_analizado") or st.session_state.get("ruta_video_actual")
    output_path = os.path.splitext(os.path.abspath(analysis_video))[0] + "_dlc_overlay.mp4"
    render_script = os.path.abspath(os.path.join("src", "scripts", "render_dlc_keypoints_video.py"))
    command = [
        sys.executable,
        render_script,
        "--video",
        os.path.abspath(analysis_video),
        "--pose",
        os.path.abspath(pose_path),
        "--output",
        output_path,
    ]
    return command, output_path, pose_path


# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Modulo 02: Extraccion de Keypoints")
st.markdown(
    """
    Proceso de vision computacional para la extraccion de coordenadas anatomicas.
    Utilice DeepLabCut SuperAnimal para procesar el video y generar una vista previa del overlay.
    """
)

st.divider()

# ================= 3. VIDEO CHECK =================
video_ok = render_video_banner("Sesion de Keypoints Activa")
if not video_ok:
    st.error("No hay video activo. Seleccionalo primero en Ingesta de Video.")
    st.stop()

active_video = st.session_state.get("ruta_video_actual")
pose_candidate = st.session_state.get("ultimo_pose_file") or find_pose_file(
    st.session_state.get("ultimo_video_analizado") or active_video
)
if pose_candidate:
    st.session_state["ultimo_pose_file"] = pose_candidate

dlc_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))
dlc_available = os.path.exists(dlc_python)
log_dir = ensure_logs_dir()
extract_snapshot = get_extract_snapshot()
if extract_snapshot["needs_rerun"]:
    st.rerun()
if st.session_state.pop("keypoints_show_completion_toast", False):
    st.toast("Extraccion completada. Revisa el panel de salida para ubicar los archivos generados.")

# ================= 4. MAIN LAYOUT =================
action = None
batch_size = int(st.session_state.get("dlc_batch_size", 16) or 16)
device_option = st.session_state.get("dlc_device_opt", "Auto (Recomendado)")

col_left, col_right = st.columns([1, 1.35])

with col_left:
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Configuracion del Motor")
    # Motor fijo en YOLO — DLC disponible en código para versiones futuras
    motor = "YOLO Pose (Experimental)"
    st.info("Motor activo: **YOLO Pose v4** — 3,953 imágenes | mAP50: 99.5%")

    st.markdown("---")
    st.caption(f"Rango activo a analizar: `{get_trim_summary()}`")

    with st.expander("Parametros de Analisis", expanded=True):
        batch_size = st.slider(
            "Batch Size",
            min_value=4,
            max_value=32,
            value=int(st.session_state.get("dlc_batch_size", 16) or 16),
            step=4,
            help="Capado a 32 para no castigar demasiado la GPU. En laptop, 16 suele ser el punto mas estable.",
        )
        device_option = st.selectbox(
            "Dispositivo Hardware",
            ["Auto (Recomendado)", "CPU (Forzar)"],
            index=0 if st.session_state.get("dlc_device_opt", "Auto (Recomendado)") == "Auto (Recomendado)" else 1,
        )
        st.caption("Mi recomendacion: deja 32 como tope, pero usa 16 por default y sube a 24/32 solo si la GPU se mantiene estable.")
        st.caption("Al terminar DLC, este flujo aplica bbox y deja sincronizado el bridge hacia SimBA en automatico.")

    extraction_running = extract_snapshot["is_running"]
    yolo_mode = motor == "YOLO Pose (Experimental)"
    extraction_disabled = (not yolo_mode and not dlc_available) or extraction_running
    if not dlc_available and not yolo_mode:
        st.error(f"No se encontro el interprete GPU esperado en `{dlc_python}`.")

    st.markdown("<br>", unsafe_allow_html=True)
    if extraction_running:
        st.info(
            "La preparacion completa sigue corriendo en segundo plano. Puedes moverte entre modulos y volver; "
            "esta pagina reconstruye el progreso leyendo el log del proceso."
        )
        c_action_1, c_action_2 = st.columns(2)
        with c_action_1:
            if st.button(
                "DETENER EXTRACCION",
                use_container_width=True,
                key="btn_stop_keypoints",
            ):
                action = "cancel_extract"
        with c_action_2:
            if st.button(
                "ABRIR CONSOLA DE LOGS",
                use_container_width=True,
                key="btn_open_keypoints_console",
            ):
                action = "open_console"
        if extract_snapshot["meta"]:
            st.caption(f"PID activo: `{extract_snapshot['meta'].get('pid')}`")
    else:
        if st.button(
            "INICIAR EXTRACCION",
            type="primary",
            use_container_width=True,
            disabled=extraction_disabled,
            key="btn_start_keypoints",
        ):
            action = "extract"
        if os.path.exists(extract_snapshot["log_path"]):
            if st.button(
                "ABRIR ULTIMA CONSOLA DE LOGS",
                use_container_width=True,
                key="btn_open_keypoints_console_idle",
            ):
                action = "open_console"
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    render_output_panel(extract_snapshot)
    hud_disabled = pose_candidate is None or extract_snapshot["is_running"]
    if st.button(
        "RENDERIZAR VISTA PREVIA (HUD)",
        use_container_width=True,
        disabled=hud_disabled,
        key="btn_render_hud",
    ):
        action = "render"
    if hud_disabled:
        st.caption("Primero extrae los keypoints para poder generar el overlay de inspeccion.")

# ================= 5. ESTADO Y LOGS =================
st.markdown("<br>", unsafe_allow_html=True)

if action == "extract":
    st.session_state["dlc_batch_size"] = int(batch_size)
    st.session_state["dlc_device_opt"] = device_option
    save_session()

    launch_background_extract(build_extract_command(batch_size, device_option, yolo_mode=yolo_mode))
    st.rerun()

elif action == "cancel_extract":
    cancel_background_extract(extract_snapshot["meta"])
    st.rerun()

elif action == "open_console":
    launch_log_viewer_console(extract_snapshot["log_path"], "TT 2026 - Logs Keypoints")
    st.toast("Se abrio una consola adicional para monitorear los logs.")

elif action == "render":
    try:
        command, output_path, pose_path = build_render_command()
    except Exception as error:
        st.session_state["keypoints_last_status"] = f"No se pudo iniciar el render: {error}"
        st.session_state["keypoints_last_progress"] = 0.0
        st.session_state["keypoints_last_logs"] = f"[ERROR] {error}"
    else:
        render_log_path = get_render_log_path()
        return_code, lines, outputs = run_logged_process(
            command=command,
            log_path=render_log_path,
            parser=parse_render_progress,
            success_status="Vista previa HUD generada correctamente.",
            error_status="La generacion del overlay termino con error.",
        )
        if return_code == 0:
            overlay_path = outputs.get("overlay_video") or output_path
            st.session_state["ultimo_overlay_path"] = overlay_path
            st.session_state["ultimo_pose_file"] = pose_path
            save_session()
            st.rerun()


@st.fragment(run_every="2s" if extract_snapshot["is_running"] else None)
def render_runtime_monitor():
    snapshot = get_extract_snapshot()
    if snapshot["is_running"]:
        render_log_panel(snapshot)
    else:
        render_log_panel()
    if snapshot["needs_rerun"]:
        st.rerun()


render_runtime_monitor()

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align: center; color: {colors['text_sub']}; font-size: 0.8rem;">
        Identidad Institucional IPN &bull; ESCOM &bull; TT 2026
    </div>
    """,
    unsafe_allow_html=True,
)
