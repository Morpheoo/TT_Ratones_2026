import os
import sys
from pathlib import Path
import json
from datetime import datetime
from io import BytesIO

import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import bindparam, text

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session
from ui_components import load_resource_with_splash
import importlib
import ui_theme

importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar, inject_sidebar_profile

st.set_page_config(page_title="Resultados | IPN - ESCOM", page_icon="assets/logos/logo_ria.png", layout="wide")

load_session()
colors = use_theme()

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

# ============================================================
# Paleta institucional IPN-ESCOM unificada
# Guinda como ancla, complementos elegidos para distinguir
# zonas espaciales (rectas/sobrias) vs conductas (frio/calido).
# ============================================================
IPN_GUINDA = "#6A1B3F"          # Guinda principal — Brazos Abiertos
IPN_CARBON = "#2B2D2F"          # Negro mate — Brazos Cerrados
IPN_CORAL = "#E07A5F"           # Coral — Centro / acentos calidos
IPN_GRIS = "#888888"            # Gris neutro — categoria descartada
IPN_AZUL_PETROLEO = "#2C5F7A"   # Azul frio — Grooming (calma)
IPN_NARANJA_QUEMADO = "#D2691E" # Naranja calido — Thigmotaxis (alerta)

ACCENT_COLOR = IPN_CORAL
ZONE_CATEGORY_COLORS = {
    "Abiertos": IPN_GUINDA,
    "Cerrados": IPN_CARBON,
    "Centro": IPN_CORAL,
    "Fuera": IPN_GRIS,
}
BEHAVIOR_COLORS = {
    "Grooming": IPN_AZUL_PETROLEO,
    "Thigmotaxis": IPN_NARANJA_QUEMADO,
    "Grooming acumulado": IPN_AZUL_PETROLEO,
    "Thigmotaxis acumulado": IPN_NARANJA_QUEMADO,
}
# Mapping para el chart "Comparativa rapida" donde cada barra es una metrica.
GLOBAL_METRIC_COLORS = {
    "Brazos abiertos": IPN_GUINDA,
    "Brazos cerrados": IPN_CARBON,
    "Grooming": IPN_AZUL_PETROLEO,
    "Thigmotaxis": IPN_NARANJA_QUEMADO,
}


def format_seconds(value):
    try:
        seconds = float(value or 0.0)
    except (TypeError, ValueError):
        seconds = 0.0
    return f"{seconds:.1f}s"


def safe_float(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def normalize_dataframe_for_streamlit(df):
    if df.empty:
        return df

    import datetime as dt

    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna()
            if not sample.empty and isinstance(sample.iloc[0], (dt.date, dt.datetime)):
                df[col] = df[col].astype(str)
        elif hasattr(df[col].dtype, "name") and any(token in df[col].dtype.name for token in ("date", "time")):
            df[col] = df[col].astype(str)
    return df


def get_latest_completed_id(df):
    if df.empty or "id" not in df.columns:
        return None

    status_series = df.get("analysis_status", pd.Series([""] * len(df))).astype(str).str.lower()
    completed = df[status_series == "completed"].copy()
    candidates = completed if not completed.empty else df.copy()
    candidates["id"] = pd.to_numeric(candidates["id"], errors="coerce")
    candidates = candidates.dropna(subset=["id"])
    if candidates.empty:
        return None
    return int(candidates["id"].max())


def filter_history_scope(df_hist, scope):
    if df_hist.empty:
        return df_hist

    if scope == "Ultimo completado":
        latest_completed_id = get_latest_completed_id(df_hist)
        if latest_completed_id is None:
            return df_hist.iloc[0:0].copy()
        return df_hist[pd.to_numeric(df_hist["id"], errors="coerce") == latest_completed_id].copy()
    if scope == "Completados":
        return df_hist[df_hist["analysis_status"].astype(str).str.lower() == "completed"].copy()
    if scope == "Pendientes":
        return df_hist[df_hist["analysis_status"].astype(str).str.lower() == "pending"].copy()
    return df_hist.copy()


def apply_plot_style(fig, *, height=360, show_y_grid=True):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Inter, sans-serif", color=colors["text_main"]),
        paper_bgcolor=colors["bg_card"],
        plot_bgcolor=colors["bg_card"],
        legend_title=None,
        hoverlabel=dict(bgcolor=colors["bg_card"], font=dict(color=colors["text_main"])),
    )
    fig.update_xaxes(showgrid=False, linecolor=colors["border"], tickfont=dict(color=colors["text_main"]))
    fig.update_yaxes(
        showgrid=show_y_grid,
        gridcolor=colors["border"],
        zerolinecolor=colors["border"],
        tickfont=dict(color=colors["text_main"]),
    )
    return fig


def results_loading_sequence():
    yield 30, "Estableciendo conexion persistente..."
    from db.connection import get_db_engine

    engine = get_db_engine()
    yield 100, "Sincronizacion de registros exitosa."
    return engine


def ensure_analysis_results_schema(conn):
    conn.execute(text("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS trajectory_path TEXT"))
    conn.commit()


def load_history_dataframe(engine):
    if not engine:
        return pd.DataFrame()

    with engine.connect() as conn:
        ensure_analysis_results_schema(conn)
        query = text(
            """
            SELECT
                e.id,
                e.rat_id,
                e.treatment,
                e.experiment_date,
                e.responsible,
                e.video_path,
                e.created_by,
                e.created_at,
                COALESCE(ar.time_open_arms, 0) AS open_t,
                COALESCE(ar.time_closed_arms, 0) AS closed_t,
                COALESCE(ar.time_center, 0) AS center_t,
                COALESCE(ar.grooming_duration, 0) AS grooming_t,
                COALESCE(ar.thigmotaxis_duration, 0) AS thigmo_t,
                COALESCE(ar.status, CASE WHEN e.processed THEN 'completed' ELSE 'pending' END) AS analysis_status,
                COALESCE(ar.trajectory_path, '') AS trajectory_path,
                COALESCE(u.username, '') AS owner_email
            FROM experiments e
            LEFT JOIN (
                SELECT DISTINCT ON (experiment_id)
                    experiment_id,
                    time_open_arms,
                    time_closed_arms,
                    time_center,
                    grooming_duration,
                    thigmotaxis_duration,
                    status,
                    trajectory_path,
                    timestamp,
                    id
                FROM analysis_results
                ORDER BY experiment_id, timestamp DESC, id DESC
            ) ar
                ON ar.experiment_id = e.id
            LEFT JOIN users u
                ON e.created_by = u.id
            ORDER BY e.created_at DESC
            """
        )
        df_hist = pd.read_sql(query, conn)

    return normalize_dataframe_for_streamlit(df_hist)


def delete_owned_experiments(engine, experiment_ids, username):
    experiment_ids = sorted({int(exp_id) for exp_id in experiment_ids if int(exp_id) > 0})
    if not experiment_ids:
        return 0, [], "No hay experimentos validos seleccionados para borrar."
    if not username:
        return 0, experiment_ids, "No se encontró el usuario activo en sesión."

    select_query = text(
        """
        SELECT
            e.id,
            COALESCE(u.username, '') AS owner_email
        FROM experiments e
        LEFT JOIN users u
            ON e.created_by = u.id
        WHERE e.id IN :experiment_ids
        """
    ).bindparams(bindparam("experiment_ids", expanding=True))

    delete_query = text(
        """
        DELETE FROM experiments
        WHERE id IN :experiment_ids
          AND created_by = (
              SELECT id
              FROM users
              WHERE username = :username
              LIMIT 1
          )
        """
    ).bindparams(bindparam("experiment_ids", expanding=True))

    with engine.connect() as conn:
        rows = conn.execute(select_query, {"experiment_ids": experiment_ids}).mappings().all()
        owned_ids = [int(row["id"]) for row in rows if row["owner_email"] == username]
        skipped_ids = [exp_id for exp_id in experiment_ids if exp_id not in owned_ids]

        deleted_count = 0
        if owned_ids:
            result = conn.execute(
                delete_query,
                {
                    "experiment_ids": owned_ids,
                    "username": username,
                },
            )
            deleted_count = int(result.rowcount or 0)
        conn.commit()

    return deleted_count, skipped_ids, ""


def update_experiment_times(engine, experiment_id, open_t, closed_t, center_t,
                            grooming_t, thigmo_t,
                            user_email=None, user_role=None, note=None):
    """
    Actualiza los tiempos de un experimento en analysis_results y registra
    un snapshot before/after en behavior_edits para auditoria.
    Solo administradores e investigadores deben invocarla.
    """
    if not engine:
        return False, "No hay conexión a la base de datos"

    from db.behavior_edits import ensure_behavior_edits_schema, fetch_user_id_by_email

    try:
        with engine.connect() as conn:
            ensure_behavior_edits_schema(conn)

            # Snapshot del estado anterior (puede no existir aun).
            before_row = conn.execute(
                text(
                    """
                    SELECT id, time_open_arms, time_closed_arms, time_center,
                           grooming_duration, thigmotaxis_duration
                    FROM analysis_results
                    WHERE experiment_id = :exp_id
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                ),
                {"exp_id": experiment_id},
            ).mappings().fetchone()

            if before_row:
                before = {
                    "open":  float(before_row["time_open_arms"] or 0.0),
                    "closed": float(before_row["time_closed_arms"] or 0.0),
                    "center": float(before_row["time_center"] or 0.0),
                    "grooming": float(before_row["grooming_duration"] or 0.0),
                    "thigmo":  float(before_row["thigmotaxis_duration"] or 0.0),
                }
                conn.execute(
                    text(
                        """
                        UPDATE analysis_results
                        SET time_open_arms = :open_t,
                            time_closed_arms = :closed_t,
                            time_center = :center_t,
                            grooming_duration = :grooming_t,
                            thigmotaxis_duration = :thigmo_t,
                            timestamp = CURRENT_TIMESTAMP
                        WHERE id = :analysis_id
                        """
                    ),
                    {
                        "open_t": float(open_t),
                        "closed_t": float(closed_t),
                        "center_t": float(center_t),
                        "grooming_t": float(grooming_t),
                        "thigmo_t": float(thigmo_t),
                        "analysis_id": int(before_row["id"]),
                    },
                )
            else:
                before = {"open": 0.0, "closed": 0.0, "center": 0.0,
                          "grooming": 0.0, "thigmo": 0.0}
                conn.execute(
                    text(
                        """
                        INSERT INTO analysis_results
                        (experiment_id, time_open_arms, time_closed_arms, time_center,
                         grooming_duration, thigmotaxis_duration, status)
                        VALUES (:exp_id, :open_t, :closed_t, :center_t,
                                :grooming_t, :thigmo_t, 'completed')
                        """
                    ),
                    {
                        "exp_id": experiment_id,
                        "open_t": float(open_t),
                        "closed_t": float(closed_t),
                        "center_t": float(center_t),
                        "grooming_t": float(grooming_t),
                        "thigmo_t": float(thigmo_t),
                    },
                )

            after = {
                "open": float(open_t),
                "closed": float(closed_t),
                "center": float(center_t),
                "grooming": float(grooming_t),
                "thigmo": float(thigmo_t),
            }
            user_id = fetch_user_id_by_email(conn, user_email)
            conn.execute(
                text(
                    """
                    INSERT INTO behavior_edits (
                        experiment_id, edited_by, edited_by_email, edited_role,
                        before_open, before_closed, before_center,
                        before_grooming, before_thigmo,
                        after_open,  after_closed,  after_center,
                        after_grooming,  after_thigmo,
                        note
                    ) VALUES (
                        :exp_id, :user_id, :user_email, :user_role,
                        :b_open, :b_closed, :b_center, :b_groom, :b_thigmo,
                        :a_open, :a_closed, :a_center, :a_groom, :a_thigmo,
                        :note
                    )
                    """
                ),
                {
                    "exp_id": int(experiment_id),
                    "user_id": user_id,
                    "user_email": user_email,
                    "user_role": user_role,
                    "b_open": before["open"], "b_closed": before["closed"],
                    "b_center": before["center"],
                    "b_groom": before["grooming"], "b_thigmo": before["thigmo"],
                    "a_open": after["open"],  "a_closed": after["closed"],
                    "a_center": after["center"],
                    "a_groom": after["grooming"],  "a_thigmo": after["thigmo"],
                    "note": note,
                },
            )
            conn.commit()
            return True, "Tiempos actualizados y registrados en historial"
    except Exception as e:
        return False, f"Error al actualizar tiempos: {str(e)}"


def build_session_fallback_dataframe():
    trajectory_path = st.session_state.get("ultimo_trajectory_file")
    video_path = st.session_state.get("ruta_video_actual")
    if not trajectory_path or not os.path.exists(trajectory_path):
        return pd.DataFrame()

    rat_id = st.session_state.get("id_raton_actual") or (Path(video_path).stem if video_path else "sesion_actual")
    treatment = st.session_state.get("treatment") or "Control"
    responsible = st.session_state.get("ingesta_responsable_actual") or st.session_state.get("user_name", "Investigador")
    bundle = load_trajectory_bundle(trajectory_path)
    summary = bundle["summary"] if bundle else {}

    return pd.DataFrame(
        [
            {
                "id": 0,
                "rat_id": rat_id,
                "treatment": treatment,
                "experiment_date": str(pd.Timestamp.now().date()),
                "responsible": responsible,
                "video_path": video_path or "",
                "created_by": None,
                "created_at": str(pd.Timestamp.now()),
                "open_t": float(summary.get("open_t", 0.0)),
                "closed_t": float(summary.get("closed_t", 0.0)),
                "center_t": float(summary.get("center_t", 0.0)),
                "grooming_t": float(summary.get("grooming_t", 0.0)),
                "thigmo_t": float(summary.get("thigmo_t", 0.0)),
                "analysis_status": "completed",
                "trajectory_path": trajectory_path,
                "owner_email": st.session_state.get("user", ""),
            }
        ]
    )


def resolve_trajectory_path(record):
    candidates = []

    trajectory_path = str(record.get("trajectory_path", "") or "").strip()
    if trajectory_path:
        candidates.append(trajectory_path)

    session_trajectory = st.session_state.get("ultimo_trajectory_file")
    if session_trajectory:
        candidates.append(session_trajectory)

    video_path = str(record.get("video_path", "") or "").strip()
    if video_path:
        video_file = Path(video_path)
        if video_file.exists():
            candidates.append(str(video_file.with_name(video_file.stem + "_STREAMLIT_MULTIMODAL_trajectory.csv")))
            candidates.extend(str(path.resolve()) for path in sorted(video_file.parent.glob(f"{video_file.stem}*STREAMLIT_MULTIMODAL_trajectory.csv")))

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)
    return None


def load_trajectory_bundle(trajectory_path):
    if not trajectory_path or not os.path.exists(trajectory_path):
        return None

    df = pd.read_csv(trajectory_path)
    if df.empty or "Tiempo (s)" not in df.columns:
        return None

    df = df.copy()
    df["Tiempo (s)"] = pd.to_numeric(df["Tiempo (s)"], errors="coerce").fillna(0.0)
    if "Grooming" in df.columns:
        df["Grooming"] = pd.to_numeric(df["Grooming"], errors="coerce").fillna(0.0)
    else:
        df["Grooming"] = 0.0
    if "Thigmotaxis" in df.columns:
        df["Thigmotaxis"] = pd.to_numeric(df["Thigmotaxis"], errors="coerce").fillna(0.0)
    else:
        df["Thigmotaxis"] = 0.0

    if "Zona" not in df.columns:
        df["Zona"] = "Ninguna"
    df["Zona"] = df["Zona"].fillna("Ninguna").astype(str)

    if "x" not in df.columns:
        df["x"] = 0
    if "y" not in df.columns:
        df["y"] = 0

    step_seconds = df["Tiempo (s)"].diff().dropna()
    step_seconds = step_seconds[step_seconds > 0]
    frame_seconds = float(step_seconds.median()) if not step_seconds.empty else (1.0 / 30.0)

    zone_counts = df["Zona"].value_counts(dropna=False).sort_index()
    zone_seconds = (zone_counts * frame_seconds).reset_index()
    zone_seconds.columns = ["Zona", "Segundos"]
    zone_seconds["Categoria"] = zone_seconds["Zona"].apply(classify_zone_bucket)

    summary = {
        "open_t": float(zone_seconds.loc[zone_seconds["Categoria"] == "Abiertos", "Segundos"].sum()),
        "closed_t": float(zone_seconds.loc[zone_seconds["Categoria"] == "Cerrados", "Segundos"].sum()),
        "center_t": float(zone_seconds.loc[zone_seconds["Categoria"] == "Centro", "Segundos"].sum()),
        "grooming_t": float(df["Grooming"].sum() * frame_seconds),
        "thigmo_t": float(df["Thigmotaxis"].sum() * frame_seconds),
        "duration_t": float(len(df) * frame_seconds),
    }

    timeline = df[["Tiempo (s)", "Grooming", "Thigmotaxis"]].copy()
    timeline["Grooming acumulado"] = timeline["Grooming"].cumsum() * frame_seconds
    timeline["Thigmotaxis acumulado"] = timeline["Thigmotaxis"].cumsum() * frame_seconds

    if len(timeline) > 1800:
        timeline = timeline.iloc[:: max(len(timeline) // 1800, 1)].copy()

    heatmap_df = df[["x", "y", "Zona"]].copy()
    heatmap_df["x"] = pd.to_numeric(heatmap_df["x"], errors="coerce")
    heatmap_df["y"] = pd.to_numeric(heatmap_df["y"], errors="coerce")
    heatmap_df = heatmap_df.dropna(subset=["x", "y"])
    heatmap_df = heatmap_df[(heatmap_df["x"] > 0) & (heatmap_df["y"] > 0)]
    if len(heatmap_df) > 4500:
        heatmap_df = heatmap_df.iloc[:: max(len(heatmap_df) // 4500, 1)].copy()

    heatmap_width = int(max(1280, heatmap_df["x"].max() + 24)) if not heatmap_df.empty else 1280
    heatmap_height = int(max(720, heatmap_df["y"].max() + 24)) if not heatmap_df.empty else 720

    return {
        "trajectory_path": trajectory_path,
        "frame_seconds": frame_seconds,
        "zone_seconds": zone_seconds.sort_values("Segundos", ascending=False).reset_index(drop=True),
        "timeline": timeline,
        "heatmap": heatmap_df,
        "heatmap_width": heatmap_width,
        "heatmap_height": heatmap_height,
        "summary": summary,
    }


def classify_zone_bucket(zone_name):
    zone = str(zone_name or "").strip().lower()
    if "abierto" in zone:
        return "Abiertos"
    if "cerrado" in zone:
        return "Cerrados"
    if "centro" in zone:
        return "Centro"
    return "Fuera"


def build_distribution_dataframe(metrics):
    return pd.DataFrame(
        [
            {"Categoria": "Abiertos", "Segundos": metrics["open_t"]},
            {"Categoria": "Cerrados", "Segundos": metrics["closed_t"]},
            {"Categoria": "Centro", "Segundos": metrics["center_t"]},
        ]
    )


def coalesce_metric(record, summary, key):
    # El DB (analysis_results) es la fuente de verdad: refleja el output
    # del pipeline Y cualquier edicion manual posterior. El bundle del CSV
    # de trayectoria solo se usa como fallback cuando el DB todavía no tiene
    # valor (registros legacy o sin procesar).
    db_value = record.get(key)
    if db_value is not None and str(db_value) != "":
        return safe_float(db_value)
    if summary and summary["summary"].get(key) is not None:
        return safe_float(summary["summary"][key])
    return 0.0


def _read_video_background_frame(video_path, width, height):
    """Devuelve un frame BGR del video escalado a (width, height), o None si no se puede."""
    if not video_path:
        return None
    if not os.path.exists(video_path):
        return None
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        target = max(0, total_frames // 2 - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok or frame is None:
            return None
        if frame.shape[1] != int(width) or frame.shape[0] != int(height):
            frame = cv2.resize(frame, (int(width), int(height)), interpolation=cv2.INTER_AREA)
        return frame
    finally:
        cap.release()


def build_opencv_heatmap_image(heatmap_df, width, height, video_path=None):
    if heatmap_df is None or heatmap_df.empty:
        return None

    canvas = np.zeros((int(height), int(width)), dtype=np.float32)
    for row in heatmap_df.itertuples(index=False):
        x = int(round(float(row.x)))
        y = int(round(float(row.y)))
        if 0 <= x < width and 0 <= y < height:
            canvas[y, x] += 1.0

    if float(canvas.max()) <= 0:
        return None

    blurred = cv2.GaussianBlur(canvas, (0, 0), sigmaX=29, sigmaY=29)
    normalized = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_PLASMA)

    background = _read_video_background_frame(video_path, width, height)
    if background is None:
        # Fallback: fondo gris plano si el video no esta accesible.
        background = np.full((int(height), int(width), 3), 246, dtype=np.uint8)
        background[:] = (245, 244, 246)
    else:
        # Atenuar el frame para que no compita visualmente con el heatmap.
        background = cv2.addWeighted(background, 0.55, np.zeros_like(background), 0.0, 0)

    # Mezclar heatmap sobre el frame: alpha proporcional a la intensidad.
    alpha = (normalized.astype(np.float32) / 255.0)[..., None]
    blended = (background.astype(np.float32) * (1.0 - alpha) + colored.astype(np.float32) * alpha)
    blended = blended.clip(0, 255).astype(np.uint8)
    return cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)


def build_plasma_colorbar(width=480, height=36):
    """Barra horizontal con el colormap PLASMA para mostrar como leyenda."""
    gradient = np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1))
    colored = cv2.applyColorMap(gradient, cv2.COLORMAP_PLASMA)
    return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)


def render_global_kpis(df_hist):
    m1, m2, m3, m4 = st.columns(4)
    open_mean = df_hist["open_t"].mean() if not df_hist.empty and "open_t" in df_hist.columns else 0.0
    grooming_mean = df_hist["grooming_t"].mean() if not df_hist.empty and "grooming_t" in df_hist.columns else 0.0

    with m1:
        st.metric("Total experimentos", len(df_hist))
    with m2:
        latest_date = str(df_hist["experiment_date"].max()) if not df_hist.empty and "experiment_date" in df_hist.columns else "N/A"
        st.metric("Último registro", latest_date)
    with m3:
        st.metric("Prom. abiertos", format_seconds(open_mean))
    with m4:
        st.metric("Prom. grooming", format_seconds(grooming_mean))


def render_global_chart(df_view):
    st.markdown("#### Comparativa rápida")
    chart_df = df_view.copy()
    chart_df["Registro"] = chart_df.apply(
        lambda row: f"#{row['id']} | {row['rat_id']}",
        axis=1,
    )
    melted = chart_df.melt(
        id_vars=["Registro"],
        value_vars=["open_t", "closed_t", "grooming_t", "thigmo_t"],
        var_name="Metrica",
        value_name="Segundos",
    )
    melted["Metrica"] = melted["Metrica"].map(
        {
            "open_t": "Brazos abiertos",
            "closed_t": "Brazos cerrados",
            "grooming_t": "Grooming",
            "thigmo_t": "Thigmotaxis",
        }
    )
    fig = px.bar(
        melted,
        x="Registro",
        y="Segundos",
        color="Metrica",
        barmode="group",
        color_discrete_map=GLOBAL_METRIC_COLORS,
    )
    fig.update_traces(marker_line_color=colors["bg_card"], marker_line_width=1.2)
    apply_plot_style(fig, height=360)
    selected_signature = "_".join(str(exp_id) for exp_id in df_view["id"].astype(int).tolist())
    st.plotly_chart(fig, use_container_width=True, key=f"global_chart_{selected_signature}")


def generate_experiments_csv(df_experiments):
    """
    Genera un archivo CSV con los datos de experimentos seleccionados.
    """
    # Seleccionar y renombrar columnas relevantes
    export_df = df_experiments[[
        'id', 'rat_id', 'treatment', 'experiment_date', 'responsible',
        'open_t', 'closed_t', 'center_t', 'grooming_t', 'thigmo_t',
        'analysis_status', 'owner_email', 'created_at'
    ]].copy()
    
    export_df.columns = [
        'ID Experimento', 'ID Ratón', 'Tratamiento', 'Fecha Experimento', 'Responsable',
        'Tiempo Brazos Abiertos (s)', 'Tiempo Brazos Cerrados (s)', 'Tiempo Centro (s)',
        'Grooming (s)', 'Thigmotaxis (s)', 'Estado Análisis', 'Creado Por', 'Fecha Creación'
    ]
    
    # Agregar BOM UTF-8 para compatibilidad con Excel y reconocimiento de acentos
    return export_df.to_csv(index=False).encode('utf-8-sig')


def generate_experiments_json(df_experiments):
    """
    Genera un archivo JSON con los datos de experimentos seleccionados.
    """
    # Convertir a formato JSON amigable
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "total_experiments": len(df_experiments),
            "system": "Prototipo EPM - Análisis de Comportamiento Animal",
            "institution": "IPN - ESCOM - TT 2026"
        },
        "experiments": []
    }
    
    for _, row in df_experiments.iterrows():
        experiment = {
            "id": int(row['id']),
            "rat_id": str(row['rat_id']),
            "treatment": str(row['treatment']),
            "experiment_date": str(row['experiment_date']),
            "responsible": str(row['responsible']),
            "results": {
                "time_open_arms_seconds": float(row['open_t']),
                "time_closed_arms_seconds": float(row['closed_t']),
                "time_center_seconds": float(row['center_t']),
                "grooming_duration_seconds": float(row['grooming_t']),
                "thigmotaxis_duration_seconds": float(row['thigmo_t'])
            },
            "metadata": {
                "analysis_status": str(row['analysis_status']),
                "created_by": str(row.get('owner_email', '')),
                "created_at": str(row.get('created_at', ''))
            }
        }
        export_data["experiments"].append(experiment)
    
    return json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')


def generate_experiments_pdf(df_experiments):
    """
    Genera un archivo PDF con los datos de experimentos seleccionados.
    Usa reportlab para crear un reporte profesional.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch
    except ImportError as e:
        return generate_experiments_html_as_pdf(df_experiments)
    
    if df_experiments is None or df_experiments.empty:
        return b""
    
    buffer = BytesIO()
    
    try:
        # Crear documento
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título simple
        elements.append(Paragraph("Prototipo de Análisis EPM", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Instituto Politecnico Nacional - ESCOM", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Reporte: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Tabla de datos
        table_data = [['ID', 'Raton', 'Tratamiento', 'Fecha', 'Abiertos', 'Cerrados', 'Grooming', 'Thigmo']]
        
        for _, row in df_experiments.iterrows():
            table_data.append([
                str(int(row['id'])),
                str(row['rat_id'])[:10],
                str(row['treatment'])[:12],
                str(row['experiment_date'])[:10],
                f"{float(row['open_t']):.1f}",
                f"{float(row['closed_t']):.1f}",
                f"{float(row['grooming_t']):.1f}",
                f"{float(row['thigmo_t']):.1f}"
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Estadísticas
        elements.append(Paragraph("Estadísticas resumidas", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        stats_data = [
            ['Metrica', 'Promedio'],
            ['Brazos Abiertos', f"{df_experiments['open_t'].mean():.1f} s"],
            ['Brazos Cerrados', f"{df_experiments['closed_t'].mean():.1f} s"],
            ['Grooming', f"{df_experiments['grooming_t'].mean():.1f} s"],
            ['Thigmotaxis', f"{df_experiments['thigmo_t'].mean():.1f} s"]
        ]
        
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(stats_table)
        
        # Construir documento
        doc.build(elements)
        
        # Obtener bytes
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        try:
            buffer.close()
        except:
            pass
        return b""


def generate_experiments_html_as_pdf(df_experiments):
    """
    Genera un HTML formateado para impresión/guardado como PDF (fallback si reportlab no está disponible).
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte de Experimentos EPM</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 3px solid #6A1B3F;
                padding-bottom: 15px;
            }}
            .header h1 {{
                color: #6A1B3F;
                margin: 5px 0;
            }}
            .header p {{
                color: #666;
                margin: 3px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 12px;
            }}
            th {{
                background-color: #6A1B3F;
                color: white;
                padding: 10px;
                text-align: left;
            }}
            td {{
                padding: 8px;
                border: 1px solid #ddd;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .summary {{
                background-color: #f0f0f0;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Prototipo de Análisis EPM</h1>
            <p>Instituto Politécnico Nacional - ESCOM</p>
            <p>Reporte de Experimentos - {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        
        <div class="summary">
            <strong>Total de experimentos:</strong> {len(df_experiments)}
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Ratón</th>
                    <th>Tratamiento</th>
                    <th>Fecha</th>
                    <th>Abiertos (s)</th>
                    <th>Cerrados (s)</th>
                    <th>Grooming (s)</th>
                    <th>Thigmo (s)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in df_experiments.iterrows():
        html += f"""
                <tr>
                    <td>{row['id']}</td>
                    <td>{row['rat_id']}</td>
                    <td>{row['treatment']}</td>
                    <td>{str(row['experiment_date'])[:10]}</td>
                    <td>{float(row['open_t']):.1f}</td>
                    <td>{float(row['closed_t']):.1f}</td>
                    <td>{float(row['grooming_t']):.1f}</td>
                    <td>{float(row['thigmo_t']):.1f}</td>
                </tr>
        """
    
    html += f"""
            </tbody>
        </table>
        
        <div class="summary">
            <h3>Estadísticas Resumidas</h3>
            <table style="width: 80%; margin: 10px auto;">
                <tr>
                    <th>Métrica</th>
                    <th>Media</th>
                    <th>Min</th>
                    <th>Max</th>
                </tr>
                <tr>
                    <td>Brazos Abiertos (s)</td>
                    <td>{df_experiments['open_t'].mean():.1f}</td>
                    <td>{df_experiments['open_t'].min():.1f}</td>
                    <td>{df_experiments['open_t'].max():.1f}</td>
                </tr>
                <tr>
                    <td>Brazos Cerrados (s)</td>
                    <td>{df_experiments['closed_t'].mean():.1f}</td>
                    <td>{df_experiments['closed_t'].min():.1f}</td>
                    <td>{df_experiments['closed_t'].max():.1f}</td>
                </tr>
                <tr>
                    <td>Grooming (s)</td>
                    <td>{df_experiments['grooming_t'].mean():.1f}</td>
                    <td>{df_experiments['grooming_t'].min():.1f}</td>
                    <td>{df_experiments['grooming_t'].max():.1f}</td>
                </tr>
                <tr>
                    <td>Thigmotaxis (s)</td>
                    <td>{df_experiments['thigmo_t'].mean():.1f}</td>
                    <td>{df_experiments['thigmo_t'].min():.1f}</td>
                    <td>{df_experiments['thigmo_t'].max():.1f}</td>
                </tr>
            </table>
        </div>
        
        <div class="footer">
            Prototipo EPM - TT 2026 | Generado automáticamente<br>
            Para guardar como PDF: Ctrl+P → Guardar como PDF
        </div>
    </body>
    </html>
    """
    
    return html.encode('utf-8')


def render_edit_badge(engine, record_id):
    """Aviso compacto arriba del panel cuando el experimento tiene ediciones manuales."""
    from db.behavior_edits import load_behavior_edits

    edits = load_behavior_edits(engine, record_id)
    if not edits:
        return 0

    last = edits[0]
    edited_when = str(last.get("edited_at") or "")
    edited_by = last.get("edited_by_email") or "desconocido"
    st.markdown(
        f"<div style='background:#FFF6E6;border-left:4px solid {IPN_NARANJA_QUEMADO};"
        f"padding:8px 12px;border-radius:4px;margin:6px 0;font-size:0.85rem;'>"
        f"Tiempos editados manualmente — ultima edicion por <b>{edited_by}</b> "
        f"({last.get('edited_role') or 'rol N/D'}) el {edited_when}. "
        f"Total de ediciones: <b>{len(edits)}</b>. "
        f"<span style='color:#666;'>(ver historial al final del panel)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    return len(edits)


def render_edit_history_expander(engine, record_id, can_revert):
    """Expander con el historial completo de ediciones + botones de revert."""
    from db.behavior_edits import load_behavior_edits, revert_to_before_snapshot

    edits = load_behavior_edits(engine, record_id)
    if not edits:
        st.caption("Este experimento no tiene ediciones manuales registradas.")
        return

    with st.expander(f"Historial de ediciones del registro #{record_id} ({len(edits)})",
                     expanded=False):
        for edit in edits:
            cols = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
            cols[0].markdown(
                f"**#{edit['id']}** &mdash; {edit.get('edited_by_email') or 'desconocido'}  \n"
                f"<span style='color:#666;font-size:0.78rem;'>"
                f"{edit.get('edited_role') or ''} &middot; {edit.get('edited_at')}"
                f"</span>",
                unsafe_allow_html=True,
            )

            def _delta(label, before_val, after_val):
                before_v = float(before_val or 0.0)
                after_v = float(after_val or 0.0)
                diff = after_v - before_v
                arrow = "↑" if diff > 0.05 else ("↓" if diff < -0.05 else "·")
                return f"**{label}**  \n{before_v:.1f}s → {after_v:.1f}s {arrow}"

            cols[1].markdown(_delta("Abiertos", edit["before_open"], edit["after_open"]))
            cols[2].markdown(_delta("Cerrados", edit["before_closed"], edit["after_closed"]))
            cols[3].markdown(_delta("Centro", edit.get("before_center"), edit.get("after_center")))
            cols[4].markdown(_delta("Grooming", edit["before_grooming"], edit["after_grooming"]))
            cols[5].markdown(_delta("Thigmo", edit["before_thigmo"], edit["after_thigmo"]))

            with cols[6]:
                if can_revert:
                    if st.button("Revertir", key=f"revert_edit_{record_id}_{edit['id']}",
                                 help="Restaura los tiempos al estado anterior a esta edicion"):
                        ok, msg = revert_to_before_snapshot(engine, edit["id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if edit.get("note"):
                st.caption(f"Nota: {edit['note']}")
            st.markdown("<hr style='margin:6px 0;opacity:0.15;'/>", unsafe_allow_html=True)


def render_inline_time_editor_form(engine, record_id, current_values,
                                   user_email, user_role):
    """Form de edicion: 4 inputs + nota + guardar. Solo se renderiza cuando
    el toggle 'Editar tiempos' esta activo."""
    e1, e2, e3, e4, e5 = st.columns(5)
    new_open = e1.number_input(
        "Abiertos (s)", min_value=0.0, step=0.1, format="%.1f",
        value=float(current_values["open"]),
        key=f"edit_open_{record_id}",
    )
    new_closed = e2.number_input(
        "Cerrados (s)", min_value=0.0, step=0.1, format="%.1f",
        value=float(current_values["closed"]),
        key=f"edit_closed_{record_id}",
    )
    new_center = e3.number_input(
        "Centro (s)", min_value=0.0, step=0.1, format="%.1f",
        value=float(current_values["center"]),
        key=f"edit_center_{record_id}",
    )
    new_groom = e4.number_input(
        "Grooming (s)", min_value=0.0, step=0.1, format="%.1f",
        value=float(current_values["grooming"]),
        key=f"edit_groom_{record_id}",
    )
    new_thigmo = e5.number_input(
        "Thigmotaxis (s)", min_value=0.0, step=0.1, format="%.1f",
        value=float(current_values["thigmo"]),
        key=f"edit_thigmo_{record_id}",
    )

    note = st.text_input(
        "Motivo de la edicion (obligatorio para auditoria)",
        key=f"edit_note_{record_id}",
        placeholder="Ej: el modelo perdio un evento de grooming en el segundo 45",
    )

    has_changes = (
        abs(new_open - current_values["open"]) > 0.01
        or abs(new_closed - current_values["closed"]) > 0.01
        or abs(new_center - current_values["center"]) > 0.01
        or abs(new_groom - current_values["grooming"]) > 0.01
        or abs(new_thigmo - current_values["thigmo"]) > 0.01
    )
    has_note = bool((note or "").strip())

    btn_col, info_col = st.columns([1, 3])
    with btn_col:
        save_clicked = st.button(
            "Guardar tiempos editados",
            type="primary",
            disabled=not (has_changes and has_note),
            key=f"save_inline_{record_id}",
            use_container_width=True,
        )
    with info_col:
        if not has_changes:
            st.caption("Edita un valor para activar el botón de guardado.")
        elif not has_note:
            st.caption("Escribe un motivo para poder guardar (queda en el historial).")
        else:
            st.caption("Listo para guardar. Los cambios fluyen al módulo de Comparación.")

    if save_clicked:
        ok, msg = update_experiment_times(
            engine,
            record_id,
            new_open,
            new_closed,
            new_center,
            new_groom,
            new_thigmo,
            user_email=user_email,
            user_role=user_role,
            note=note.strip(),
        )
        if ok:
            st.success(msg)
            st.session_state.pop("results_original_df", None)
            st.session_state[f"edit_mode_{record_id}"] = False
            st.rerun()
        else:
            st.error(msg)


def render_detail_panel(record, trajectory_bundle, engine=None,
                        is_admin=False, can_edit_record=False,
                        user_email=None, user_role=None):
    record_id = int(record.get("id", 0) or 0)
    metric_open = coalesce_metric(record, trajectory_bundle, "open_t")
    metric_closed = coalesce_metric(record, trajectory_bundle, "closed_t")
    metric_center = coalesce_metric(record, trajectory_bundle, "center_t")
    metric_groom = coalesce_metric(record, trajectory_bundle, "grooming_t")
    metric_thigmo = coalesce_metric(record, trajectory_bundle, "thigmo_t")

    st.markdown('<div class="content-card" style="border-top: 4px solid #6F1D46;">', unsafe_allow_html=True)
    st.markdown(f"#### Análisis del registro #{record['id']}")

    if engine and record_id > 0:
        render_edit_badge(engine, record_id)

    info_left, info_right = st.columns(2)
    with info_left:
        st.write(f"**Sujeto:** {record['rat_id']}")
        st.write(f"**Tratamiento:** {record['treatment']}")
        st.write(f"**Responsable:** {record['responsible']}")
    with info_right:
        st.write(f"**Fecha:** {record['experiment_date']}")
        st.write(f"**Estado:** {record['analysis_status']}")
        if trajectory_bundle:
            st.write(f"**Trayectoria:** `{os.path.basename(trajectory_bundle['trajectory_path'])}`")

    edit_mode_key = f"edit_mode_{record_id}"
    can_show_toggle = bool(engine and record_id > 0 and can_edit_record)

    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.markdown("##### Tiempos del registro")
    with header_right:
        if can_show_toggle:
            edit_mode = st.toggle(
                "Editar",
                value=st.session_state.get(edit_mode_key, False),
                key=f"toggle_{edit_mode_key}",
                help="Activa el modo edicion para corregir los tiempos detectados por el modelo.",
            )
            st.session_state[edit_mode_key] = edit_mode
        else:
            edit_mode = False

    if edit_mode:
        render_inline_time_editor_form(
            engine,
            record_id,
            current_values={
                "open": metric_open,
                "closed": metric_closed,
                "center": metric_center,
                "grooming": metric_groom,
                "thigmo": metric_thigmo,
            },
            user_email=user_email,
            user_role=user_role,
        )
    else:
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Abiertos", format_seconds(metric_open))
        k2.metric("Cerrados", format_seconds(metric_closed))
        k3.metric("Centro", format_seconds(metric_center))
        k4.metric("Grooming", format_seconds(metric_groom))
        k5.metric("Thigmotaxis", format_seconds(metric_thigmo))

    # Mostrar ruta del video analizado
    video_path = record.get('video_path', '')
    if video_path:
        st.markdown("---")
        st.markdown("**Ruta del video analizado:**")
        st.code(video_path, language=None)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("##### Distribución espacial")
        distribution_df = build_distribution_dataframe(
            {
                "open_t": metric_open,
                "closed_t": metric_closed,
                "center_t": metric_center,
            }
        )
        fig_pie = px.pie(
            distribution_df,
            values="Segundos",
            names="Categoria",
            hole=0.55,
            color="Categoria",
            color_discrete_map=ZONE_CATEGORY_COLORS,
        )
        fig_pie.update_traces(textfont=dict(color="white"), marker=dict(line=dict(color=colors["bg_card"], width=2)))
        apply_plot_style(fig_pie, height=360, show_y_grid=False)
        st.plotly_chart(fig_pie, use_container_width=True, key=f"detail_distribution_{record_id}")

    with chart_right:
        st.markdown("##### Conductas acumuladas")
        behavior_df = pd.DataFrame(
            [
                {"Conducta": "Grooming", "Segundos": metric_groom},
                {"Conducta": "Thigmotaxis", "Segundos": metric_thigmo},
            ]
        )
        fig_behavior = px.bar(
            behavior_df,
            x="Conducta",
            y="Segundos",
            color="Conducta",
            color_discrete_map=BEHAVIOR_COLORS,
        )
        fig_behavior.update_traces(marker_line_color=colors["bg_card"], marker_line_width=1.2)
        apply_plot_style(fig_behavior, height=360)
        fig_behavior.update_layout(showlegend=False)
        st.plotly_chart(fig_behavior, use_container_width=True, key=f"detail_behavior_{record_id}")

    if not trajectory_bundle:
        st.info("No se encontró el archivo de trayectoria final para generar mapas y series temporales.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    zone_df = trajectory_bundle["zone_seconds"]
    timeline = trajectory_bundle["timeline"]
    heatmap_df = trajectory_bundle["heatmap"]

    lower_left, lower_right = st.columns(2)

    with lower_left:
        st.markdown("##### Tiempo por zona")
        zone_plot_df = zone_df[zone_df["Categoria"] != "Fuera"].copy().sort_values("Segundos", ascending=True)
        fig_zone = px.bar(
            zone_plot_df,
            x="Segundos",
            y="Zona",
            color="Categoria",
            orientation="h",
            color_discrete_map=ZONE_CATEGORY_COLORS,
        )
        fig_zone.update_traces(marker_line_color=colors["bg_card"], marker_line_width=1.2)
        apply_plot_style(fig_zone, height=360)
        fig_zone.update_layout(xaxis_title="Segundos", yaxis_title=None)
        st.plotly_chart(fig_zone, use_container_width=True, key=f"detail_zones_{record_id}")

    with lower_right:
        st.markdown("##### Serie temporal conductual")
        timeline_plot = timeline[["Tiempo (s)", "Grooming acumulado", "Thigmotaxis acumulado"]].copy()
        fig_timeline = px.area(
            timeline_plot,
            x="Tiempo (s)",
            y=["Grooming acumulado", "Thigmotaxis acumulado"],
            color_discrete_map=BEHAVIOR_COLORS,
        )
        apply_plot_style(fig_timeline, height=360)
        fig_timeline.update_layout(hovermode="x unified", xaxis_title="Tiempo (s)", yaxis_title="Segundos acumulados")
        st.plotly_chart(fig_timeline, use_container_width=True, key=f"detail_timeline_{record_id}")

    st.markdown("##### Mapa de calor del experimento")
    heatmap_image = build_opencv_heatmap_image(
        heatmap_df,
        trajectory_bundle["heatmap_width"],
        trajectory_bundle["heatmap_height"],
        video_path=record.get("video_path"),
    )
    if heatmap_image is None:
        st.info("La trayectoria no trae suficientes coordenadas válidas para construir el mapa de calor.")
    else:
        st.image(
            heatmap_image,
            use_container_width=True,
            caption="Mapa de permanencia (colormap PLASMA) superpuesto sobre un frame del video original.",
        )

        # Recuadro separado con la leyenda de la escala de colores.
        st.markdown("**Cómo leer este mapa**")
        st.image(
            build_plasma_colorbar(),
            use_container_width=True,
        )
        leg_left, leg_right = st.columns(2)
        with leg_left:
            st.caption("← Menos tiempo (zona poco visitada)")
        with leg_right:
            st.markdown(
                "<div style='text-align:right;color:#888;font-size:0.85em;'>"
                "Mas tiempo (zona caliente) →"
                "</div>",
                unsafe_allow_html=True,
            )
        st.caption(
            "Negro / morado oscuro: el roedor paso poco o nada en esa zona. "
            "Tonos rosa y naranja: gradacion intermedia. "
            "Amarillo brillante: zonas donde permanecio mas tiempo durante el experimento."
        )

    if engine and record_id > 0:
        st.markdown("---")
        st.markdown("##### Historial de versiones del registro")
        can_revert = bool(is_admin or can_edit_record)
        render_edit_history_expander(engine, record_id, can_revert)

    st.markdown("</div>", unsafe_allow_html=True)


# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.warning("Debes iniciar sesión antes de usar el prototipo.")
    st.stop()

# ================= 2. DATABASE CONNECTION =================
engine = load_resource_with_splash(
    page_id="page_results",
    state_key="engine",
    generator_factory=results_loading_sequence,
    dependency_signature="results_db_engine",
    subtitle="TT 2026 - Sincronizando reportes...",
)

# ================= 3. CABECERA =================
render_topbar()
st.markdown("### Módulo 05: Resultados y estadísticas")
st.markdown(
    """
    Dashboard para revisar metrica conductual real del experimento:
    tiempo total en brazos abiertos, brazos cerrados, centro, grooming y thigmotaxis.
    """
)
delete_notice = st.session_state.pop("results_delete_notice", None)
if delete_notice:
    st.success(delete_notice)
st.divider()

# ================= 4. DASHBOARD CONTENT =================
try:
    df_hist = load_history_dataframe(engine)
    if df_hist.empty:
        df_hist = build_session_fallback_dataframe()

    if df_hist.empty:
        st.info("No hay experimentos analizados ni trayectorias disponibles todavía.")
    else:
        numeric_cols = ["open_t", "closed_t", "center_t", "grooming_t", "thigmo_t"]
        for column in numeric_cols:
            df_hist[column] = pd.to_numeric(df_hist[column], errors="coerce").fillna(0.0)

        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Historial experimental")
        scope_options = ["Ultimo completado", "Completados", "Todos", "Pendientes"]
        history_scope = st.selectbox(
            "Vista del historial",
            scope_options,
            index=2,  # Por defecto muestra "Todos"
            key="results_history_scope",
        )
        df_scope = filter_history_scope(df_hist, history_scope)

        # Obtener rol y usuario actual una sola vez
        user_role = st.session_state.get("role", "estudiante").lower()
        current_user = str(st.session_state.get("user", "") or "")
        is_admin = user_role == "admin"
        is_investigador = user_role == "investigador"

        render_global_kpis(df_scope if not df_scope.empty else df_hist.iloc[0:0].copy())
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Filtra registros y luego selecciona uno para ver detalles y gráficas.")

        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            q_search = st.text_input("Buscar sujeto o responsable")
        with filter_col2:
            treatments = ["Todos"] + sorted([value for value in df_scope["treatment"].dropna().unique().tolist() if value])
            q_treat = st.selectbox("Filtrar por tratamiento", treatments)
        with filter_col3:
            statuses = ["Todos"] + sorted([value for value in df_scope["analysis_status"].dropna().unique().tolist() if value])
            q_status = st.selectbox("Estado", statuses)

        # Filtro adicional para investigadores
        show_only_mine = False
        
        if is_investigador:
            show_only_mine = st.checkbox(
                "Mostrar solo mis experimentos (para poder editarlos)",
                value=False,
                key="filter_only_mine",
                help="Activa este filtro para ver solo tus experimentos y poder editar los tiempos"
            )

        df_view = df_scope.copy()
        if q_search:
            mask = (
                df_view["rat_id"].astype(str).str.contains(q_search, case=False, na=False)
                | df_view["responsible"].astype(str).str.contains(q_search, case=False, na=False)
            )
            df_view = df_view[mask]
        if q_treat != "Todos":
            df_view = df_view[df_view["treatment"] == q_treat]
        if q_status != "Todos":
            df_view = df_view[df_view["analysis_status"] == q_status]
        
        # Aplicar filtro "solo mis experimentos" para investigadores
        if show_only_mine and current_user:
            df_view = df_view[df_view["owner_email"].astype(str) == current_user]

        display_df = df_view[
            [
                "id",
                "rat_id",
                "treatment",
                "experiment_date",
                "responsible",
                "open_t",
                "closed_t",
                "grooming_t",
                "thigmo_t",
                "analysis_status",
            ]
        ].copy()
        display_df = display_df.rename(
            columns={
                "id": "ID",
                "rat_id": "Sujeto",
                "treatment": "Tratamiento",
                "experiment_date": "Fecha",
                "responsible": "Responsable",
                "open_t": "Abiertos (s)",
                "closed_t": "Cerrados (s)",
                "grooming_t": "Grooming (s)",
                "thigmo_t": "Thigmotaxis (s)",
                "analysis_status": "Estado",
            }
        )
        selected_before = {
            int(exp_id)
            for exp_id in st.session_state.get("results_selected_ids", [])
            if str(exp_id).isdigit()
        }

        # Fusionar cambios pendientes del editor (edited_rows) para que un rerun
        # intermedio no borre checkboxes que el usuario acaba de marcar/desmarcar.
        _editor_state = st.session_state.get("results_selection_editor", {})
        _edited_rows = (_editor_state or {}).get("edited_rows", {})
        _id_list = display_df["ID"].astype(int).tolist()
        for _row_idx_str, _row_changes in _edited_rows.items():
            try:
                _row_idx = int(_row_idx_str)
                _exp_id = _id_list[_row_idx]
                if "Seleccionar" in _row_changes:
                    if _row_changes["Seleccionar"]:
                        selected_before.add(_exp_id)
                    else:
                        selected_before.discard(_exp_id)
            except (IndexError, KeyError, ValueError, TypeError):
                pass

        visible_ids = {int(exp_id) for exp_id in display_df["ID"].tolist()}
        selected_before = selected_before.intersection(visible_ids)
        if not selected_before and len(visible_ids) == 1:
            selected_before = visible_ids

        selection_df = display_df.copy()
        selection_df.insert(0, "Seleccionar", selection_df["ID"].astype(int).isin(selected_before))
        
        # Determinar qué experimentos puede editar este usuario
        editable_exp_ids = set()
        if is_admin:
            # Admin puede editar todos
            editable_exp_ids = set(selection_df["ID"].astype(int).tolist())
        elif is_investigador:
            # Investigador solo puede editar sus propios experimentos
            for exp_id in selection_df["ID"].astype(int).tolist():
                exp_data = df_view[df_view["id"] == exp_id]
                if not exp_data.empty:
                    owner_email = str(exp_data.iloc[0].get("owner_email", ""))
                    if owner_email == current_user:
                        editable_exp_ids.add(exp_id)
        
        # Nota: en versiones anteriores se insertaba aqui una segunda columna
        # checkbox sin header para indicar editabilidad. Se removio porque
        # duplicaba visualmente la columna "Sel.". La info de permisos ya se
        # comunica via los mensajes st.info/st.warning de mas abajo y por las
        # celdas de tiempo deshabilitadas para experimentos no editables.


        # Configurar columnas deshabilitadas basándose en permisos
        time_columns = ["Abiertos (s)", "Cerrados (s)", "Grooming (s)", "Thigmotaxis (s)"]
        
        if is_admin:
            # Admin puede editar tiempos de todos, pero no otras columnas
            disabled_columns = [col for col in selection_df.columns if col not in time_columns and col != "Seleccionar"]
            st.info("Como administrador, puedes editar los tiempos de cualquier experimento en la tabla.")
        elif is_investigador:
            # Verificar si hay experimentos ajenos en la vista actual
            all_ids_in_view = set(selection_df["ID"].astype(int).tolist())
            has_foreign_experiments = bool(all_ids_in_view - editable_exp_ids)
            
            if has_foreign_experiments:
                # Hay experimentos ajenos: deshabilitar columnas de tiempo
                disabled_columns = [col for col in selection_df.columns if col != "Seleccionar"]
                if editable_exp_ids:
                    st.warning(f"Hay experimentos de otros investigadores en la vista actual. Filtra para ver solo tus experimentos y poder editarlos. (Tienes {len(editable_exp_ids)} experimento(s) propio(s) en esta vista)")
                else:
                    st.warning("No tienes experimentos propios en esta vista. Solo puedes ver los datos.")
            else:
                # Solo hay experimentos propios: permitir edición de tiempos
                disabled_columns = [col for col in selection_df.columns if col not in time_columns and col != "Seleccionar"]
                if editable_exp_ids:
                    st.info(f"Como investigador, puedes editar los tiempos de tus experimentos ({len(editable_exp_ids)} en esta vista).")
                else:
                    st.info("No hay experimentos en esta vista.")
        else:
            # Estudiantes no pueden editar nada excepto selección
            disabled_columns = [col for col in selection_df.columns if col != "Seleccionar"]
        
        # Guardar estado original para detectar cambios
        if "results_original_df" not in st.session_state:
            st.session_state["results_original_df"] = selection_df.copy()
        
        edited_selection = st.data_editor(
            selection_df,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_columns,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn(
                    "Sel.",
                    help="Marca uno o varios experimentos para compararlos y ver sus detalles.",
                    default=False,
                    width="small",
                ),
                "": st.column_config.CheckboxColumn(
                    "",
                    help="Indica si puedes editar los tiempos de este experimento.",
                    disabled=True,
                    width="small",
                ),
                "Abiertos (s)": st.column_config.NumberColumn(
                    "Abiertos (s)",
                    help="Tiempo en brazos abiertos (segundos)",
                    min_value=0.0,
                    format="%.1f"
                ),
                "Cerrados (s)": st.column_config.NumberColumn(
                    "Cerrados (s)",
                    help="Tiempo en brazos cerrados (segundos)",
                    min_value=0.0,
                    format="%.1f"
                ),
                "Grooming (s)": st.column_config.NumberColumn(
                    "Grooming (s)",
                    help="Duración de grooming (segundos)",
                    min_value=0.0,
                    format="%.1f"
                ),
                "Thigmotaxis (s)": st.column_config.NumberColumn(
                    "Thigmotaxis (s)",
                    help="Duración de thigmotaxis (segundos)",
                    min_value=0.0,
                    format="%.1f"
                )
            },
            key="results_selection_editor",
        )
        
        # Detectar cambios en los tiempos y guardar en BD (solo para admin/investigador)
        if is_admin or is_investigador:
            original_df = st.session_state["results_original_df"]
            changes_detected = []
            unauthorized_changes = []
            
            for idx in edited_selection.index:
                exp_id = int(edited_selection.loc[idx, "ID"])
                
                # Buscar fila original correspondiente
                original_matches = original_df[original_df["ID"] == exp_id]
                if original_matches.empty:
                    continue
                    
                original_row = original_matches.iloc[0]
                edited_row = edited_selection.loc[idx]
                
                # Verificar si hubo cambios en los tiempos
                try:
                    orig_open = float(original_row["Abiertos (s)"])
                    orig_closed = float(original_row["Cerrados (s)"])
                    orig_grooming = float(original_row["Grooming (s)"])
                    orig_thigmo = float(original_row["Thigmotaxis (s)"])
                    
                    edit_open = float(edited_row["Abiertos (s)"])
                    edit_closed = float(edited_row["Cerrados (s)"])
                    edit_grooming = float(edited_row["Grooming (s)"])
                    edit_thigmo = float(edited_row["Thigmotaxis (s)"])
                    
                    times_changed = (
                        abs(orig_open - edit_open) > 0.01 or
                        abs(orig_closed - edit_closed) > 0.01 or
                        abs(orig_grooming - edit_grooming) > 0.01 or
                        abs(orig_thigmo - edit_thigmo) > 0.01
                    )
                    
                    if times_changed:
                        # Verificar permisos: Admin puede editar todo, investigador solo lo suyo
                        if exp_id in editable_exp_ids:
                            # El centro no es editable en este flujo masivo (tabla),
                            # asi que reutilizamos su valor original sin cambios.
                            try:
                                orig_center = float(original_row["Centro (s)"])
                            except (KeyError, ValueError, TypeError):
                                orig_center = 0.0
                            changes_detected.append({
                                "id": exp_id,
                                "open_t": edit_open,
                                "closed_t": edit_closed,
                                "center_t": orig_center,
                                "grooming_t": edit_grooming,
                                "thigmo_t": edit_thigmo
                            })
                        else:
                            unauthorized_changes.append(exp_id)
                except (ValueError, TypeError):
                    continue
            
            # Advertir sobre cambios no autorizados (investigador intentando editar experimentos ajenos)
            if unauthorized_changes:
                st.error(f"No tienes permiso para editar los experimentos: {', '.join(f'#{id}' for id in unauthorized_changes)}")
            
            # Mostrar botón para guardar cambios si se detectaron modificaciones autorizadas
            if changes_detected:
                st.warning(f"Se detectaron {len(changes_detected)} cambio(s) autorizados en los tiempos. Presiona 'Guardar cambios' para aplicarlos a la base de datos.")
                
                if st.button("Guardar cambios", type="primary", key="save_time_changes"):
                    success_count = 0
                    error_count = 0
                    
                    for change in changes_detected:
                        success, message = update_experiment_times(
                            engine,
                            change["id"],
                            change["open_t"],
                            change["closed_t"],
                            change["center_t"],
                            change["grooming_t"],
                            change["thigmo_t"],
                            user_email=current_user,
                            user_role=user_role,
                        )
                        
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                            st.error(f"Error en experimento #{change['id']}: {message}")
                    
                    if success_count > 0:
                        st.success(f"✓ {success_count} experimento(s) actualizado(s) exitosamente")
                        # Resetear estado original
                        del st.session_state["results_original_df"]
                        st.rerun()
                    
                    if error_count > 0:
                        st.error(f"✗ {error_count} experimento(s) con errores")
        
        selected_ids = edited_selection.loc[
            edited_selection["Seleccionar"],
            "ID",
        ].astype(int).tolist()
        st.session_state["results_selected_ids"] = selected_ids

        selected_view = df_view[df_view["id"].astype(int).isin(selected_ids)].copy()
        owned_selected_ids = []
        blocked_selected_ids = []
        for row in selected_view.itertuples(index=False):
            row_id = int(row.id)
            owner_email = str(getattr(row, "owner_email", "") or "")
            if row_id > 0 and owner_email == current_user:
                owned_selected_ids.append(row_id)
            elif row_id > 0:
                blocked_selected_ids.append(row_id)

        if selected_ids:
            st.caption(f"Seleccionados para visualizar: {len(selected_ids)}")
            
            # Botones de descarga de reportes
            st.markdown("##### Descargar reportes")
            col_csv, col_json, col_pdf = st.columns(3)
            
            with col_csv:
                csv_data = generate_experiments_csv(selected_view)
                st.download_button(
                    label="CSV",
                    data=csv_data,
                    file_name=f"experimentos_epm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_results"
                )
                st.caption("Datos tabulares compatibles con Excel")
            
            with col_json:
                json_data = generate_experiments_json(selected_view)
                st.download_button(
                    label="JSON",
                    data=json_data,
                    file_name=f"experimentos_epm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_results"
                )
                st.caption("Formato estructurado para APIs")
            
            with col_pdf:
                try:
                    pdf_data = generate_experiments_pdf(selected_view)
                    # Verificar que los datos del PDF no estén vacíos
                    if pdf_data and len(pdf_data) > 100:
                        st.download_button(
                            label="PDF",
                            data=pdf_data,
                            file_name=f"reporte_experimentos_epm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_pdf_results"
                        )
                        st.caption("Reporte profesional imprimible")
                    else:
                        st.error("Error al generar PDF")
                except Exception as e:
                    st.error(f"No se pudo generar el PDF: {str(e)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if blocked_selected_ids:
                st.warning(
                    "Hay experimentos seleccionados que pertenecen a otros investigadores. "
                    "Puedes visualizarlos si aparecen en tu historial, pero no borrarlos."
                )

            # Solo permitir borrado a investigadores y administradores
            can_delete = is_admin or is_investigador
            
            if can_delete:
                delete_confirmed = st.checkbox(
                    "Confirmo que deseo borrar los experimentos seleccionados que me pertenecen.",
                    key="results_delete_confirm",
                )
                if st.button(
                    "Borrar mis experimentos seleccionados",
                    type="secondary",
                    use_container_width=True,
                    disabled=not owned_selected_ids or not delete_confirmed,
                    key="btn_delete_selected_results",
                ):
                    deleted_count, skipped_ids, delete_error = delete_owned_experiments(
                        engine,
                        selected_ids,
                        current_user,
                    )
                    if delete_error:
                        st.error(delete_error)
                    else:
                        st.session_state["results_selected_ids"] = []
                        notice = f"Se borraron {deleted_count} experimento(s) propios."
                        if skipped_ids:
                            notice += f" Se omitieron {len(skipped_ids)} registro(s) sin permiso de borrado."
                        st.session_state["results_delete_notice"] = notice
                        st.rerun()
            else:
                # Mensaje informativo para estudiantes
                st.info("Los estudiantes no tienen permisos para borrar experimentos. Solo investigadores y administradores pueden eliminar registros.")
        else:
            st.caption("Marca una o varias casillas para visualizar comparativas y detalles.")
        st.markdown("</div>", unsafe_allow_html=True)

        if not df_view.empty:
            if selected_ids and not selected_view.empty:
                render_global_chart(selected_view)
                st.markdown("<br>", unsafe_allow_html=True)

                for selected_exp in selected_view.to_dict(orient="records"):
                    trajectory_bundle = load_trajectory_bundle(resolve_trajectory_path(selected_exp))
                    can_edit_record = int(selected_exp.get("id", 0) or 0) in editable_exp_ids
                    render_detail_panel(
                        selected_exp,
                        trajectory_bundle,
                        engine=engine,
                        is_admin=is_admin,
                        can_edit_record=can_edit_record,
                        user_email=current_user,
                        user_role=user_role,
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info("Selecciona al menos un experimento en la tabla para ver sus gráficas y detalles.")
        else:
            st.warning("No hay registros que coincidan con los filtros actuales.")
except Exception as error:
    st.error(f"Error de base de datos o dashboard: {error}")

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
