import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sys
import time
# sklearn se importa de forma LAZY en la sección de clustering (ver abajo)
# para no bloquear la carga inicial de la página.

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

from ui_components import generic_splash_loader

# ================= 0. PERSISTENCIA =================
st.set_page_config(page_title="Resultados (EPM)", page_icon="📊", layout="wide")

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from session_utils import load_session, save_session

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

# =============== 2. TEMA Y ESTILOS =================
from ui_theme import use_theme
use_theme()

def results_loading_sequence():
    """Generador para el splash screen de Resultados."""
    yield 20, "Conectando con la base de datos central..."
    from db.connection import get_db_engine
    engine = get_db_engine()
    time.sleep(0.3)
    
    yield 50, "Cargando historial de experimentación..."
    time.sleep(0.3)
    
    yield 80, "Inicializando componentes de visualización..."
    import plotly.express as px
    time.sleep(0.2)
    
    yield 100, "Dashboard listo."
    return engine

# ================== 2. EJECUCIÓN DEL SPLASH SCREEN (RESULTADOS) ==================
if "results_loaded" not in st.session_state:
    generic_splash_loader(results_loading_sequence())
    st.session_state.results_loaded = True

# Color for Plotly charts (depends on theme_mode which use_theme manages via session_state)
plotly_text_color = "#333333" if st.session_state.get("theme_mode", "Claro") == "Claro" else "#E5E7EB"

# =============== 3. CSS GLOBAL PARA DASHBOARD =================
st.markdown(
    """
    <style>
    .tt-dash-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: var(--text-main);
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
    }

    .tt-dash-subtitle {
        font-size: 0.95rem;
        color: var(--text-main);
        opacity: 0.9;
        margin-bottom: 1.2rem;
    }

    .tt-card {
        background-color: transparent;
        padding: 0;
        box-shadow: none;
        border: none;
        margin-bottom: 0;
    }

    /* Colores de st.metric */
    div[data-testid="stMetric"] label {
        color: var(--text-main) !important;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-main) !important;
    }
    div[data-testid="stMetricDelta"] {
        color: var(--primary) !important;
    }

    .tt-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 0.6rem;
    }

    .tt-footer-note {
        font-size: 0.8rem;
        color: var(--text-main);
        opacity: 0.75;
        text-align: center;
        margin-top: 1.0rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============== 4. ENCABEZADO =================
st.markdown('<div class="tt-dash-title">📊 Resultados del Comportamiento (EPM)</div>', unsafe_allow_html=True)
st.markdown('<div class="tt-dash-subtitle">Análisis etológico automático del experimento en el laberinto en cruz elevado.</div>', unsafe_allow_html=True)

st.markdown('<div class="tt-dash-title" style="margin-top: 2rem;">🔬 Bitácora de Experimentos EPM</div>', unsafe_allow_html=True)
st.markdown('<div class="tt-dash-subtitle">Explora y carga experimentos almacenados para visualizar su dashboard analítico.</div>', unsafe_allow_html=True)

# Lazy import del engine AQUÍ, no al tope del módulo
# (el engine está cacheado con @st.cache_resource, así que sólo conecta la primera vez)
from db.connection import get_db_engine
from sqlalchemy import text

engine = get_db_engine()

if engine:
    try:
        with engine.connect() as conn:
            # Listar todos los experimentos para KPIs y Tabla
            query_all = text("""
                SELECT e.id, 
                       e.rat_id as "Sujeto / Video", 
                       e.treatment as "Tratamiento", 
                       e.experiment_date as "Fecha", 
                       e.responsible as "Investigador",
                       COALESCE(a.time_open_arms, 0) as "Open_Arms",
                       COALESCE(a.time_closed_arms, 0) as "Closed_Arms",
                       u.username as "owner_email"
                FROM experiments e
                LEFT JOIN analysis_results a ON e.id = a.experiment_id
                LEFT JOIN users u ON e.created_by = u.id
                ORDER BY e.created_at DESC
            """)
            df_historial_raw = pd.read_sql(query_all, conn)
            
            if not df_historial_raw.empty:
                # --- A. TARJETAS KPI GLOBALES ---
                total_exps = len(df_historial_raw)
                ultima_fecha = df_historial_raw["Fecha"].max()
                
                # Filtrar solo los que tienen datos válidos (mayores a cero) para promedios
                df_valid = df_historial_raw[(df_historial_raw["Open_Arms"] > 0) | (df_historial_raw["Closed_Arms"] > 0)]
                prom_abiertos = df_valid["Open_Arms"].mean() if not df_valid.empty else 0
                prom_cerrados = df_valid["Closed_Arms"].mean() if not df_valid.empty else 0
                
                k_1, k_2, k_3, k_4 = st.columns(4)
                with k_1:
                    with st.container(border=True):
                        st.metric("👥 Experimentos Registrados", f"{total_exps}")
                with k_2:
                    with st.container(border=True):
                        st.metric("📅 Último Análisis", str(ultima_fecha))
                with k_3:
                    with st.container(border=True):
                        st.metric("⏳ Promedio T. Abiertos", f"{prom_abiertos:.1f} s")
                with k_4:
                    with st.container(border=True):
                        st.metric("⏳ Promedio T. Cerrados", f"{prom_cerrados:.1f} s")
                
                # --- B. BARRA DE FILTROS ELEGANTE ---
                st.markdown("### Filtros")
                
                # Estados de filtro en session_state para poder "limpiarlos"
                if "filter_search" not in st.session_state: st.session_state.filter_search = ""
                if "filter_treat" not in st.session_state: st.session_state.filter_treat = "Todos"
                if "filter_inv" not in st.session_state: st.session_state.filter_inv = "Todos"
                
                def clear_filters():
                    st.session_state.filter_search = ""
                    st.session_state.filter_treat = "Todos"
                    st.session_state.filter_inv = "Todos"
                
                with st.container(border=True):
                    f1, f2, f3, f4, f5 = st.columns([3, 2, 2, 2, 1], gap="small", vertical_alignment="bottom")
                    with f1:
                        busqueda = st.text_input("Buscar por ID, sujeto...", key="filter_search", label_visibility="collapsed", placeholder="🔍 Buscar...")
                    with f2:
                        opts_treat = ["Todos"] + list(df_historial_raw["Tratamiento"].unique())
                        tratamiento = st.selectbox("Tratamiento", opts_treat, key="filter_treat", label_visibility="collapsed")
                    with f3:
                        opts_inv = ["Todos"] + list(df_historial_raw["Investigador"].unique())
                        investigador = st.selectbox("Investigador", opts_inv, key="filter_inv", label_visibility="collapsed")
                    with f4:
                        fechas_str = df_historial_raw["Fecha"].astype(str).unique()
                        opts_fecha = ["Todas"] + sorted(list(fechas_str), reverse=True)
                        fecha = st.selectbox("Fecha", opts_fecha, label_visibility="collapsed")
                    with f5:
                        st.button("Limpiar", on_click=clear_filters, use_container_width=True)

                # --- APLICAR FILTROS A DATAFRAME ---
                df_show = df_historial_raw.copy()
                if busqueda:
                    mask = df_show.astype(str).apply(lambda row: row.str.contains(busqueda, case=False, na=False).any(), axis=1)
                    df_show = df_show[mask]
                if tratamiento != "Todos":
                    df_show = df_show[df_show["Tratamiento"] == tratamiento]
                if investigador != "Todos":
                    df_show = df_show[df_show["Investigador"] == investigador]
                if fecha != "Todas":
                    df_show = df_show[df_show["Fecha"].astype(str) == fecha]
                
                # Formatear columnas finales para la UI
                df_ui = df_show.copy()
                df_ui = df_ui.rename(columns={"id": "ID"})
                df_ui["T. Abierto"] = df_ui["Open_Arms"].apply(lambda x: f"{x:.1f} s")
                df_ui["T. Cerrado"] = df_ui["Closed_Arms"].apply(lambda x: f"{x:.1f} s")
                df_ui["Estatus"] = "Completado ✅"
                df_ui = df_ui[["ID", "Sujeto / Video", "Tratamiento", "Fecha", "Investigador", "T. Abierto", "T. Cerrado", "Estatus"]]
                
                # --- C. TABLA PRINCIPAL MODERNA ---
                st.markdown("### Historial de experimentos")
                
                event = st.dataframe(
                    df_ui, 
                    use_container_width=True, 
                    hide_index=True, 
                    height=250,
                    selection_mode="multi-row",
                    on_select="rerun",
                    column_config={
                        "ID": st.column_config.NumberColumn(format="#%d"),
                    }
                )
                
                # --- D. SELECCIÓN DE EXPERIMENTO ---
                st.markdown("### Experimento seleccionado")
                
                with st.container(border=True):
                    selected_rows = event.selection.rows
                    if len(selected_rows) > 1:
                        # === MODO MULTI-SELECCIÓN: Borrado masivo ===
                        st.markdown("### 🗑️ Eliminación Múltiple")
                        current_user = st.session_state.get("user", "")
                        
                        selected_ids = []
                        owned_ids = []
                        for idx in selected_rows:
                            row = df_ui.iloc[idx]
                            exp_id = int(row["ID"])
                            selected_ids.append(exp_id)
                            raw_row = df_historial_raw[df_historial_raw["id"] == exp_id].iloc[0]
                            owner = raw_row.get("owner_email", "")
                            investigador = raw_row.get("Investigador", "")
                            if current_user == owner or current_user == investigador:
                                owned_ids.append(exp_id)
                        
                        st.info(f"Has seleccionado **{len(selected_ids)}** experimentos.")
                        
                        if len(owned_ids) == 0:
                            st.warning("⚠️ Ninguno de estos experimentos te pertenece. No puedes eliminarlos.")
                        else:
                            not_owned = len(selected_ids) - len(owned_ids)
                            if not_owned > 0:
                                st.warning(f"⚠️ {not_owned} experimento(s) pertenecen a otro usuario y NO se eliminarán.")
                            
                            st.error(
                                f"Se eliminarán **{len(owned_ids)}** experimento(s) tuyos "
                                f"(IDs: {', '.join(f'#{x}' for x in owned_ids)}) "
                                f"junto con sus ROIs y resultados."
                            )
                            confirm_multi = st.checkbox(
                                f"Confirmo eliminar mis {len(owned_ids)} experimentos seleccionados",
                                key="confirm_multi_del"
                            )
                            if st.button("🗑️ Eliminar Seleccionados", disabled=not confirm_multi, type="primary"):
                                with engine.connect() as del_conn:
                                    for eid in owned_ids:
                                        del_conn.execute(text("DELETE FROM experiments WHERE id = :id"), {"id": eid})
                                    del_conn.commit()
                                st.success(f"✅ {len(owned_ids)} experimento(s) eliminados.")
                                import time
                                time.sleep(1)
                                st.rerun()

                    elif len(selected_rows) == 1:
                        # === MODO SINGLE: Detalle + Editar + Eliminar ===
                        selected_ui_row = df_ui.iloc[selected_rows[0]]
                        exp_select = int(selected_ui_row["ID"])
                        
                        sel_row = df_historial_raw[df_historial_raw["id"] == exp_select].iloc[0]
                        total = sel_row["Open_Arms"] + sel_row["Closed_Arms"]
                        idx_ansi = (sel_row["Open_Arms"] / total) * 100 if total > 0 else 0
                        
                        col_i1, col_i2 = st.columns([1, 1])
                        with col_i1:
                            st.markdown(f"**ID:** #{sel_row['id']}")
                            st.markdown(f"**Sujeto:** {sel_row['Sujeto / Video']}")
                            st.markdown(f"**Tratamiento:** {sel_row['Tratamiento']}")
                            st.markdown(f"**Investigador:** {sel_row['Investigador']}")
                        with col_i2:
                            st.markdown(f"**Tiempo brazos abiertos:** {sel_row['Open_Arms']:.1f} s")
                            st.markdown(f"**Tiempo brazos cerrados:** {sel_row['Closed_Arms']:.1f} s")
                            st.markdown(f"**Índice de ansiedad:** {idx_ansi:.1f} %")
                            st.write("")
                            
                        with st.expander("✏️ Editar Detalles del Experimento"):
                            with st.form(f"edit_form_{exp_select}"):
                                new_sujeto = st.text_input("Sujeto / Video", value=sel_row['Sujeto / Video'])
                                new_trat = st.text_input("Tratamiento", value=sel_row['Tratamiento'])
                                new_inv = st.text_input("Investigador", value=sel_row['Investigador'])
                                
                                try:
                                    parsed_date = pd.to_datetime(sel_row['Fecha']).date()
                                except:
                                    from datetime import date
                                    parsed_date = date.today()
                                    
                                new_date = st.date_input("Fecha", value=parsed_date)
                                
                                eq_col1, eq_col2 = st.columns([1,1])
                                with eq_col1:
                                    save_btn = st.form_submit_button("💾 Guardar Cambios", type="secondary", use_container_width=True)
                                
                                if save_btn:
                                    try:
                                        q_upd = text("""
                                            UPDATE experiments 
                                            SET rat_id = :s, treatment = :t, responsible = :r, experiment_date = :d
                                            WHERE id = :eid
                                        """)
                                        conn.execute(q_upd, {
                                            "s": new_sujeto, 
                                            "t": new_trat, 
                                            "r": new_inv, 
                                            "d": new_date, 
                                            "eid": exp_select
                                        })
                                        conn.commit()
                                        st.success("¡Metadatos actualizados correctamente!")
                                        import time
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        conn.rollback()
                                        st.error(f"Error al actualizar: {e}")
                                        
                        # --- ELIMINAR EXPERIMENTO (Solo el dueño) ---
                        current_user = st.session_state.get("user", "")
                        owner_email = sel_row.get("owner_email", "")
                        is_owner = (current_user == owner_email) or (current_user == sel_row.get("Investigador", ""))

                        if is_owner:
                            with st.expander("🗑️ Eliminar este experimento"):
                                st.error(
                                    f"⚠️ Esta acción eliminará permanentemente el experimento "
                                    f"**#{sel_row['id']}** ({sel_row['Sujeto / Video']}) "
                                    f"junto con todas sus ROIs y resultados."
                                )
                                confirm_del = st.checkbox(
                                    f"Confirmo que quiero eliminar el experimento #{sel_row['id']}",
                                    key=f"confirm_del_{exp_select}"
                                )
                                if st.button("🗑️ Eliminar Experimento", disabled=not confirm_del, type="primary", key=f"btn_del_{exp_select}"):
                                    with engine.connect() as del_conn:
                                        del_conn.execute(text("DELETE FROM experiments WHERE id = :id"), {"id": exp_select})
                                        del_conn.commit()
                                    st.success(f"✅ Experimento #{exp_select} eliminado.")
                                    import time
                                    time.sleep(1)
                                    st.rerun()

                        st.write("")
                        load_btn = st.button("🚀 Cargar y visualizar dashboard", type="primary", use_container_width=True)
                        
                        if load_btn:
                            # Lógica de carga
                            q_res = text("SELECT * FROM analysis_results WHERE experiment_id = :eid ORDER BY timestamp DESC LIMIT 1")
                            res_data = conn.execute(q_res, {"eid": exp_select}).fetchone()
                            
                            if res_data:
                                st.session_state["db_metrics"] = {
                                    "total_time": 300, 
                                    "open": res_data.time_open_arms,
                                    "closed": res_data.time_closed_arms,
                                    "center": res_data.time_center,
                                    "grooming": res_data.grooming_duration,
                                    "thigmo": res_data.thigmotaxis_duration
                                }
                                
                                q_exp = text("SELECT rat_id FROM experiments WHERE id = :eid")
                                v_data = conn.execute(q_exp, {"eid": exp_select}).fetchone()
                                
                                df_loaded = False
                                if hasattr(res_data, 'trajectory_path') and res_data.trajectory_path and os.path.exists(res_data.trajectory_path):
                                    try:
                                        st.session_state["resultados_analisis"] = pd.read_csv(res_data.trajectory_path)
                                        df_loaded = True
                                    except Exception: pass
                                
                                if not df_loaded and v_data:
                                    fallback_path = os.path.join(os.getcwd(), "videos", f"{v_data[0]}_STREAMLIT_MULTIMODAL_trajectory.csv")
                                    if os.path.exists(fallback_path):
                                        st.session_state["resultados_analisis"] = pd.read_csv(fallback_path)
                                        df_loaded = True
                                
                                if not df_loaded and "resultados_analisis" in st.session_state:
                                    del st.session_state["resultados_analisis"]
                                    
                                st.success("¡Dashboard Recargado en Memoria! Haz scroll hacia abajo para interactuar con los gráficos.")
                                st.rerun()
                            else:
                                st.error("Sin métricas para ese registro.")
                    else:
                        st.info("👈 Haz clic en una o varias filas de la tabla para inspeccionar o eliminar experimentos.")
                
            else:
                st.info("No hay experimentos en el historial aún.")
    except Exception as e:
        st.error(f"Error accediendo a la Base de Datos: {e}")

# Añadir divisor para separar de la simulación
st.markdown("<hr style='border: 1px solid rgba(15,23,42,0.1);'>", unsafe_allow_html=True)

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

# Recuperamos el DataFrame de manera segura
df = st.session_state.get("resultados_analisis")

# =============== 6. CÁLCULO DE KPIs =================
# Valores por defecto para layout seguro
resumen_zonas = None
total_tiempo = 0
tiempo_abiertos = 0
tiempo_cerrados = 0
indice_ansiedad = 0
grooming_val = 0
thigmo_val = 0
num_entradas = 0

if df is not None:
    resumen_zonas = df.groupby("Zona")["Tiempo (s)"].count() * (1 / 10)  # 10 FPS aprox
    total_tiempo = resumen_zonas.sum()
    tiempo_abiertos = resumen_zonas.filter(like="Abierto").sum()
    tiempo_cerrados = resumen_zonas.filter(like="Cerrado").sum()
    indice_ansiedad = (tiempo_abiertos / total_tiempo) * 100 if total_tiempo > 0 else 0.0

# =============== 7. PANEL DE MÉTRICAS =================
st.markdown('<div class="tt-section-title">🧬 Indicadores Clave de Ansiedad</div>', unsafe_allow_html=True)

# Si viene de DB, usamos esos valores PRIORITARIAMENTE si no hay DF o para complementar
if "db_metrics" in st.session_state:
    m = st.session_state["db_metrics"]
    # Si tenemos DF, total_tiempo ya se calculó arriba, pero DB es la verdad histórica
    # Sin embargo, para consistencia visual si acabamos de analizar, preferimos DF.
    # Aquí la lógica: Si df es None, OBLIGATORIAMENTE usamos DB.
    if df is None:
        total_tiempo = m.get("open", 0) + m.get("closed", 0) + m.get("center", 0)
        tiempo_abiertos = m.get("open", 0)
        tiempo_cerrados = m.get("closed", 0)
        grooming_val = m.get("grooming", 0)
        thigmo_val = m.get("thigmo", 0)
        indice_ansiedad = (tiempo_abiertos / total_tiempo * 100) if total_tiempo > 0 else 0
        num_entradas = m.get("num_entradas", 0)
else:
    # Si no hay DB metrics, usamos lo calculado del DF
    if df is not None:
        grooming_val = df["Grooming"].sum() * (1/10) if "Grooming" in df.columns else 0
        thigmo_val = df["Thigmotaxis"].sum() * (1/10) if "Thigmotaxis" in df.columns else 0
        
        # Cálculo aproximado de entradas a brazos abiertos
        num_entradas = 0
        if "Zona" in df.columns:
            # Detectar transiciones: (Zona actual contiene "Abierto") Y (Zona previa NO contiene "Abierto")
            is_open = df["Zona"].astype(str).str.contains("Abierto")
            entries = (is_open & (~is_open.shift(1).fillna(False))).sum()
            num_entradas = int(entries)

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

# =============== 8. GRÁFICAS INTERACTIVAS (SOLO SI HAY DATOS DETALLADOS) =================
st.write("")

def generate_zone_colors(df):
    """Genera un mapa de colores consistente basado en la identidad institucional IPN."""
    unique_zones = sorted(df["Zona"].unique())
    color_map = {}
    
    # Paletas Institucionales
    guindas = ["#6A1B2E", "#8F314A", "#4A1020", "#7A2238", "#B55A73"] # Varios tonos de guinda
    dorados = ["#C9A227", "#D4B04C", "#B2881D"] # Acento institucional
    carbones = ["#1F2937", "#374151", "#111827"] # Neutros oscuros
    grises = ["#9CA3AF", "#D1D5DB"]
    
    from itertools import cycle
    g_cyc = cycle(guindas)
    d_cyc = cycle(dorados)
    c_cyc = cycle(carbones)
    gr_cyc = cycle(grises)
    
    for zone in unique_zones:
        z_lower = zone.lower()
        if "abierto" in z_lower:
            color_map[zone] = next(g_cyc)
        elif "centro" in z_lower:
            color_map[zone] = next(d_cyc)
        elif "cerrado" in z_lower:
            color_map[zone] = next(c_cyc)
        else:
            color_map[zone] = next(gr_cyc)
            
    return color_map

if df is not None:
    # Generar colores consistentes
    zone_color_map = generate_zone_colors(df)
    
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
            color_discrete_map=zone_color_map # <--- APLICAR COLORES
        )
        fig_timeline.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=plotly_text_color),
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
        # Asegurarnos de tener resumen_zonas
        if resumen_zonas is None:
             resumen_zonas = df.groupby("Zona")["Tiempo (s)"].count() * (1 / 10)

        fig_pie = px.pie(
            names=resumen_zonas.index,
            values=resumen_zonas.values,
            hole=0.4,
            title="Preferencia de zona",
            color=resumen_zonas.index, # Importante: mapear color a los nombres
            color_discrete_map=zone_color_map # <--- APLICAR COLORES
        )
        fig_pie.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=plotly_text_color),
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
            font=dict(color=plotly_text_color),
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
        # Lazy import sklearn: solo se necesita en esta sección de ML
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

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
                font=dict(color=plotly_text_color)
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
else:
    # MENSAJE ALTERNATIVO SI NO HAY DATOS CRUDOS
    st.info("ℹ️ Estás visualizando un registro histórico sin datos de trayectoria detallados. Las gráficas de movimiento (Mapas de calor, Etogramas) solo están disponibles para el análisis recién ejecutado.")

try:
    from reporting import generate_pdf_report
except ImportError:
    # Fallback si el path no se ha refrescado en el entorno del linter
    from src.reporting import generate_pdf_report

st.write("")
st.markdown(
    '<div class="tt-section-title">📑 Reporte Final</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="tt-card">', unsafe_allow_html=True)

col_d1, col_d2 = st.columns(2)
with col_d1:
    if df is not None:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar datos crudos (CSV)",
            data=csv,
            file_name="analisis_raton.csv",
            mime="text/csv",
        )
    else:
        st.warning("Datos CSV no disponibles para este registro.")

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
            plot_paths = []
            
            # Solo generamos gráficas en el PDF si tenemos el DF para crearlas
            if df is not None:
                # 1. Guardar gráficas temporalmente
                temp_dir = "reports/temp"
                os.makedirs(temp_dir, exist_ok=True)
                
                # --- Ajustes visuales para PDF (Forzar tema claro) ---
                def prepare_for_pdf(fig):
                    fig.update_layout(
                        template="plotly_white",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font={"color": "black", "size": 14}
                    )
                    return fig
                
                # Etograma
                path_timeline = os.path.join(temp_dir, "timeline.png")
                # Se asume que fig_timeline existe porque estamos dentro del if df is not None
                try:
                    fig_timeline_pdf = prepare_for_pdf(fig_timeline)
                    fig_timeline_pdf.write_image(path_timeline, width=800, height=400, scale=2)
                    plot_paths.append(path_timeline)
                except Exception as e_plot:
                    st.warning(f"No se pudo generar la imagen del etograma: {e_plot}")
                
                # Pie Chart
                path_pie = os.path.join(temp_dir, "pie.png")
                try:
                    fig_pie_pdf = prepare_for_pdf(fig_pie)
                    fig_pie_pdf.update_traces(textfont_color="black", marker={"line": {"color": "#000000", "width": 1}})
                    fig_pie_pdf.write_image(path_pie, width=600, height=400, scale=2)
                    plot_paths.append(path_pie)
                except Exception as e_plot:
                    st.warning(f"No se pudo generar la imagen de distribución: {e_plot}")
                
                # Heatmap
                path_map = os.path.join(temp_dir, "heatmap.png")
                try:
                    fig_map_pdf = prepare_for_pdf(fig_map)
                    # Heatmap font fix
                    fig_map_pdf.update_coloraxes(colorbar_tickfont={"color": "black"})
                    fig_map_pdf.write_image(path_map, width=600, height=500, scale=2)
                    plot_paths.append(path_map)
                except Exception as e_plot:
                    st.warning(f"No se pudo generar la imagen del mapa de calor: {e_plot}")
            
            # 2. Generar PDF con gráficas (si las hay) o solo métricas
            pdf_path = generate_pdf_report(user_name, role, kpi_data, plots=plot_paths)
            
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
