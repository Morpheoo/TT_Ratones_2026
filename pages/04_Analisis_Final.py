import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

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
from config import GROOMING_MODEL, SIMBA_BASE, SIMBA_PROJECT_DIR, THIGMOTAXIS_MODEL

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
        elif "[STEP] BBOX" in line:
            progress = max(progress, 0.46)
            status = "Aplicando filtro anatomico bbox..."
        elif "[STEP] SIMBA_FEATURES" in line:
            progress = max(progress, 0.68)
            status = "Importando pose al proyecto SimBA..."
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
    st.session_state["analysis_last_logs"] = trim_log_text(lines, max_lines=220)
    st.session_state["analysis_last_status"] = final_status
    st.session_state["analysis_last_progress"] = final_progress

    return return_code, lines, outputs


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
        "ultimo_thigmotaxis_timelog",
        "analysis_db_notice",
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
        str(Path(SIMBA_BASE).resolve()),
        "--batch-size",
        str(int(batch_size)),
        "--start-seconds",
        str(start_seconds),
    ]
    if end_seconds is not None:
        command.extend(["--end-seconds", str(int(end_seconds))])
    if zones_file:
        command.extend(["--zones-file", zones_file])
    if device_option == "CPU (Forzar)":
        command.append("--force-cpu")
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

            existing = conn.execute(
                text("SELECT id FROM experiments WHERE video_path = :video_path ORDER BY created_at DESC LIMIT 1"),
                {"video_path": video_path},
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
                        "video_path": video_path,
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


def render_output_panel():
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Salidas generadas")

    final_video = st.session_state.get("ultimo_multimodal_video")
    if final_video and os.path.exists(final_video):
        st.video(final_video)
    else:
        st.info("Aun no existe un video multimodal final para este registro.")

    generated_files = collect_generated_files()
    if generated_files:
        st.markdown("##### Archivos detectados")
        for file_path in generated_files:
            st.write(f"- `{os.path.basename(file_path)}`")

    summary = build_summary_from_trajectory(st.session_state.get("ultimo_trajectory_file"))
    if summary:
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
        "has_models": GROOMING_MODEL.exists() and THIGMOTAXIS_MODEL.exists(),
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
    recorte temporal, DeepLabCut, filtro bbox, importacion a SimBA y render multimodal final.
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
        st.caption("El pipeline reutiliza pose, filtro bbox y video final si ya existen y siguen vigentes.")

    can_run = status_flags["has_video"] and status_flags["has_zonas"] and status_flags["has_models"]
    if not status_flags["has_zonas"]:
        st.error("Necesitas guardar primero las ROIs en el Modulo 03.")
    if not status_flags["has_models"]:
        st.error("No se encontraron los modelos activos de SimBA en generated_models.")

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
    st.session_state["dlc_device_opt"] = device_option
    zones_file = write_zones_temp_file()
    save_session()

    analysis_log_path = os.path.join(ensure_logs_dir(), "analysis_pipeline.log")
    return_code, lines, outputs = run_logged_process(
        command=build_pipeline_command(batch_size, device_option, zones_file),
        log_path=analysis_log_path,
        parser=parse_pipeline_progress,
        success_status="Pipeline multimodal completado.",
        error_status="El pipeline multimodal termino con error.",
    )

    if return_code == 0:
        output_map = {
            "analyzed_video": "ultimo_video_analizado",
            "raw_pose_file": "ultimo_pose_file",
            "filtered_pose": "ultimo_pose_filtrado",
            "filtered_pose_file": "ultimo_pose_filtrado",
            "bbox_video": "ultimo_bbox_video",
            "bbox_validation_video": "ultimo_bbox_video",
            "feature_csv": "ultimo_feature_file",
            "final_feature_csv": "ultimo_feature_file",
            "multimodal_video": "ultimo_multimodal_video",
            "final_video": "ultimo_multimodal_video",
            "trajectory_file": "ultimo_trajectory_file",
            "final_trajectory": "ultimo_trajectory_file",
            "grooming_timelog": "ultimo_grooming_timelog",
            "final_grooming_timelog": "ultimo_grooming_timelog",
            "thigmotaxis_timelog": "ultimo_thigmotaxis_timelog",
            "final_thigmotaxis_timelog": "ultimo_thigmotaxis_timelog",
        }
        for output_key, session_key in output_map.items():
            candidate = outputs.get(output_key)
            if candidate and os.path.exists(candidate):
                st.session_state[session_key] = candidate

        if st.session_state.get("ultimo_pose_filtrado"):
            st.session_state["ultimo_pose_file"] = st.session_state["ultimo_pose_filtrado"]

        summary = build_summary_from_trajectory(st.session_state.get("ultimo_trajectory_file"))
        if summary:
            st.session_state["analysis_db_notice"] = persist_summary_to_db(summary)

        save_session()
        st.rerun()

render_status_panel()

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
