import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =============== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
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

# =============== 5. CARGA DE DATOS (REAL O SIMULADA) =================
if "resultados_analisis" not in st.session_state:
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

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Tiempo Total", f"{total_tiempo:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

with kpi2:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric(
        "Tiempo en Brazos Abiertos",
        f"{tiempo_abiertos:.1f} s",
        delta=f"{indice_ansiedad:.1f}% del total",
        delta_color="normal" if indice_ansiedad > 20 else "inverse",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with kpi3:
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Tiempo en Brazos Cerrados", f"{tiempo_cerrados:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)

with kpi4:
    cambios = df["Zona"] != df["Zona"].shift(1)
    num_entradas = cambios.sum()
    st.markdown('<div class="tt-metric-card">', unsafe_allow_html=True)
    st.metric("Actividad (Entradas)", f"{num_entradas}")
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

# =============== 10. EXPORTACIÓN =================
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
