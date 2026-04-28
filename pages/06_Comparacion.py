import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session, save_session
from ui_components import run_page_splash
from db.connection import get_db_engine
import importlib
import ui_theme

importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar

st.set_page_config(
    page_title="Comparación | IPN - ESCOM",
    page_icon="assets/logos/logo_ria.png",
    layout="wide"
)

load_session()
colors = use_theme()

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

role = st.session_state.get("role", "")
if role not in ["investigador", "admin"]:
    st.error("Acceso denegado. Solo investigadores y administradores.")
    st.stop()

run_page_splash(
    "page_comparacion",
    [
        "Cargando experimentos completados...",
        "Preparando herramientas de comparación...",
        "Generando visualizaciones comparativas...",
    ],
    subtitle="TT 2026 - Análisis Comparativo de Experimentos EPM",
)

# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Módulo 06: Comparación de Grupos Experimentales")
st.markdown("""
    Genera tablas consolidadas con estadísticas descriptivas por grupo de tratamiento.
    Exporta datos formateados para análisis estadístico (ANOVA, prueba t, etc.).
    **Recomendado:** 6-8 ratas por grupo para validez estadística.
""")

# ================= 3. FUNCIONES AUXILIARES =================

def format_seconds(seconds):
    """Convierte segundos a formato mm:ss"""
    if pd.isna(seconds) or seconds is None:
        return "0:00"
    seconds = float(seconds)
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def get_all_experiments():
    """Obtiene todos los experimentos completados con sus resultados"""
    engine = get_db_engine()
    if not engine:
        return pd.DataFrame()

    query = text("""
        SELECT
            e.id,
            e.rat_id,
            e.treatment,
            e.experiment_date,
            e.responsible,
            e.duration_seconds,
            ar.time_open_arms,
            ar.time_closed_arms,
            ar.time_center,
            ar.grooming_duration,
            ar.thigmotaxis_duration
        FROM experiments e
        INNER JOIN analysis_results ar ON e.id = ar.experiment_id
        WHERE e.processed = TRUE AND ar.status = 'completed'
        ORDER BY e.experiment_date DESC, e.rat_id
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df

def create_comparison_label(row):
    """Crea una etiqueta descriptiva para cada experimento"""
    date = pd.to_datetime(row['experiment_date']).strftime('%Y-%m-%d')
    return f"{row['rat_id']} | {row['treatment']} | {date}"

# ================= 4. CARGAR DATOS =================
with st.spinner("Cargando experimentos..."):
    df_experiments = get_all_experiments()

if df_experiments.empty:
    st.warning("No hay experimentos completados para comparar.")
    st.info("Completa al menos 2 experimentos en el Módulo 04: Análisis Final para usar esta función.")
    st.stop()

# Agregar columna de etiqueta
df_experiments['label'] = df_experiments.apply(create_comparison_label, axis=1)

# ================= 5. SELECCIÓN DE GRUPOS =================
st.markdown("---")
st.markdown("#### Selección Manual de Experimentos para Comparación")

st.info("""
**Instrucciones:**
1. Selecciona el **tratamiento** para cada grupo
2. Selecciona los **experimentos específicos** que deseas incluir de cada tratamiento
3. Cada grupo debe tener **entre 6 y 8 experimentos** (válido para análisis estadístico)
4. Ambos grupos **deben tener la misma cantidad** de experimentos
5. Presiona el botón **Comparar** para generar el análisis
""")

# Obtener tratamientos únicos
all_treatments = sorted(df_experiments['treatment'].unique().tolist())

if len(all_treatments) < 2:
    st.warning("Se necesitan al menos 2 tratamientos diferentes para comparar grupos.")
    st.info("Asegúrate de tener experimentos con diferentes tratamientos (ej: Control, Diazepam 5mg, etc.)")
    st.stop()

# Recuperar selecciones previas de session_state (si existen)
prev_treatment_g1 = st.session_state.get('treatment_g1', all_treatments[0])
prev_treatment_g2 = st.session_state.get('treatment_g2', all_treatments[1] if len(all_treatments) > 1 else all_treatments[0])
prev_selected_g1 = st.session_state.get('selected_g1', [])
prev_selected_g2 = st.session_state.get('selected_g2', [])

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Grupo 1")
    group1_treatment = st.selectbox(
        "Tratamiento para Grupo 1:",
        options=all_treatments,
        index=all_treatments.index(prev_treatment_g1) if prev_treatment_g1 in all_treatments else 0,
        key="selectbox_treatment_g1"
    )

    # Filtrar experimentos por tratamiento del Grupo 1
    df_group1_available = df_experiments[df_experiments['treatment'] == group1_treatment].copy()
    group1_available_labels = df_group1_available['label'].tolist()

    st.info(f"Experimentos disponibles: **{len(group1_available_labels)}**")

    # Filtrar valores previos que aún son válidos para este tratamiento
    valid_prev_g1 = [label for label in prev_selected_g1 if label in group1_available_labels]

    selected_group1_labels = st.multiselect(
        "Selecciona experimentos para Grupo 1:",
        options=group1_available_labels,
        default=valid_prev_g1 if st.session_state.get('comparison_ready', False) else [],
        key="multiselect_g1",
        help="Puedes seleccionar múltiples experimentos. Usa Ctrl+Click o Cmd+Click"
    )

    n_group1 = len(selected_group1_labels)

    if n_group1 > 0:
        if 6 <= n_group1 <= 8:
            st.success(f"Experimentos seleccionados: **{n_group1}** ✓")
        elif n_group1 < 6:
            st.warning(f"Experimentos seleccionados: **{n_group1}** (mínimo requerido: 6)")
        else:  # n_group1 > 8
            st.error(f"Experimentos seleccionados: **{n_group1}** (máximo permitido: 8)")
    else:
        st.info("Selecciona entre 6 y 8 experimentos")

with col2:
    st.markdown("##### Grupo 2")

    # Filtrar para no repetir el mismo tratamiento
    available_treatments_g2 = [t for t in all_treatments if t != group1_treatment]
    if not available_treatments_g2:
        st.error("No hay otro tratamiento disponible para comparar")
        st.stop()

    # Asegurar que el tratamiento previo sea válido
    default_treatment_g2 = prev_treatment_g2 if prev_treatment_g2 in available_treatments_g2 else available_treatments_g2[0]

    group2_treatment = st.selectbox(
        "Tratamiento para Grupo 2:",
        options=available_treatments_g2,
        index=available_treatments_g2.index(default_treatment_g2) if default_treatment_g2 in available_treatments_g2 else 0,
        key="selectbox_treatment_g2"
    )

    # Filtrar experimentos por tratamiento del Grupo 2
    df_group2_available = df_experiments[df_experiments['treatment'] == group2_treatment].copy()
    group2_available_labels = df_group2_available['label'].tolist()

    st.info(f"Experimentos disponibles: **{len(group2_available_labels)}**")

    # Filtrar valores previos que aún son válidos para este tratamiento
    valid_prev_g2 = [label for label in prev_selected_g2 if label in group2_available_labels]

    selected_group2_labels = st.multiselect(
        "Selecciona experimentos para Grupo 2:",
        options=group2_available_labels,
        default=valid_prev_g2 if st.session_state.get('comparison_ready', False) else [],
        key="multiselect_g2",
        help="Puedes seleccionar múltiples experimentos. Usa Ctrl+Click o Cmd+Click"
    )

    n_group2 = len(selected_group2_labels)

    if n_group2 > 0:
        if 6 <= n_group2 <= 8:
            st.success(f"Experimentos seleccionados: **{n_group2}** ✓")
        elif n_group2 < 6:
            st.warning(f"Experimentos seleccionados: **{n_group2}** (mínimo requerido: 6)")
        else:  # n_group2 > 8
            st.error(f"Experimentos seleccionados: **{n_group2}** (máximo permitido: 8)")
    else:
        st.info("Selecciona entre 6 y 8 experimentos")

# ================= VALIDACIÓN Y BOTÓN COMPARAR =================
st.markdown("---")

# Verificar si hay selecciones
if n_group1 == 0 or n_group2 == 0:
    st.warning("Debes seleccionar experimentos en ambos grupos antes de comparar.")
    st.stop()

# Verificar rango permitido (6-8 experimentos)
if n_group1 < 6 or n_group1 > 8:
    st.error(f"Grupo 1: Se requieren entre 6 y 8 experimentos (actualmente: {n_group1})")
    st.stop()

if n_group2 < 6 or n_group2 > 8:
    st.error(f"Grupo 2: Se requieren entre 6 y 8 experimentos (actualmente: {n_group2})")
    st.stop()

# Verificar si tienen el mismo número
if n_group1 != n_group2:
    st.error(f"Los grupos deben tener la misma cantidad de experimentos. Grupo 1: {n_group1}, Grupo 2: {n_group2}")
    st.info("Ajusta tus selecciones para que ambos grupos tengan el mismo número de experimentos.")
    st.stop()

# Validación exitosa
st.success(f"✓ Validación exitosa: Ambos grupos tienen **{n_group1}** experimento(s) seleccionado(s)")

# Botón para ejecutar la comparación
if st.button("Comparar Grupos", type="primary", use_container_width=True):
    st.session_state['comparison_ready'] = True
    st.session_state['selected_g1'] = selected_group1_labels
    st.session_state['selected_g2'] = selected_group2_labels
    st.session_state['treatment_g1'] = group1_treatment
    st.session_state['treatment_g2'] = group2_treatment
    st.rerun()

# Verificar si se ha ejecutado la comparación
if not st.session_state.get('comparison_ready', False):
    st.info("Presiona el botón 'Comparar Grupos' para generar el análisis estadístico.")
    st.stop()

# Recuperar selecciones de session_state
selected_group1_labels = st.session_state.get('selected_g1', [])
selected_group2_labels = st.session_state.get('selected_g2', [])
group1_treatment = st.session_state.get('treatment_g1', 'Grupo1')
group2_treatment = st.session_state.get('treatment_g2', 'Grupo2')

# Obtener los DataFrames correspondientes
df_group1 = df_experiments[df_experiments['label'].isin(selected_group1_labels)].copy()
df_group2 = df_experiments[df_experiments['label'].isin(selected_group2_labels)].copy()

# Combinar datos de ambos grupos
df_comparison = pd.concat([df_group1, df_group2], ignore_index=True)
df_comparison['Grupo'] = 'Grupo 1'
df_comparison.loc[df_comparison['label'].isin(selected_group2_labels), 'Grupo'] = 'Grupo 2'

# ================= 6. TABLA DE DATOS INDIVIDUALES =================
st.markdown("---")

# Botón para reiniciar comparación
col_title, col_reset = st.columns([4, 1])
with col_title:
    st.markdown("#### Datos Individuales por Sujeto")
with col_reset:
    if st.button("Nueva Comparación", type="secondary"):
        st.session_state['comparison_ready'] = False
        st.session_state.pop('selected_g1', None)
        st.session_state.pop('selected_g2', None)
        st.session_state.pop('treatment_g1', None)
        st.session_state.pop('treatment_g2', None)
        st.rerun()

# Mostrar resumen de selección
with st.expander("Resumen de Experimentos Seleccionados", expanded=False):
    col_sum1, col_sum2 = st.columns(2)
    with col_sum1:
        st.markdown(f"**Grupo 1: {group1_treatment}**")
        for label in selected_group1_labels:
            st.markdown(f"- {label}")
    with col_sum2:
        st.markdown(f"**Grupo 2: {group2_treatment}**")
        for label in selected_group2_labels:
            st.markdown(f"- {label}")

# Preparar datos para visualización
display_df = df_comparison[[
    'Grupo', 'rat_id', 'treatment', 'experiment_date',
    'time_open_arms', 'time_closed_arms', 'time_center',
    'grooming_duration', 'thigmotaxis_duration'
]].copy()

# Renombrar columnas
display_df.columns = [
    'Grupo', 'ID Ratón', 'Tratamiento', 'Fecha',
    'T. Abiertos (s)', 'T. Cerrados (s)', 'T. Centro (s)',
    'Grooming (s)', 'Tigmotaxis (s)'
]

# Formatear fecha
display_df['Fecha'] = pd.to_datetime(display_df['Fecha']).dt.strftime('%Y-%m-%d')

# Mostrar tabla
st.dataframe(
    display_df.style.background_gradient(subset=[
        'T. Abiertos (s)', 'T. Cerrados (s)', 'T. Centro (s)',
        'Grooming (s)', 'Tigmotaxis (s)'
    ], cmap='RdYlGn', axis=0),
    use_container_width=True,
    hide_index=True
)

# ================= 7. ESTADÍSTICAS DESCRIPTIVAS POR GRUPO =================
st.markdown("---")
st.markdown("#### Estadísticas Descriptivas por Grupo")
st.markdown("Tabla consolidada para análisis estadístico (ANOVA, prueba t)")

# Variables de interés
metrics = {
    'time_open_arms': 'Tiempo Brazos Abiertos (s)',
    'time_closed_arms': 'Tiempo Brazos Cerrados (s)',
    'time_center': 'Tiempo Centro (s)',
    'grooming_duration': 'Grooming (s)',
    'thigmotaxis_duration': 'Tigmotaxis (s)'
}

# Calcular estadísticas por grupo y métrica
stats_data = []

for metric_col, metric_name in metrics.items():
    for group_name in ['Grupo 1', 'Grupo 2']:
        group_data = df_comparison[df_comparison['Grupo'] == group_name][metric_col].dropna()

        n = len(group_data)
        mean = group_data.mean() if n > 0 else 0
        std = group_data.std() if n > 1 else 0
        sem = std / (n ** 0.5) if n > 1 else 0  # Error estándar de la media
        min_val = group_data.min() if n > 0 else 0
        max_val = group_data.max() if n > 0 else 0

        treatment = group1_treatment if group_name == 'Grupo 1' else group2_treatment

        stats_data.append({
            'Variable': metric_name,
            'Grupo': group_name,
            'Tratamiento': treatment,
            'N': n,
            'Media': round(mean, 2),
            'Desv. Est.': round(std, 2),
            'Error Est.': round(sem, 2),
            'Mínimo': round(min_val, 2),
            'Máximo': round(max_val, 2)
        })

df_stats = pd.DataFrame(stats_data)

# Mostrar tabla de estadísticas
st.dataframe(
    df_stats,
    use_container_width=True,
    hide_index=True
)

# ================= 8. COMPARACIÓN VISUAL =================
st.markdown("---")
st.markdown("#### Comparación Visual de Grupos")

tab1, tab2 = st.tabs([
    "Barras con Error",
    "Comparación Métrica Individual"
])

with tab1:
    st.markdown("##### Comparación de Medias con Barras de Error")

    # Selector de métrica
    selected_metric_name = st.selectbox(
        "Selecciona una métrica:",
        list(metrics.values()),
        key="metric_visual"
    )

    # Obtener columna correspondiente
    metric_col = [k for k, v in metrics.items() if v == selected_metric_name][0]

    # Filtrar datos para la métrica seleccionada
    df_plot = df_stats[df_stats['Variable'] == selected_metric_name].copy()

    # Crear gráfico de barras con error
    fig_bars = go.Figure()

    colors_group = {
        'Grupo 1': colors['primary'],
        'Grupo 2': colors['success']
    }

    for grupo in ['Grupo 1', 'Grupo 2']:
        data_grupo = df_plot[df_plot['Grupo'] == grupo]
        if not data_grupo.empty:
            fig_bars.add_trace(go.Bar(
                name=f"{grupo} ({data_grupo['Tratamiento'].iloc[0]})",
                x=[grupo],
                y=data_grupo['Media'],
                error_y=dict(
                    type='data',
                    array=data_grupo['Desv. Est.'],
                    visible=True
                ),
                marker_color=colors_group[grupo],
                text=data_grupo['Media'].round(2),
                textposition='outside'
            ))

    fig_bars.update_layout(
        title=f'{selected_metric_name} - Comparación de Grupos',
        yaxis_title=selected_metric_name,
        xaxis_title='Grupo',
        showlegend=True,
        height=500,
        barmode='group'
    )

    st.plotly_chart(fig_bars, use_container_width=True)

    # Mostrar N de cada grupo
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        n1 = df_plot[df_plot['Grupo'] == 'Grupo 1']['N'].iloc[0]
        st.metric("N Grupo 1", n1)
    with col_n2:
        n2 = df_plot[df_plot['Grupo'] == 'Grupo 2']['N'].iloc[0]
        st.metric("N Grupo 2", n2)

with tab2:
    st.markdown("##### Comparación Detallada")

    # Tabla comparativa lado a lado
    comparison_table = []

    for metric_name in metrics.values():
        group1_data = df_stats[(df_stats['Variable'] == metric_name) & (df_stats['Grupo'] == 'Grupo 1')]
        group2_data = df_stats[(df_stats['Variable'] == metric_name) & (df_stats['Grupo'] == 'Grupo 2')]

        if not group1_data.empty and not group2_data.empty:
            diff = group2_data['Media'].iloc[0] - group1_data['Media'].iloc[0]
            pct_diff = (diff / group1_data['Media'].iloc[0] * 100) if group1_data['Media'].iloc[0] != 0 else 0

            comparison_table.append({
                'Variable': metric_name,
                f'Grupo 1 Media±DE': f"{group1_data['Media'].iloc[0]:.2f} ± {group1_data['Desv. Est.'].iloc[0]:.2f}",
                f'Grupo 2 Media±DE': f"{group2_data['Media'].iloc[0]:.2f} ± {group2_data['Desv. Est.'].iloc[0]:.2f}",
                'Diferencia': f"{diff:+.2f}",
                '% Cambio': f"{pct_diff:+.1f}%"
            })

    df_comparison_table = pd.DataFrame(comparison_table)
    st.dataframe(df_comparison_table, use_container_width=True, hide_index=True)

# ================= 9. EXPORTAR CONSOLIDADO PARA ANÁLISIS ESTADÍSTICO =================
st.markdown("---")
st.markdown("#### Exportar Consolidado para Análisis Estadístico")

st.info("""
**Formato de Exportación:**
- **Hoja 1 (Datos Individuales):** Datos crudos de cada sujeto experimental
- **Hoja 2 (Estadísticas por Grupo):** Media, Desviación Estándar, Error Estándar, N
- **Hoja 3 (Resumen Comparativo):** Diferencias entre grupos
- **Formato compatible** con SPSS, R, GraphPad Prism, JASP
""")

# Preparar datos para exportación
from io import BytesIO

# Hoja 1: Datos individuales
df_individual_export = df_comparison[[
    'Grupo', 'rat_id', 'treatment', 'experiment_date',
    'time_open_arms', 'time_closed_arms', 'time_center',
    'grooming_duration', 'thigmotaxis_duration'
]].copy()

df_individual_export.columns = [
    'Grupo', 'ID_Raton', 'Tratamiento', 'Fecha',
    'Tiempo_Brazos_Abiertos_s', 'Tiempo_Brazos_Cerrados_s', 'Tiempo_Centro_s',
    'Grooming_s', 'Tigmotaxis_s'
]

# Hoja 2: Estadísticas descriptivas por grupo
df_stats_export = df_stats.copy()

# Hoja 3: Resumen comparativo
summary_data = []
for metric_name in metrics.values():
    group1_data = df_stats[(df_stats['Variable'] == metric_name) & (df_stats['Grupo'] == 'Grupo 1')]
    group2_data = df_stats[(df_stats['Variable'] == metric_name) & (df_stats['Grupo'] == 'Grupo 2')]

    if not group1_data.empty and not group2_data.empty:
        diff = group2_data['Media'].iloc[0] - group1_data['Media'].iloc[0]
        pct_diff = (diff / group1_data['Media'].iloc[0] * 100) if group1_data['Media'].iloc[0] != 0 else 0

        # Calcular tamaño del efecto (Cohen's d)
        pooled_std = ((group1_data['Desv. Est.'].iloc[0]**2 + group2_data['Desv. Est.'].iloc[0]**2) / 2) ** 0.5
        cohens_d = diff / pooled_std if pooled_std > 0 else 0

        summary_data.append({
            'Variable': metric_name,
            'Tratamiento_1': group1_treatment,
            'Media_Grupo_1': group1_data['Media'].iloc[0],
            'DE_Grupo_1': group1_data['Desv. Est.'].iloc[0],
            'N_Grupo_1': group1_data['N'].iloc[0],
            'Tratamiento_2': group2_treatment,
            'Media_Grupo_2': group2_data['Media'].iloc[0],
            'DE_Grupo_2': group2_data['Desv. Est.'].iloc[0],
            'N_Grupo_2': group2_data['N'].iloc[0],
            'Diferencia_Medias': round(diff, 2),
            'Pct_Cambio': round(pct_diff, 2),
            'Cohens_d': round(cohens_d, 3)
        })

df_summary_export = pd.DataFrame(summary_data)

# Crear archivo Excel con múltiples hojas
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    # Hoja 1: Datos individuales
    df_individual_export.to_excel(writer, index=False, sheet_name='Datos_Individuales')

    # Hoja 2: Estadísticas por grupo
    df_stats_export.to_excel(writer, index=False, sheet_name='Estadisticas_Descriptivas')

    # Hoja 3: Resumen comparativo
    df_summary_export.to_excel(writer, index=False, sheet_name='Resumen_Comparativo')

    # Hoja 4: Metadata
    metadata = pd.DataFrame({
        'Campo': ['Fecha_Exportacion', 'Grupo_1', 'Grupo_2', 'N_Grupo_1', 'N_Grupo_2',
                  'Usuario', 'Sistema'],
        'Valor': [
            pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            group1_treatment,
            group2_treatment,
            len(df_group1),
            len(df_group2),
            st.session_state.get('user_name', 'Desconocido'),
            'EPM Sistema TT2026 IPN-ESCOM'
        ]
    })
    metadata.to_excel(writer, index=False, sheet_name='Metadata')

    # Ajustar ancho de columnas automáticamente en todas las hojas
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                except:
                    pass

            # Ajustar ancho con un margen adicional
            adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres de ancho
            worksheet.column_dimensions[column_letter].width = adjusted_width

excel_data = buffer.getvalue()

col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    st.download_button(
        label="Descargar Consolidado Excel (Completo)",
        data=excel_data,
        file_name=f"consolidado_{group1_treatment}_vs_{group2_treatment}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    st.caption("4 hojas: Datos individuales, Estadísticas, Resumen comparativo, Metadata")

with col_exp2:
    # CSV simplificado (solo estadísticas)
    csv_stats = df_stats_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar Estadísticas (CSV)",
        data=csv_stats,
        file_name=f"estadisticas_{group1_treatment}_vs_{group2_treatment}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    st.caption("Tabla de estadísticas descriptivas solamente")

# ================= 10. RECOMENDACIONES PARA ANÁLISIS =================
st.markdown("---")
st.markdown("#### Guía para Análisis Estadístico")

with st.expander(" Recomendaciones para Pruebas Estadísticas"):
    col_guide1, col_guide2 = st.columns(2)

    with col_guide1:
        st.markdown("**Pruebas Paramétricas:**")
        st.markdown("""
        - **Prueba t de Student** (2 grupos)
          - Verificar normalidad (Shapiro-Wilk)
          - Verificar homogeneidad de varianzas (Levene)
          - Si N₁ ≈ N₂ y datos normales

        - **ANOVA de una vía** (>2 grupos)
          - Comparar múltiples tratamientos
          - Post-hoc: Tukey, Bonferroni
        """)

    with col_guide2:
        st.markdown("**Pruebas No Paramétricas:**")
        st.markdown("""
        - **U de Mann-Whitney** (2 grupos)
          - Alternativa a t de Student
          - No requiere normalidad
          - Datos ordinales o no normales

        - **Kruskal-Wallis** (>2 grupos)
          - Alternativa a ANOVA
          - Post-hoc: Dunn
        """)

    st.markdown("---")
    st.markdown("**Interpretación del Tamaño del Efecto (Cohen's d):**")
    st.markdown("""
    - **|d| < 0.2:** Efecto trivial
    - **0.2 ≤ |d| < 0.5:** Efecto pequeño
    - **0.5 ≤ |d| < 0.8:** Efecto mediano
    - **|d| ≥ 0.8:** Efecto grande
    """)

    st.markdown("---")
    st.markdown("**Software Recomendado:**")
    st.markdown("""
    - **SPSS:** Import Excel → Analyze → Compare Means → Independent Samples t-test
    - **R:** `t.test()`, `aov()`, `TukeyHSD()`
    - **GraphPad Prism:** Importar hoja "Datos_Individuales" → Column Stats
    - **JASP:** Importar CSV → T-Tests → Independent Samples
    - **Python:** `scipy.stats.ttest_ind()`, `scipy.stats.f_oneway()`
    """)

# ================= 11. NOTAS Y CONCLUSIONES =================
# ================= 11. NOTAS Y CONCLUSIONES =================
st.markdown("---")
st.markdown("#### Observaciones y Conclusiones del Análisis")

notes = st.text_area(
    "Registra observaciones, interpretaciones o hallazgos relevantes:",
    height=150,
    placeholder="Ej: Los sujetos del grupo Diazepam 5mg muestran un aumento significativo en tiempo de brazos abiertos (p < 0.05), sugiriendo efecto ansiolítico. Se recomienda prueba t de Student para confirmación estadística..."
)

if st.button(" Guardar Notas", type="primary"):
    if notes.strip():
        st.session_state[f'comparison_notes_{group1_treatment}_vs_{group2_treatment}'] = {
            'notes': notes,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'grupo1': group1_treatment,
            'grupo2': group2_treatment
        }
        st.success(" Notas guardadas en la sesión actual.")
    else:
        st.warning("No hay notas para guardar.")

st.markdown("---")
