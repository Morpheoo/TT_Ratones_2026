import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sys
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ================= 0. PERSISTENCIA =================
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from src.session_utils import load_session, save_session

# Cargar sesión antes de validar login
load_session()

# =============== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
    st.stop()

# GUARDIA: ADMINS NO PUEDEN USAR EL MÓDULO EXPERIMENTAL
if st.session_state.get("role") == "admin":
    st.warning("⛔ El rol de Administrador está limitado a gestión de usuarios.")
    st.info("Para cuidar la integridad de los datos, los administradores no pueden crear ni modificar experimentos.")
    st.stop()

# OJO: set_page_config ya se hace en Login/Home. No lo repetimos aquí para evitar error.
# st.set_page_config(page_title="Dashboard Resultados", layout="wide")

# =============== 2. SELECTOR DE TEMA =================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Oscuro"

theme_mode = st.sidebar.radio(
    "Tema de la interfaz",
    ["Claro", "Oscuro"],
    index=0 if st.session_state.theme_mode == "Claro" else 1,
)
st.session_state.theme_mode = theme_mode

# Paleta verde según tema
if theme_mode == "Claro":
    colors = {
        "page_bg": "#d1fae5",
        "card_bg": "#ecfdf5",
        "text_main": "#064e3b",
        "shadow": "rgba(15, 23, 42, 0.15)",
        "primary": "#10b981",
        "primary_hover": "#059669",
    }
else:
    colors = {
        "page_bg": "#022c22",
        "card_bg": "#064e3b",
        "text_main": "#ecfdf5",
        "shadow": "rgba(0,0,0,0.6)",
        "primary": "#22c55e",
        "primary_hover": "#16a34a",
    }

# =============== 3. CSS GLOBAL PARA DASHBOARD =================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

    .tt-dash-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: {colors["text_main"]};
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
    }}

    .tt-dash-subtitle {{
        font-size: 0.95rem;
        color: {colors["text_main"]};
        opacity: 0.9;
        margin-bottom: 1.2rem;
    }}

    .tt-card {{
        background-color: {colors["card_bg"]};
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 14px 30px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.18);
        margin-bottom: 1.4rem;
    }}

    .tt-metric-card {{
        background-color: {colors["card_bg"]};
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 10px 24px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.15);
    }}

    /* Colores de st.metric */
    div[data-testid="stMetric"] label {{
        color: {colors["text_main"]} !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: {colors["text_main"]} !important;
    }}
    div[data-testid="stMetricDelta"] {{
        color: {colors["primary"]} !important;
    }}

    .tt-section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {colors["text_main"]};
        margin-bottom: 0.6rem;
    }}

    .tt-footer-note {{
        font-size: 0.8rem;
        color: {colors["text_main"]};
        opacity: 0.75;
        text-align: center;
        margin-top: 1.0rem;
    }}

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
    </style>
    """,
    unsafe_allow_html=True,
)

# =============== 4. ENCABEZADO =================
st.markdown(
    '<div class="tt-dash-title">📊 Resultados del Comportamiento (EPM)</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="tt-dash-subtitle">'
    'Resumen de métricas de ansiedad, preferencia de zonas y trayectorias '
    'del espécimen en el laberinto en cruz elevado.'
    '</div>',
    unsafe_allow_html=True,
)

# =============== 5. CARGA DE DATOS (HISTORIAL DB) =================
from src.db.connection import get_db_engine
from sqlalchemy import text

st.sidebar.markdown("### 📂 Historial de Experimentos")
engine = get_db_engine()
df_db = None

if engine:
    try:
        with engine.connect() as conn:
            # Listar experimentos recientes
            query_list = text("""
                SELECT id, rat_id, treatment, experiment_date, created_at 
                FROM experiments 
                ORDER BY created_at DESC LIMIT 10
            """)
            exps = conn.execute(query_list).fetchall()
            
            opciones_exp = {f"{e[1]} ({e[2]}) - {e[3]} [ID:{e[0]}]": e[0] for e in exps}
            
            sel_exp_label = st.sidebar.selectbox("Cargar experimento previo:", ["Seleccionar..."] + list(opciones_exp.keys()))
            
            if sel_exp_label != "Seleccionar...":
                exp_id = opciones_exp[sel_exp_label]
                
                # Cargar métricas de ese experimento
                q_res = text("""
                    SELECT * FROM analysis_results WHERE experiment_id = :eid ORDER BY timestamp DESC LIMIT 1
                """)
                res_data = conn.execute(q_res, {"eid": exp_id}).fetchone()
                
                if res_data:
                    # Si tuviéramos tabla detallada de frames, la cargaríamos aquí.
                    # Por ahora simulamos el DF temporal si no existe o usamos lógica híbrida.
                    # Mapear columnas de BD a variables locales para visualización
                    st.session_state["db_metrics"] = {
                        "total_time": 300, # Placeholder si no guardamos duración
                        "open": res_data.time_open_arms,
                        "closed": res_data.time_closed_arms,
                        "center": res_data.time_center,
                        "grooming": res_data.grooming_duration,
                        "thigmo": res_data.thigmotaxis_duration
                    }
                    st.success(f"Datos cargados del Experimento ID: {exp_id}")
                else:
                    st.warning("Experiment sin resultados procesados.")
    except Exception as e:
        st.sidebar.error(f"Error BD: {e}")

if "resultados_analisis" not in st.session_state and "db_metrics" not in st.session_state:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.warning("⚠️ No hay datos de un análisis reciente.")

    st.info(
        "🛠️ **Modo Desarrollo:** Puedes generar datos aleatorios para probar "
        "el diseño del dashboard."
    )
    if st.button("🎲 Generar Datos de Prueba (Simulación)"):
        # Simulamos 5 minutos (300 segs) de datos a 10 FPS = 3000 filas
        n_frames = 3000
        tiempos = np.linspace(0, 300, n_frames)

        opciones = [
            "Brazo Cerrado 1",
            "Brazo Cerrado 2",
            "Centro 1",
            "Brazo Abierto 1",
            "Brazo Abierto 2",
        ]
        probs = [0.35, 0.35, 0.2, 0.05, 0.05]
        zonas_sim = np.random.choice(opciones, n_frames, p=probs)

        x_sim = np.random.randint(0, 800, n_frames)
        y_sim = np.random.randint(0, 600, n_frames)

        df_mock = pd.DataFrame(
            {
                "Tiempo (s)": tiempos,
                "Zona": zonas_sim,
                "x": x_sim,
                "y": y_sim,
                "Grooming": np.zeros(n_frames),
                "Thigmotaxis": np.zeros(n_frames)
            }
        )

        st.session_state["resultados_analisis"] = df_mock
        st.markdown("</div>", unsafe_allow_html=True)
        st.rerun()
    else:
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# Recuperamos el DataFrame ya existente
df = st.session_state["resultados_analisis"]

# =============== 6. CÁLCULO DE KPIs =================
resumen_zonas = df.groupby("Zona")["Tiempo (s)"].count() * (1 / 10)  # 10 FPS aprox
total_tiempo = resumen_zonas.sum()

tiempo_abiertos = resumen_zonas.filter(like="Abierto").sum()
tiempo_cerrados = resumen_zonas.filter(like="Cerrado").sum()

indice_ansiedad = (tiempo_abiertos / total_tiempo) * 100 if total_tiempo > 0 else 0.0

# =============== 7. PANEL DE MÉTRICAS =================
st.markdown('<div class="tt-section-title">🧬 Indicadores Clave de Ansiedad</div>', unsafe_allow_html=True)

# Si viene de DB, usamos esos valores
if "db_metrics" in st.session_state:
    m = st.session_state["db_metrics"]
    total_tiempo = m.get("open", 0) + m.get("closed", 0) + m.get("center", 0)
    tiempo_abiertos = m.get("open", 0)
    tiempo_cerrados = m.get("closed", 0)
    grooming_val = m.get("grooming", 0)
    thigmo_val = m.get("thigmo", 0)
    indice_ansiedad = (tiempo_abiertos / total_tiempo * 100) if total_tiempo > 0 else 0
else:
    # Viene de dataframe en memoria
    grooming_val = df["Grooming"].sum() * (1/10) if "Grooming" in df.columns else 0
    thigmo_val = df["Thigmotaxis"].sum() * (1/10) if "Thigmotaxis" in df.columns else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Tiempo Total", f"{total_tiempo:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

with kpi2:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric(
        "T. Brazos Abiertos",
        f"{tiempo_abiertos:.1f} s",
        delta=f"{indice_ansiedad:.1f}%",
        delta_color="normal" if indice_ansiedad > 20 else "inverse",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with kpi3:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("T. Brazos Cerrados", f"{tiempo_cerrados:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

with kpi4:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Acicalamiento", f"{grooming_val:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

with kpi5:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Contacto Pared", f"{thigmo_val:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

# =============== 8. GRÁFICAS INTERACTIVAS =================
st.write("")

col_graf1, col_graf2 = st.columns([2, 1])

with col_graf1:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">📈 Etograma Temporal</div>',
        unsafe_allow_html=True,
    )
    fig_timeline = px.scatter(
        df,
        x="Tiempo (s)",
        y="Zona",
        color="Zona",
        title="Posición del ratón a lo largo del tiempo",
        height=350,
    )
    fig_timeline.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text_main"]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_graf2:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">🍰 Distribución de Tiempo</div>',
        unsafe_allow_html=True,
    )
    fig_pie = px.pie(
        names=resumen_zonas.index,
        values=resumen_zonas.values,
        hole=0.4,
        title="Preferencia de zona",
    )
    fig_pie.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text_main"]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =============== 9. MAPA DE CALOR =================
st.write("")
st.markdown(
    '<div class="tt-section-title">🗺️ Mapa de Trayectoria (Heatmap)</div>',
    unsafe_allow_html=True,
)
c1, c2 = st.columns([3, 1])

with c1:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    fig_map = px.density_heatmap(
        df,
        x="x",
        y="y",
        nbinsx=30,
        nbinsy=30,
        color_continuous_scale="Viridis",
        title="Zonas de mayor permanencia",
    )
    fig_map.update_yaxes(autorange="reversed")
    fig_map.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text_main"]),
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        """
        **Interpretación:**

        - Zonas más brillantes indican donde el espécimen pasó más tiempo.
        - Acumulación en brazos cerrados → mayor nivel de ansiedad.
        - Mayor exploración en brazos abiertos → efecto ansiolítico del tratamiento.
        """,
        unsafe_allow_html=False,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =============== 10. MINERÍA DE DATOS (K-MEANS) =================
st.write("")
st.markdown(
    '<div class="tt-section-title">🧠 Minería de Datos (Clustering de Comportamiento)</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="tt-card">', unsafe_allow_html=True)

if len(df) > 10:
    st.info("🤖 El algoritmo K-Means agrupa automáticamente los momentos del experimento en 'Estados de Comportamiento' basados en velocidad y posición.")
    
    # 1. Preparar datos para clustering
    # Calculamos velocidad instantánea entre puntos
    df_ml = df.copy()
    df_ml["dx"] = df_ml["x"].diff().fillna(0)
    df_ml["dy"] = df_ml["y"].diff().fillna(0)
    df_ml["velocity"] = np.sqrt(df_ml["dx"]**2 + df_ml["dy"]**2)
    
    # Distancia al centro (asumiendo centro aprox en 400,300 de canvas 800x600 o calcular media)
    center_x, center_y = 400, 300
    df_ml["dist_center"] = np.sqrt((df_ml["x"] - center_x)**2 + (df_ml["y"] - center_y)**2)
    
    # Features para el modelo
    X = df_ml[["velocity", "dist_center"]].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 2. Entrenar K-Means
    n_clusters = st.slider("Número de Agrupamientos (Clusters)", 2, 5, 3)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_ml["Cluster"] = kmeans.fit_predict(X_scaled)
    
    # 3. Visualizar
    col_k1, col_k2 = st.columns([2, 1])
    
    with col_k1:
        fig_cluster = px.scatter(
            df_ml,
            x="x",
            y="y",
            color=df_ml["Cluster"].astype(str),
            title="Mapa de Comportamientos Identificados",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_cluster.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=colors["text_main"])
        )
        # Invertir Y para que coincida con video
        fig_cluster.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_cluster, use_container_width=True)
        
    with col_k2:
        st.markdown("**Análisis de Clusters:**")
        # Interpretar clusters (básico)
        comps = df_ml.groupby("Cluster")[["velocity", "dist_center"]].mean()
        for c_id, row in comps.iterrows():
            vel_desc = "Alta" if row["velocity"] > df_ml["velocity"].mean() else "Baja"
            pos_desc = "Periferia" if row["dist_center"] > df_ml["dist_center"].mean() else "Centro"
            st.markdown(f"- **Grupo {c_id}:** Movilidad {vel_desc}, Tendencia a {pos_desc}")
            
else:
    st.warning("Necesitamos más datos para ejecutar Minería de Datos.")

st.markdown("</div>", unsafe_allow_html=True)
from src.reporting import generate_pdf_report

st.write("")
st.markdown(
    '<div class="tt-section-title">📑 Reporte Final</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="tt-card">', unsafe_allow_html=True)

col_d1, col_d2 = st.columns(2)
with col_d1:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Descargar datos crudos (CSV)",
        data=csv,
        file_name="analisis_raton.csv",
        mime="text/csv",
    )
with col_d2:
    if st.button("🖨️ Generar reporte PDF"):
        kpi_data = {
            "tiempo_total": total_tiempo,
            "tiempo_abiertos": tiempo_abiertos,
            "tiempo_cerrados": tiempo_cerrados,
            "pref_abiertos": indice_ansiedad,
            "entradas": num_entradas
        }
        user_name = st.session_state.get("user_name", "Investigador")
        role = st.session_state.get("role", "Usuario")
        
        try:
            pdf_path = generate_pdf_report(user_name, role, kpi_data)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "💾 Descargar PDF",
                    data=f,
                    file_name="reporte_epm_tt2026.pdf",
                    mime="application/pdf"
                )
            st.success("✅ Reporte PDF generado correctamente.")
        except Exception as e:
            st.error(f"Error al generar PDF: {e}")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="tt-footer-note">ESCOM - IPN · Prototipo académico · No usar en producción</div>',
    unsafe_allow_html=True,
)
