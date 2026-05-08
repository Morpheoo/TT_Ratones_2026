import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session, save_session
from ui_components import run_page_splash
import importlib
import ui_theme

importlib.reload(ui_theme)
from ui_theme import render_topbar, use_theme, inject_sidebar_profile
from video_context_banner import render_video_banner
from config import (
    GROOMING_MODEL,
    GROOMING_MODEL_YOLO,
    SIMBA_BASE,
    SIMBA_PROJECT_DIR,
    SIMBA_YOLO_BASE,
    THIGMOTAXIS_MODEL,
    THIGMOTAXIS_MODEL_YOLO,
)

st.set_page_config(page_title="Analisis Final | IPN", page_icon="assets/logos/logo_ria.png", layout="wide")

load_session()
colors = use_theme()

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.warning("Debes iniciar sesion antes de usar el sistema.")
    st.stop()

run_page_splash(
    "page_analysis_final",
    [
        "Inicializando pipeline multimodal...",
        "Verificando modelos y recursos activos...",
        "Preparando ejecucion conductual...",
    ],
    subtitle="TT 2026 - Cargando analisis final...",
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
    if st.button("Cerrar Sesión", key="logout_btn", use_container_width=True):
        from session_utils import clear_session
        clear_session()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Sidebar con navegación
    inject_sidebar_profile(show_admin_button=True)


def format_mm_ss(total_seconds):
    total_seconds = max(0, int(total_seconds or 0))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def ensure_logs_dir():
    log_dir = os.path.join("logs", "analysis")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def read_log_lines(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as file_handle:
        return [line.rstrip() for line in file_handle.readlines()]


def trim_log_text(lines, max_lines=180):
    if not lines:
        return "[INFO] Aun no hay logs del pipeline."
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


def parse_pipeline_progress(lines, current_progress):
    progress = max(current_progress, 0.02)
    status = "Preparando pipeline multimodal..."

    for line in lines:
        if "[STEP] BOOT" in line:
            progress = max(progress, 0.05)
            status = "Preparando pipeline multimodal..."
        elif "[STEP] DLC" in line:
            progress = max(progress, 0.14)
            status = "Extrayendo keypoints con DeepLabCut..."
        elif "[STEP] YOLO_POSE" in line:
            progress = max(progress, 0.18)
            status = "Extrayendo keypoints con YOLO Pose..."
        elif "[STEP] BBOX" in line:
            progress = max(progress, 0.46)
            status = "Aplicando filtro anatomico bbox..."
        elif "[STEP] SIMBA_FEATURES" in line:
            progress = max(progress, 0.68)
            status = "Importando pose al proyecto SimBA..."
        elif "[STEP] GROOMING_LSTM" in line:
            progress = max(progress, 0.76)
            status = "Aplicando memoria temporal LSTM a Grooming..."
        elif "[STEP] FINAL_VIDEO" in line:
            progress = max(progress, 0.82)
            status = "Renderizando video multimodal final..."
        elif "[STEP] ERROR" in line or line.startswith("[ERROR]"):
            status = "El pipeline termino con error."

    for line in reversed(lines):
        trim_match = re.search(r"\[TRIM\]\s+(\d+)/(\d+)", line)
        if trim_match:
            current = int(trim_match.group(1))
            total = max(int(trim_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.14 + (0.08 * ratio))
            status = f"Recortando video... {int(ratio * 100)}%"
            break

        inference_match = re.search(r"\[HEARTBEAT\]\s+inference\s+elapsed=(\d+)s", line)
        if inference_match:
            elapsed = int(inference_match.group(1))
            progress = min(max(progress + 0.015, 0.24), 0.42)
            status = f"Extrayendo keypoints... {format_mm_ss(elapsed)} transcurridos"
            break

        import_match = re.search(r"\[HEARTBEAT\]\s+import_dlc\s+elapsed=(\d+)s", line)
        if import_match:
            elapsed = int(import_match.group(1))
            progress = min(max(progress + 0.01, 0.18), 0.28)
            status = f"Cargando DeepLabCut... {format_mm_ss(elapsed)} transcurridos"
            break

        bbox_match = re.search(r"\[BBOX\]\s+(\d+)/(\d+)", line)
        if bbox_match:
            current = int(bbox_match.group(1))
            total = max(int(bbox_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.48 + (0.10 * ratio))
            status = f"Detectando bbox YOLO... {int(ratio * 100)}%"
            break

        bbox_render_match = re.search(r"\[RENDER\]\s+(\d+)/(\d+)", line)
        if bbox_render_match:
            current = int(bbox_render_match.group(1))
            total = max(int(bbox_render_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.58 + (0.08 * ratio))
            status = f"Renderizando validacion bbox... {int(ratio * 100)}%"
            break

        final_render_match = re.search(r"Renderizados\s+(\d+)/(\d+)\s+frames", line)
        if final_render_match:
            current = int(final_render_match.group(1))
            total = max(int(final_render_match.group(2)), 1)
            ratio = current / total
            progress = max(progress, 0.84 + (0.14 * ratio))
            status = f"Renderizando HUD multimodal... {int(ratio * 100)}%"
            break

    if any("SUCCESS: Full behavior pipeline complete." in line for line in lines) or any(
        line.startswith("[OUTPUT] FINAL_VIDEO=") for line in lines
    ):
        progress = 1.0
        status = "Pipeline multimodal completado."

    return progress, status, collect_output_markers(lines)


def get_analysis_state_path():
    return os.path.abspath(os.path.join(ensure_logs_dir(), "analysis_pipeline.process.json"))


def save_analysis_meta(meta):
    with open(get_analysis_state_path(), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def load_analysis_meta():
    path = get_analysis_state_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_pid_alive(pid):
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {int(pid)}"],
            capture_output=True, text=True, check=False,
        )
        return str(int(pid)) in (result.stdout or "")
    except Exception:
        return False


def launch_background_analysis(command, log_path):
    wrapper_script = os.path.abspath(os.path.join("src", "scripts", "run_with_live_log.py"))
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("[INFO] Lanzando pipeline multimodal en segundo plano...\n")

    wrapper_command = [
        sys.executable, wrapper_script,
        "--log", log_path,
        "--label", "TT 2026 - Analisis Final YOLO",
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
    }
    save_analysis_meta(meta)
    st.session_state["analysis_last_status"] = "Pipeline multimodal lanzado en segundo plano."
    st.session_state["analysis_last_progress"] = 0.03
    st.session_state["analysis_last_logs"] = trim_log_text(read_log_lines(log_path))


def cancel_background_analysis(meta):
    if not meta:
        return
    log_path = meta.get("log_path") or os.path.join(ensure_logs_dir(), "analysis_pipeline.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("[STEP] CANCELLED\n[INFO] Cancelado por el usuario.\n")
    pid = meta.get("pid")
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, check=False)
    meta["status"] = "cancelled"
    save_analysis_meta(meta)
    st.session_state["analysis_last_status"] = "Pipeline cancelado por el usuario."


def get_analysis_snapshot():
    meta = load_analysis_meta()
    log_path = meta.get("log_path") if meta else os.path.join(ensure_logs_dir(), "analysis_pipeline.log")
    lines = read_log_lines(log_path)
    progress, status, outputs = parse_pipeline_progress(lines, float(
        st.session_state.get("analysis_last_progress", 0.0) or 0.0))
    needs_rerun = False

    if meta:
        is_running = bool(meta.get("pid") and is_pid_alive(meta.get("pid")) and meta.get("status") == "running")
        if is_running:
            meta["last_progress"] = progress
            save_analysis_meta(meta)
        else:
            if meta.get("status") == "running":
                if any("[STEP] COMPLETE" in l for l in lines):
                    meta["status"] = "completed"
                elif any("[STEP] CANCELLED" in l for l in lines):
                    meta["status"] = "cancelled"
                else:
                    meta["status"] = "error"

            if meta["status"] == "completed":
                progress = 1.0
                status = "Pipeline multimodal completado."
                if not meta.get("outputs_imported"):
                    _sync_analysis_outputs(outputs)
                    meta["outputs_imported"] = True
                if not meta.get("completion_handled"):
                    st.session_state["analysis_show_toast"] = True
            elif meta["status"] == "cancelled":
                status = "Pipeline cancelado por el usuario."
            else:
                status = "El pipeline termino con error. Revisa los logs."

            meta["last_progress"] = progress
            if not meta.get("completion_handled"):
                meta["completion_handled"] = True
                needs_rerun = True
            save_analysis_meta(meta)
    else:
        is_running = False

    st.session_state["analysis_last_logs"] = trim_log_text(lines, max_lines=220)
    st.session_state["analysis_last_status"] = status
    st.session_state["analysis_last_progress"] = progress
    return {"meta": meta, "is_running": is_running, "progress": progress,
            "status": status, "lines": lines, "outputs": outputs,
            "log_path": log_path, "needs_rerun": needs_rerun}


def _sync_analysis_outputs(outputs):
    output_map = {
        "analyzed_video": "ultimo_video_analizado",
        "raw_pose_file": "ultimo_pose_file",
        "filtered_pose": "ultimo_pose_filtrado",
        "filtered_pose_file": "ultimo_pose_filtrado",
        "bbox_video": "ultimo_bbox_video",
        "feature_csv": "ultimo_feature_file",
        "final_feature_csv": "ultimo_feature_file",
        "multimodal_video": "ultimo_multimodal_video",
        "final_video": "ultimo_multimodal_video",
        "trajectory_file": "ultimo_trajectory_file",
        "final_trajectory": "ultimo_trajectory_file",
        "grooming_timelog": "ultimo_grooming_timelog",
        "final_grooming_timelog": "ultimo_grooming_timelog",
        "grooming_lstm_csv": "ultimo_grooming_lstm_csv",
        "final_grooming_lstm_csv": "ultimo_grooming_lstm_csv",
        "thigmotaxis_timelog": "ultimo_thigmotaxis_timelog",
        "final_thigmotaxis_timelog": "ultimo_thigmotaxis_timelog",
        "yolo_keypoints_video": "ultimo_yolo_kp_video",
        "resultados_dir": "ultimo_resultados_dir",
    }
    for out_key, sess_key in output_map.items():
        val = outputs.get(out_key)
        if val and os.path.exists(val):
            st.session_state[sess_key] = val
    save_session()


def find_pose_file(video_path):
    if not video_path:
        return None

    video_dir = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    patterns = [
        f"{base_name}*filtered*.h5",
        f"{base_name}*_bbox_constrained.h5",
        f"{base_name}*DLC*.h5",
        f"{base_name}*filtered*.csv",
        f"{base_name}*_bbox_constrained.csv",
        f"{base_name}*DLC*.csv",
    ]
    for pattern in patterns:
        matches = sorted(Path(video_dir).glob(pattern))
        if matches:
            return str(matches[-1].resolve())
    return None


def find_feature_file(video_path):
    if not video_path:
        return None
    candidate = Path(SIMBA_PROJECT_DIR) / "csv" / "features_extracted" / f"{Path(video_path).stem}.csv"
    return str(candidate.resolve()) if candidate.exists() else None


def write_zones_temp_file():
    zones = st.session_state.get("zonas_configuradas") or []
    if not zones:
        return None
    log_dir = ensure_logs_dir()
    zones_path = os.path.join(log_dir, "zonas_activas.json")
    with open(zones_path, "w", encoding="utf-8") as file_handle:
        json.dump(zones, file_handle, indent=2, ensure_ascii=False)
    return zones_path


def infer_trim_window(record):
    candidates = [
        record.get("trajectory_path"),
        record.get("video_path"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        match = re.search(r"_trimmed_(\d+)_(\d+)", os.path.basename(str(candidate)))
        if match:
            return int(match.group(1)), int(match.group(2))

    duration_seconds = record.get("duration_seconds")
    if duration_seconds not in (None, "", 0):
        try:
            return 0, int(float(duration_seconds))
        except (TypeError, ValueError):
            pass
    return 0, None


def reset_analysis_runtime_state():
    for key in [
        "ultimo_video_analizado",
        "ultimo_pose_file",
        "ultimo_pose_filtrado",
        "ultimo_bbox_video",
        "ultimo_feature_file",
        "ultimo_multimodal_video",
        "ultimo_trajectory_file",
        "ultimo_grooming_timelog",
        "ultimo_grooming_lstm_csv",
        "ultimo_thigmotaxis_timelog",
        "analysis_db_notice",
        "analysis_persist_key",
        "analysis_last_logs",
        "analysis_last_status",
        "analysis_last_progress",
    ]:
        st.session_state.pop(key, None)


def fetch_reprocessable_experiments(limit=25):
    try:
        from db.connection import get_db_engine
    except Exception:
        return []

    engine = get_db_engine()
    if not engine:
        return []

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS trajectory_path TEXT"))
        conn.commit()
        rows = conn.execute(
            text(
                """
                SELECT
                    e.id,
                    e.rat_id,
                    e.treatment,
                    e.experiment_date,
                    e.responsible,
                    e.video_path,
                    e.duration_seconds,
                    e.created_at,
                    COALESCE(ar.trajectory_path, '') AS trajectory_path,
                    COUNT(r.id) AS zone_count
                FROM experiments e
                LEFT JOIN (
                    SELECT DISTINCT ON (experiment_id)
                        experiment_id,
                        trajectory_path,
                        timestamp,
                        id
                    FROM analysis_results
                    ORDER BY experiment_id, timestamp DESC, id DESC
                ) ar
                    ON ar.experiment_id = e.id
                LEFT JOIN roi_configurations r
                    ON r.experiment_id = e.id
                GROUP BY
                    e.id,
                    e.rat_id,
                    e.treatment,
                    e.experiment_date,
                    e.responsible,
                    e.video_path,
                    e.duration_seconds,
                    e.created_at,
                    ar.trajectory_path
                ORDER BY e.created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    records = []
    for row in rows:
        record = dict(row)
        video_path = record.get("video_path")
        if not video_path or not os.path.exists(video_path):
            continue
        records.append(record)
    return records


def load_previous_experiment_context(record):
    try:
        from db.connection import get_db_engine
        from db.experiment_history import load_experiment_zones
    except Exception as error:
        return False, f"No se pudo cargar la capa de historial: {error}"

    engine = get_db_engine()
    if not engine:
        return False, "No se encontro conexion a PostgreSQL para recuperar zonas historicas."

    experiment_id = int(record["id"])
    zones = load_experiment_zones(engine, experiment_id)
    start_seconds, end_seconds = infer_trim_window(record)

    st.session_state["ruta_video_actual"] = record["video_path"]
    st.session_state["id_raton_actual"] = record.get("rat_id") or Path(record["video_path"]).stem
    st.session_state["treatment"] = record.get("treatment") or "Control"
    st.session_state["ingesta_responsable_actual"] = record.get("responsible") or st.session_state.get("user_name", "Investigador")
    st.session_state["inicio_recorte"] = int(start_seconds or 0)
    st.session_state["fin_recorte"] = None if end_seconds is None else int(end_seconds)
    st.session_state["zonas_configuradas"] = zones
    st.session_state["analysis_selected_experiment_id"] = experiment_id
    reset_analysis_runtime_state()
    save_session()

    return True, (
        f"Se cargo el registro previo #{experiment_id} para reprocesarlo con el pipeline actual. "
        f"Recorte inferido: {format_mm_ss(start_seconds)} -> "
        f"{format_mm_ss(end_seconds) if end_seconds is not None else 'fin del video'}."
    )


def build_pipeline_command(batch_size, device_option, zones_file):
    runner_script = os.path.abspath(os.path.join("src", "scripts", "run_behavior_pipeline.py"))
    video_path = os.path.abspath(st.session_state["ruta_video_actual"])
    start_seconds = int(st.session_state.get("inicio_recorte", 0) or 0)
    end_seconds = st.session_state.get("fin_recorte")

    command = [
        sys.executable,
        runner_script,
        "--video",
        video_path,
        "--project-root",
        str(Path(SIMBA_YOLO_BASE).resolve()),
        "--batch-size",
        str(int(batch_size)),
        "--start-seconds",
        str(start_seconds),
        "--backend", "yolo",
        "--grooming-source", "rescue",
    ]
    if end_seconds is not None:
        command.extend(["--end-seconds", str(int(end_seconds))])
    if zones_file:
        command.extend(["--zones-file", zones_file])
    return command


def collect_generated_files():
    files = []
    for key in [
        "ultimo_pose_file",
        "ultimo_pose_filtrado",
        "ultimo_bbox_video",
        "ultimo_feature_file",
        "ultimo_multimodal_video",
        "ultimo_trajectory_file",
        "ultimo_grooming_timelog",
        "ultimo_thigmotaxis_timelog",
    ]:
        candidate = st.session_state.get(key)
        if candidate and os.path.exists(candidate) and candidate not in files:
            files.append(candidate)
    return files


def build_summary_from_trajectory(trajectory_path):
    if not trajectory_path or not os.path.exists(trajectory_path):
        return None

    df = pd.read_csv(trajectory_path)
    if df.empty:
        return None

    time_series = pd.to_numeric(df.get("Tiempo (s)"), errors="coerce")
    step_seconds = time_series.diff().dropna()
    step_seconds = step_seconds[step_seconds > 0]
    frame_seconds = float(step_seconds.median()) if not step_seconds.empty else (1.0 / 30.0)

    zone_series = df.get("Zona", pd.Series(["Outside"] * len(df))).astype(str)
    open_time = float(zone_series.str.contains("abierto", case=False, na=False).sum() * frame_seconds)
    closed_time = float(zone_series.str.contains("cerrado", case=False, na=False).sum() * frame_seconds)
    center_time = float(zone_series.str.contains("centro", case=False, na=False).sum() * frame_seconds)
    grooming_series = df["Grooming"] if "Grooming" in df.columns else pd.Series([0] * len(df))
    thigmotaxis_series = df["Thigmotaxis"] if "Thigmotaxis" in df.columns else pd.Series([0] * len(df))
    grooming_duration = float(pd.to_numeric(grooming_series, errors="coerce").fillna(0).sum() * frame_seconds)
    thigmotaxis_duration = float(pd.to_numeric(thigmotaxis_series, errors="coerce").fillna(0).sum() * frame_seconds)
    total_duration = float(len(df) * frame_seconds)

    return {
        "total_duration": total_duration,
        "time_open_arms": open_time,
        "time_closed_arms": closed_time,
        "time_center": center_time,
        "grooming_duration": grooming_duration,
        "thigmotaxis_duration": thigmotaxis_duration,
        "trajectory_path": trajectory_path,
    }


def _video_path_variants(video_path):
    if not video_path:
        return []

    variants = []
    raw_path = os.path.normpath(str(video_path))
    variants.append(raw_path)

    absolute_path = os.path.abspath(raw_path)
    variants.append(os.path.normpath(absolute_path))

    try:
        variants.append(os.path.normpath(os.path.relpath(absolute_path, os.getcwd())))
    except ValueError:
        pass

    return list(dict.fromkeys(variants))


def _stored_video_path(video_path):
    if not video_path:
        return video_path

    raw_path = os.path.normpath(str(video_path))
    absolute_path = os.path.abspath(raw_path)
    try:
        relative_path = os.path.normpath(os.path.relpath(absolute_path, os.getcwd()))
        if not relative_path.startswith("..") and not os.path.isabs(relative_path):
            return relative_path
    except ValueError:
        pass
    return raw_path


def _summary_persist_key(summary):
    trajectory_path = os.path.abspath(summary["trajectory_path"])
    try:
        modified_at = os.path.getmtime(trajectory_path)
    except OSError:
        modified_at = 0.0
    active_video = st.session_state.get("ruta_video_actual", "")
    selected_experiment_id = st.session_state.get("analysis_selected_experiment_id", "")
    return f"{selected_experiment_id}|{active_video}|{trajectory_path}|{modified_at:.6f}"


def persist_summary_to_db(summary):
    try:
        try:
            from db.connection import get_db_engine
            from sqlalchemy import text
        except Exception as error:
            return f"No se pudo cargar la capa DB: {error}"

        engine = get_db_engine()
        if not engine:
            return "No se encontro una conexion activa a PostgreSQL."

        video_path = st.session_state.get("ruta_video_actual")
        if not video_path:
            return "No hay video activo para registrar en BD."

        selected_experiment_id = st.session_state.get("analysis_selected_experiment_id")
        video_path_candidates = _video_path_variants(video_path)
        db_video_path = _stored_video_path(video_path)
        rat_id = st.session_state.get("id_raton_actual") or Path(video_path).stem
        treatment = st.session_state.get("treatment") or "Control"
        responsible = st.session_state.get("ingesta_responsable_actual") or st.session_state.get("user_name", "Investigador")
        username = st.session_state.get("user")

        with engine.connect() as conn:
            user_row = conn.execute(
                text("SELECT id FROM users WHERE username = :username LIMIT 1"),
                {"username": username},
            ).fetchone()
            user_id = int(user_row[0]) if user_row else None

            existing = None
            if selected_experiment_id:
                existing = conn.execute(
                    text("SELECT id FROM experiments WHERE id = :experiment_id LIMIT 1"),
                    {"experiment_id": int(selected_experiment_id)},
                ).fetchone()

            if existing is None and video_path_candidates:
                where_clause = " OR ".join(
                    f"video_path = :video_path_{idx}" for idx, _ in enumerate(video_path_candidates)
                )
                params = {
                    f"video_path_{idx}": candidate
                    for idx, candidate in enumerate(video_path_candidates)
                }
                existing = conn.execute(
                    text(
                        f"""
                        SELECT id
                        FROM experiments
                        WHERE {where_clause}
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    params,
                ).fetchone()

            if existing:
                experiment_id = int(existing[0])
                conn.execute(
                    text(
                        """
                        UPDATE experiments
                        SET treatment = :treatment,
                            experiment_date = CURRENT_DATE,
                            responsible = :responsible,
                            duration_seconds = :duration_seconds,
                            created_by = COALESCE(:created_by, created_by),
                            processed = TRUE
                        WHERE id = :experiment_id
                        """
                    ),
                    {
                        "treatment": treatment,
                        "responsible": responsible,
                        "duration_seconds": summary["total_duration"],
                        "created_by": user_id,
                        "experiment_id": experiment_id,
                    },
                )
            else:
                created = conn.execute(
                    text(
                        """
                        INSERT INTO experiments (
                            rat_id,
                            treatment,
                            experiment_date,
                            responsible,
                            video_path,
                            duration_seconds,
                            created_by,
                            processed
                        )
                        VALUES (
                            :rat_id,
                            :treatment,
                            CURRENT_DATE,
                            :responsible,
                            :video_path,
                            :duration_seconds,
                            :created_by,
                            TRUE
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "rat_id": rat_id,
                        "treatment": treatment,
                        "responsible": responsible,
                        "video_path": db_video_path,
                        "duration_seconds": summary["total_duration"],
                        "created_by": user_id,
                    },
                ).fetchone()
                experiment_id = int(created[0])

            conn.execute(text("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS trajectory_path TEXT"))
            conn.execute(
                text("DELETE FROM analysis_results WHERE experiment_id = :experiment_id"),
                {"experiment_id": experiment_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO analysis_results (
                        experiment_id,
                        total_distance,
                        time_open_arms,
                        time_closed_arms,
                        time_center,
                        grooming_duration,
                        thigmotaxis_duration,
                        status,
                        trajectory_path
                    )
                    VALUES (
                        :experiment_id,
                        0,
                        :time_open_arms,
                        :time_closed_arms,
                        :time_center,
                        :grooming_duration,
                        :thigmotaxis_duration,
                        'completed',
                        :trajectory_path
                    )
                    """
                ),
                {
                    "experiment_id": experiment_id,
                    "time_open_arms": summary["time_open_arms"],
                    "time_closed_arms": summary["time_closed_arms"],
                    "time_center": summary["time_center"],
                    "grooming_duration": summary["grooming_duration"],
                    "thigmotaxis_duration": summary["thigmotaxis_duration"],
                    "trajectory_path": summary["trajectory_path"],
                },
            )
            conn.commit()

        return f"Resumen persistido en BD para el experimento #{experiment_id}."
    except Exception as error:
        return f"Pipeline listo, pero no se pudo persistir el resumen en BD: {error}"


def render_status_panel():
    st.markdown("#### Estado y Logs")
    last_progress = float(st.session_state.get("analysis_last_progress", 0.0) or 0.0)
    last_status = st.session_state.get("analysis_last_status", "Aun no se ejecuta el pipeline final.")
    last_logs = st.session_state.get("analysis_last_logs", "[INFO] Aun no hay logs del pipeline.")

    st.progress(min(max(last_progress, 0.0), 1.0), text=last_status)
    st.code(last_logs, language="bash")


def render_loading_animation(message):
    """
    Renderiza una animación de carga con el logo del proyecto pulsando.
    """
    import base64
    logo_path = os.path.abspath(os.path.join("assets", "logos", "logo_ria.png"))
    
    # Convertir imagen a base64
    try:
        with open(logo_path, "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode()
        logo_src = f"data:image/png;base64,{logo_base64}"
    except:
        logo_src = ""  # Fallback si no se encuentra la imagen
    
    animation_html = f"""
    <style>
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.15); }}
        }}
        .loading-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background: white;
            border-radius: 8px;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .loading-logo {{
            width: 120px;
            height: 120px;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        .loading-message {{
            margin-top: 1.5rem;
            text-align: center;
            font-size: 1rem;
            font-weight: 500;
            color: #333;
            line-height: 1.6;
        }}
    </style>
    <div class="loading-container">
        <img src="{logo_src}" class="loading-logo" alt="Logo">
        <div class="loading-message">{message}</div>
    </div>
    """
    st.markdown(animation_html, unsafe_allow_html=True)


def inject_close_warning():
    """
    Inyecta JavaScript para advertir al usuario antes de cerrar/recargar la página
    cuando hay un proceso en ejecución.
    """
    warning_script = """
    <script>
        (function() {
            // Función que muestra advertencia
            function handleBeforeUnload(e) {
                var confirmationMessage = 'Hay un proceso de análisis final en ejecución. Si cierra o recarga la página, el proceso se detendrá y perderá el progreso. ¿Está seguro de que desea continuar?';
                
                // Método estándar moderno
                e.preventDefault();
                e.returnValue = confirmationMessage;
                
                // Método legacy para navegadores antiguos
                return confirmationMessage;
            }
            
            // Remover listeners previos si existen
            if (window.__streamlit_unload_listener) {
                window.removeEventListener('beforeunload', window.__streamlit_unload_listener);
                window.removeEventListener('unload', window.__streamlit_unload_listener);
            }
            
            // Agregar listeners para beforeunload (recargar/cerrar)
            window.__streamlit_unload_listener = handleBeforeUnload;
            window.addEventListener('beforeunload', handleBeforeUnload, {capture: true});
            
            // Asegurar que el usuario ha interactuado con la página
            document.addEventListener('click', function() {
                window.__user_has_interacted = true;
            }, {once: true});
            
            console.log('Advertencia de cierre/recarga activada');
        })();
    </script>
    """
    components.html(warning_script, height=0)


def remove_close_warning():
    """
    Remueve la advertencia de cierre cuando el proceso ha terminado.
    """
    remove_script = """
    <script>
        (function() {
            if (window.__streamlit_unload_listener) {
                window.removeEventListener('beforeunload', window.__streamlit_unload_listener, {capture: true});
                window.__streamlit_unload_listener = null;
                console.log('Advertencia de cierre/recarga removida');
            }
        })();
    </script>
    """
    components.html(remove_script, height=0)


def render_output_panel():
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Salidas generadas")

    final_video = st.session_state.get("ultimo_multimodal_video")
    if final_video and os.path.exists(final_video):
        st.video(final_video)
    else:
        st.info("Aun no existe un video multimodal final para este registro.")

    # Carpeta de resultados YOLO
    active_video = st.session_state.get("ruta_video_actual")
    if active_video:
        video_stem = Path(active_video).stem
        resultados_dir = os.path.abspath(os.path.join("resultados_yolo", video_stem))
        st.markdown("---")
        col_btn, col_path = st.columns([1, 1.5])
        with col_btn:
            if st.button("ABRIR CARPETA RESULTADOS", use_container_width=True, key="btn_open_resultados"):
                os.makedirs(resultados_dir, exist_ok=True)
                subprocess.Popen(["explorer", resultados_dir])
                st.toast(f"Abriendo: {resultados_dir}")
        with col_path:
            if os.path.exists(resultados_dir):
                archivos = [f for f in os.listdir(resultados_dir)]
                st.caption(f"`resultados_yolo/{video_stem}/` — {len(archivos)} archivo(s)")
                if final_video and os.path.exists(final_video):
                    st.code(final_video, language=None)
            else:
                st.caption(f"Los resultados se guardarán en `resultados_yolo/{video_stem}/`")

    generated_files = collect_generated_files()
    if generated_files:
        with st.expander("Ver todos los archivos detectados", expanded=False):
            for file_path in generated_files:
                st.code(file_path, language=None)

    summary = build_summary_from_trajectory(st.session_state.get("ultimo_trajectory_file"))
    if summary:
        persist_key = _summary_persist_key(summary)
        if st.session_state.get("analysis_persist_key") != persist_key:
            st.session_state["analysis_db_notice"] = persist_summary_to_db(summary)
            st.session_state["analysis_persist_key"] = persist_key
            save_session()

        st.markdown("---")
        st.markdown("##### Resumen rapido")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Abiertos", f"{summary['time_open_arms']:.1f}s")
        m2.metric("Cerrados", f"{summary['time_closed_arms']:.1f}s")
        m3.metric("Grooming", f"{summary['grooming_duration']:.1f}s")
        m4.metric("Thigmotaxis", f"{summary['thigmotaxis_duration']:.1f}s")

    db_notice = st.session_state.get("analysis_db_notice")
    if db_notice:
        st.caption(db_notice)
    st.markdown("</div>", unsafe_allow_html=True)


def resolve_status_flags():
    active_video = st.session_state.get("ruta_video_actual")
    analyzed_video = st.session_state.get("ultimo_video_analizado") or active_video
    pose_candidate = st.session_state.get("ultimo_pose_file") or find_pose_file(analyzed_video)
    feature_candidate = st.session_state.get("ultimo_feature_file") or find_feature_file(analyzed_video)
    final_video = st.session_state.get("ultimo_multimodal_video")

    return {
        "has_video": bool(active_video and os.path.exists(active_video)),
        "has_zonas": bool(st.session_state.get("zonas_configuradas")),
        "has_models": GROOMING_MODEL_YOLO.exists() and THIGMOTAXIS_MODEL_YOLO.exists(),
        "has_pose": bool(pose_candidate and os.path.exists(pose_candidate)),
        "has_features": bool(feature_candidate and os.path.exists(feature_candidate)),
        "has_final_video": bool(final_video and os.path.exists(final_video)),
    }


# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Modulo 04: Analisis Final Conductual")
st.markdown(
    """
    Ejecuta el flujo operativo completo del proyecto activo:
    YOLO Pose, SimBA, RF calibrado, rescate temporal LSTM para Grooming y render multimodal final.
    """
)
st.caption(
    "Recomendacion operativa: primero agrega y etiqueta videos nuevos en SimBA, luego reentrena los modelos, "
    "y por ultimo vuelve a correr aqui los videos historicos que quieras reprocesar con el modelo mejorado."
)

st.divider()

# ================= 3. VIDEO CHECK =================
video_ok = render_video_banner("Video de Analisis Activo")

history_records = fetch_reprocessable_experiments()
selected_history_record = None

st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("#### Reprocesar videos anteriores")
if history_records:
    history_options = {
        (
            f"#{record['id']} | {record.get('rat_id', 'Sin ID')} | "
            f"{record.get('experiment_date', 'Sin fecha')} | "
            f"{os.path.basename(record.get('video_path', ''))}"
        ): record
        for record in history_records
    }
    selected_history_label = st.selectbox(
        "Carga un experimento previo para volver a correrlo con los modelos y el pipeline actuales",
        list(history_options.keys()),
        key="analysis_previous_experiment_select",
    )
    selected_history_record = history_options[selected_history_label]
    history_cols = st.columns([1.4, 1])
    with history_cols[0]:
        inferred_start, inferred_end = infer_trim_window(selected_history_record)
        st.caption(
            f"Video: `{selected_history_record['video_path']}` | "
            f"Zonas guardadas: `{selected_history_record.get('zone_count', 0)}` | "
            f"Recorte inferido: `{format_mm_ss(inferred_start)}` -> "
            f"`{format_mm_ss(inferred_end) if inferred_end is not None else 'fin del video'}`"
        )
    with history_cols[1]:
        if st.button("CARGAR REGISTRO PREVIO", use_container_width=True, key="btn_load_previous_analysis_record"):
            ok, message = load_previous_experiment_context(selected_history_record)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
else:
    st.info("Aun no hay experimentos previos disponibles con video recuperable desde la BD.")
st.markdown("</div>", unsafe_allow_html=True)

if not video_ok:
    st.warning("No hay video activo en esta sesion. Puedes cargar uno desde Ingesta o usar el selector de registros previos de arriba.")

status_flags = resolve_status_flags()
device_option = st.session_state.get("dlc_device_opt", "Auto (Recomendado)")
batch_size = int(st.session_state.get("dlc_batch_size", 16) or 16)
zones_ready = bool(st.session_state.get("zonas_configuradas"))

# ================= 4. PREREQUISITES PANEL =================
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("#### Validacion de Prerrequisitos")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f'<div style="text-align:center;"><div style="color: {"#1E8E3E" if status_flags["has_video"] else "#D93025"}; font-weight: 700;">'
        f'{"OK Video Activo" if status_flags["has_video"] else "Sin Video Activo"}</div>'
        f'<div style="font-size:0.8rem; margin-top:8px;">Registro experimental</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div style="text-align:center;"><div style="color: {"#1E8E3E" if status_flags["has_zonas"] else "#D93025"}; font-weight: 700;">'
        f'{"ROIs Configuradas" if status_flags["has_zonas"] else "Faltan ROIs"}</div>'
        f'<div style="font-size:0.8rem; margin-top:8px;">Zonas normalizadas</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div style="text-align:center;"><div style="color: {"#1E8E3E" if status_flags["has_models"] else "#D93025"}; font-weight: 700;">'
        f'{"Modelos SimBA OK" if status_flags["has_models"] else "Modelos no hallados"}</div>'
        f'<div style="font-size:0.8rem; margin-top:8px;">Generated models</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    state_label = "Pose DLC lista" if status_flags["has_pose"] else "Se generara pose nueva"
    state_color = "#1E8E3E" if status_flags["has_pose"] else "#B26A00"
    st.markdown(
        f'<div style="text-align:center;"><div style="color: {state_color}; font-weight: 700;">{state_label}</div>'
        f'<div style="font-size:0.8rem; margin-top:8px;">Reuso inteligente</div></div>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

# ================= 5. MAIN LAYOUT =================
action = None
left_col, right_col = st.columns([1, 1.35])

with left_col:
    st.markdown('<div class="content-card" style="border-top: 4px solid #6F1D46;">', unsafe_allow_html=True)
    st.markdown("#### Ejecucion del Pipeline")
    st.caption(
        f"Rango activo: `{format_mm_ss(st.session_state.get('inicio_recorte', 0))}` -> "
        f"`{format_mm_ss(st.session_state.get('fin_recorte')) if st.session_state.get('fin_recorte') is not None else 'fin del video'}`"
    )

    with st.expander("Parametros de Ejecucion", expanded=True):
        batch_size = st.slider(
            "Batch Size DLC",
            min_value=4,
            max_value=32,
            value=int(st.session_state.get("dlc_batch_size", 16) or 16),
            step=4,
            help="Se mantiene capado a 32 para no castigar la GPU. 16 suele ser el punto mas estable.",
        )
        device_option = st.selectbox(
            "Dispositivo Hardware",
            ["Auto (Recomendado)", "CPU (Forzar)"],
            index=0 if st.session_state.get("dlc_device_opt", "Auto (Recomendado)") == "Auto (Recomendado)" else 1,
        )
        st.caption("Grooming usa RF calibrado con rescate temporal LSTM cuando el RF queda en zona gris.")
        st.caption("El pipeline reutiliza pose, features, LSTM y video final si ya existen y siguen vigentes.")

    can_run = status_flags["has_video"] and status_flags["has_zonas"] and status_flags["has_models"]
    if not status_flags["has_zonas"]:
        st.error("Necesitas guardar primero las ROIs en el Modulo 03.")
    if not status_flags["has_models"]:
        st.error("No se encontraron los modelos activos de SimBA en generated_models.")

    analysis_snapshot = get_analysis_snapshot()
    if analysis_snapshot["needs_rerun"]:
        st.rerun()
    if st.session_state.pop("analysis_show_toast", False):
        st.toast("Pipeline multimodal completado. Revisa el panel de salida.")

    pipeline_running = analysis_snapshot["is_running"]

    if pipeline_running:
        st.info("El pipeline corre en segundo plano. Puedes moverte entre módulos y volver.")
        col_stop, col_log = st.columns(2)
        with col_stop:
            if st.button("DETENER PIPELINE", use_container_width=True, key="btn_stop_analysis"):
                action = "cancel"
        with col_log:
            if st.button("ABRIR CONSOLA DE LOGS", use_container_width=True, key="btn_log_analysis"):
                action = "open_console"
        if analysis_snapshot["meta"]:
            st.caption(f"PID activo: `{analysis_snapshot['meta'].get('pid')}`")
    else:
        if st.button(
            "INICIAR PIPELINE MULTIMODAL",
            type="primary",
            use_container_width=True,
            disabled=not can_run,
            key="btn_run_behavior_pipeline",
        ):
            action = "run"
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    render_output_panel()

# ================= 6. ESTADO Y LOGS =================
st.markdown("<br>", unsafe_allow_html=True)

if action == "run":
    st.session_state["dlc_batch_size"] = int(batch_size)
    save_session()
    zones_file = write_zones_temp_file()
    analysis_log_path = os.path.join(ensure_logs_dir(), "analysis_pipeline.log")
    launch_background_analysis(
        build_pipeline_command(batch_size, device_option, zones_file),
        analysis_log_path,
    )
    st.rerun()

elif action == "cancel":
    cancel_background_analysis(analysis_snapshot["meta"])
    st.rerun()

elif action == "open_console":
    powershell = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"), "System32",
        "WindowsPowerShell", "v1.0", "powershell.exe",
    )
    log_path = analysis_snapshot["log_path"]
    safe_path = os.path.abspath(log_path).replace("'", "''")
    subprocess.Popen(
        [powershell, "-NoExit", "-Command",
         f"$host.UI.RawUI.WindowTitle='TT 2026 - Analisis Final'; Get-Content -Path '{safe_path}' -Wait -Tail 40"],
        cwd=os.getcwd(),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )
    st.toast("Se abrió consola de logs.")


@st.fragment(run_every="2s" if analysis_snapshot.get("is_running") else None)
def render_analysis_monitor():
    snap = get_analysis_snapshot()
    progress = float(snap.get("progress", 0.0) or 0.0)
    status = snap.get("status", "")
    logs = trim_log_text(snap.get("lines", []), max_lines=220)
    is_running = snap.get("is_running", False)
    
    # Mostrar animación si el proceso está corriendo
    if is_running and progress < 0.95:
        render_loading_animation(
            "El análisis final está en proceso.<br>"
            "Por favor no cierre la ventana ni recargue la página.<br>"
            "Tampoco cierre la ventana de consola. Espere a que se complete."
        )
    
    st.progress(min(max(progress, 0.0), 1.0), text=status)
    st.code(logs, language="bash")
    if snap["needs_rerun"]:
        st.rerun()


# Inyectar o remover advertencia de cierre según el estado del proceso (fuera del fragmento)
if analysis_snapshot.get("is_running") and float(analysis_snapshot.get("progress", 0.0) or 0.0) < 0.95:
    inject_close_warning()
else:
    remove_close_warning()

render_analysis_monitor()

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
