import os
import sys
from pathlib import Path

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
    if st.button("Cerrar Sesión", key="logout_btn", use_container_width=True):
        from session_utils import clear_session
        clear_session()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Sidebar con navegación
    inject_sidebar_profile(show_admin_button=True)

ACCENT_COLOR = colors.get("warning", "#B7791F")
ZONE_CATEGORY_COLORS = {
    "Abiertos": colors["primary"],
    "Cerrados": ACCENT_COLOR,
    "Centro": colors["success"],
    "Fuera": colors["text_sub"],
}
BEHAVIOR_COLORS = {
    "Grooming": colors["success"],
    "Thigmotaxis": colors["danger"],
    "Grooming acumulado": colors["success"],
    "Thigmotaxis acumulado": colors["danger"],
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
        return 0, experiment_ids, "No se encontro el usuario activo en sesion."

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
    if summary and summary["summary"].get(key) is not None:
        return safe_float(summary["summary"][key])
    return safe_float(record.get(key, 0.0))


def build_opencv_heatmap_image(heatmap_df, width, height):
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
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_INFERNO)

    background = np.full((int(height), int(width), 3), 246, dtype=np.uint8)
    background[:] = (245, 244, 246)

    mask = normalized > 0
    if not np.any(mask):
        return None

    overlay = background.copy()
    overlay[mask] = colored[mask]
    blended = cv2.addWeighted(background, 0.30, overlay, 0.90, 0)
    return cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)


def render_global_kpis(df_hist):
    m1, m2, m3, m4 = st.columns(4)
    open_mean = df_hist["open_t"].mean() if not df_hist.empty and "open_t" in df_hist.columns else 0.0
    grooming_mean = df_hist["grooming_t"].mean() if not df_hist.empty and "grooming_t" in df_hist.columns else 0.0

    with m1:
        st.metric("Total experimentos", len(df_hist))
    with m2:
        latest_date = str(df_hist["experiment_date"].max()) if not df_hist.empty and "experiment_date" in df_hist.columns else "N/A"
        st.metric("Ultimo registro", latest_date)
    with m3:
        st.metric("Prom. abiertos", format_seconds(open_mean))
    with m4:
        st.metric("Prom. grooming", format_seconds(grooming_mean))


def render_global_chart(df_view):
    st.markdown("#### Comparativa rapida")
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
        color_discrete_sequence=[colors["primary"], ACCENT_COLOR, colors["success"], colors["danger"]],
    )
    fig.update_traces(marker_line_color=colors["bg_card"], marker_line_width=1.2)
    apply_plot_style(fig, height=360)
    selected_signature = "_".join(str(exp_id) for exp_id in df_view["id"].astype(int).tolist())
    st.plotly_chart(fig, use_container_width=True, key=f"global_chart_{selected_signature}")


def render_detail_panel(record, trajectory_bundle):
    record_id = int(record.get("id", 0) or 0)
    metric_open = coalesce_metric(record, trajectory_bundle, "open_t")
    metric_closed = coalesce_metric(record, trajectory_bundle, "closed_t")
    metric_center = coalesce_metric(record, trajectory_bundle, "center_t")
    metric_groom = coalesce_metric(record, trajectory_bundle, "grooming_t")
    metric_thigmo = coalesce_metric(record, trajectory_bundle, "thigmo_t")

    st.markdown('<div class="content-card" style="border-top: 4px solid #6F1D46;">', unsafe_allow_html=True)
    st.markdown(f"#### Analisis del registro #{record['id']}")

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

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Abiertos", format_seconds(metric_open))
    k2.metric("Cerrados", format_seconds(metric_closed))
    k3.metric("Centro", format_seconds(metric_center))
    k4.metric("Grooming", format_seconds(metric_groom))
    k5.metric("Thigmotaxis", format_seconds(metric_thigmo))

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("##### Distribucion espacial")
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
        st.info("No se encontro el archivo de trayectoria final para generar mapas y series temporales.")
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

    st.markdown("##### Mapa de calor OpenCV")
    heatmap_image = build_opencv_heatmap_image(
        heatmap_df,
        trajectory_bundle["heatmap_width"],
        trajectory_bundle["heatmap_height"],
    )
    if heatmap_image is None:
        st.info("La trayectoria no trae suficientes coordenadas validas para construir el mapa de calor.")
    else:
        st.image(
            heatmap_image,
            use_container_width=True,
            caption="Mapa de permanencia generado con OpenCV a partir de la trayectoria del roedor.",
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.warning("Debes iniciar sesion antes de usar el sistema.")
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
st.markdown("### Modulo 05: Resultados y Estadisticas")
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
        st.info("No hay experimentos analizados ni trayectorias disponibles todavia.")
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
            index=0,
            key="results_history_scope",
        )
        df_scope = filter_history_scope(df_hist, history_scope)

        render_global_kpis(df_scope if not df_scope.empty else df_hist.iloc[0:0].copy())
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Filtra registros y luego selecciona uno para ver detalles y graficas.")

        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            q_search = st.text_input("Buscar sujeto o responsable")
        with filter_col2:
            treatments = ["Todos"] + sorted([value for value in df_scope["treatment"].dropna().unique().tolist() if value])
            q_treat = st.selectbox("Filtrar por tratamiento", treatments)
        with filter_col3:
            statuses = ["Todos"] + sorted([value for value in df_scope["analysis_status"].dropna().unique().tolist() if value])
            q_status = st.selectbox("Estado", statuses)

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
        visible_ids = {int(exp_id) for exp_id in display_df["ID"].tolist()}
        selected_before = selected_before.intersection(visible_ids)
        if not selected_before and len(visible_ids) == 1:
            selected_before = visible_ids

        selection_df = display_df.copy()
        selection_df.insert(0, "Seleccionar", selection_df["ID"].astype(int).isin(selected_before))
        edited_selection = st.data_editor(
            selection_df,
            use_container_width=True,
            hide_index=True,
            disabled=[column for column in selection_df.columns if column != "Seleccionar"],
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn(
                    "Sel.",
                    help="Marca uno o varios experimentos para compararlos y ver sus detalles.",
                    default=False,
                    width="small",
                )
            },
            key="results_selection_editor",
        )
        selected_ids = edited_selection.loc[
            edited_selection["Seleccionar"],
            "ID",
        ].astype(int).tolist()
        st.session_state["results_selected_ids"] = selected_ids

        current_user = str(st.session_state.get("user", "") or "")
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
            if blocked_selected_ids:
                st.warning(
                    "Hay experimentos seleccionados que pertenecen a otros investigadores. "
                    "Puedes visualizarlos si aparecen en tu historial, pero no borrarlos."
                )

            delete_confirmed = st.checkbox(
                "Confirmo que deseo borrar los experimentos seleccionados que me pertenecen.",
                key="results_delete_confirm",
            )
            if st.button(
                "BORRAR MIS EXPERIMENTOS SELECCIONADOS",
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
            st.caption("Marca una o varias casillas para visualizar comparativas y detalles.")
        st.markdown("</div>", unsafe_allow_html=True)

        if not df_view.empty:
            if selected_ids and not selected_view.empty:
                render_global_chart(selected_view)
                st.markdown("<br>", unsafe_allow_html=True)

                for selected_exp in selected_view.to_dict(orient="records"):
                    trajectory_bundle = load_trajectory_bundle(resolve_trajectory_path(selected_exp))
                    render_detail_panel(selected_exp, trajectory_bundle)
                    st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info("Selecciona al menos un experimento en la tabla para ver sus graficas y detalles.")
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
