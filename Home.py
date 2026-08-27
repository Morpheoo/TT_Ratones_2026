import streamlit as st
import os
import sys

# ================= 0. PERSISTENCIA Y CONFIG =================
sys.path.append(os.path.join(os.getcwd(), "src"))
from session_utils import load_session, save_session, clear_session
from ui_components import run_page_splash

st.set_page_config(
    page_title="Inicio",
    page_icon="assets/logos/logo_ria.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar sesión primero para obtener vars como logged_in
if "init_done" not in st.session_state:
    load_session()
    st.session_state.init_done = True

import importlib
import ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar, inject_sidebar_profile, render_footer
colors = use_theme()

# ================= 1. VERIFICAR LOGIN Y SIDEBAR =================
if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

run_page_splash(
    "page_home",
    [
        "Recuperando sesión institucional...",
        "Sincronizando panel principal...",
        "Preparando módulos del prototipo...",
    ],
    subtitle="Cargando tablero principal...",
)

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
    
    # Inyectar navegación y branding (con botón de Admin Panel para admins)
    inject_sidebar_profile(show_admin_button=True)

# ================= 2. TOPBAR ESTRUCTURA =================
render_topbar()

# Íconos SVG consistentes
svg_docker = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>'
svg_db = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>'
svg_ai = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>'
svg_user = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
svg_arrow = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>'
svg_video = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>'
svg_keypoints = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>'
svg_zones = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>'
svg_analysis = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>'
svg_chart = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>'
svg_compare = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>'
svg_admin = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>'
svg_warn = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#B7791F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
svg_cpu = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect></svg>'


# ================= 3. ENCABEZADO DE BIENVENIDA =================
user_name_raw = st.session_state.get("user_name", "Investigador")
user_first_name = user_name_raw
if "@" in user_name_raw:
    name_part = user_name_raw.split("@")[0]
    import re
    name_part = re.sub(r'\d+', '', name_part)
    if name_part.lower() == "hportocarrero":
        user_first_name = "Habid"
    else:
        user_first_name = name_part.capitalize()
else:
    user_first_name = user_name_raw.split(" ")[0].capitalize()

# ================= 4. ESTRUCTURA PRINCIPAL =================
st.markdown(f"""
<div style="margin-bottom: 2rem;">
    <h1 style="font-size: 2rem; margin: 0; color: {colors['text_main']}; letter-spacing: -0.02em;">¡Bienvenido, {user_first_name}!</h1>
    <p style="color: {colors['text_sub']}; font-size: 0.95rem; margin-top: 0.4rem; max-width: 800px;">
        Plataforma institucional para análisis automatizado y visualización de comportamiento en modelos de ansiedad.
    </p>
</div>
""", unsafe_allow_html=True)

# --- KPIs ---
c1, c2, c3 = st.columns(3)

def kpi_card(col, icon, title, main_status, sub_status, ok=True):
    dot_class = "status-ok" if ok else "status-warn"
    with col:
        st.markdown(f"""
<div class="kpi-container" style="padding: 1rem; margin-bottom: 2rem;">
    <div class="kpi-icon" style="flex-shrink:0;">{icon}</div>
    <div class="kpi-info" style="overflow:hidden;">
        <h4 style="margin-bottom:0.2rem; white-space:nowrap; text-overflow:ellipsis;">{title}</h4>
        <p style="font-size:0.75rem; white-space:nowrap; text-overflow:ellipsis;"><span class="status-dot {dot_class}"></span>{main_status}</p>
        <p style="font-size:0.65rem; opacity:0.7; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{sub_status}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Checks de estado del sistema (dinámicos) ---
import subprocess

# 1. Docker
docker_ok = False
docker_sub = "Docker no disponible"
offline_mode = False
try:
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))
    from db.connection import is_offline_mode
    offline_mode = is_offline_mode()
    if offline_mode:
        docker_ok = True
        docker_sub = "SQLite integrado"
    else:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            containers = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            docker_ok = len(containers) > 0
            docker_sub = f"{containers[0]}" if containers else "Sin contenedores activos"
        else:
            docker_sub = "Docker no responde"
except Exception:
    docker_sub = "Docker no detectado"

# 2. Base de datos
db_ok = False
db_sub = "Sin conexión"
try:
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))
    from db.connection import get_db_engine
    engine = get_db_engine()
    if engine:
        from sqlalchemy import text as sqltxt
        with engine.connect() as conn:
            conn.execute(sqltxt("SELECT 1"))
        db_ok = True
        db_sub = "SQLite local" if offline_mode else "PostgreSQL sincronizado"
    else:
        db_sub = "Motor no disponible"
except Exception as e:
    db_sub = "Error de conexión"

# 3. GPU
gpu_active = False
gpu_name = "CPU (sin GPU)"
try:
    import torch
    gpu_active = torch.cuda.is_available()
    if gpu_active:
        gpu_name = torch.cuda.get_device_name(0)
except Exception:
    pass

kpi_card(c1, svg_docker,
         "Almacenamiento" if offline_mode else "Docker",
         "Local" if offline_mode else ("Activo" if docker_ok else "Inactivo"),
         docker_sub,
         docker_ok)

kpi_card(c2, svg_db,
         "Base de datos",
         "Conectado" if db_ok else "Desconectado",
         db_sub,
         db_ok)

kpi_card(c3, svg_ai,
         "Motor de IA",
         "GPU activa" if gpu_active else "CPU habilitado",
         gpu_name,
         gpu_active)

# --- BANNER PRINCIPAL ---
svg_flask = '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.31M14 9.3V1.99M8.5 2h7M14 9.3a6.5 6.5 0 1 1-4 0M5.52 16h12.96"></path></svg>'

st.markdown(f"""
<div style="background:{colors['bg_card']}; border: 1px solid {colors['border']}; border-left: 5px solid {colors['primary']}; border-radius: 8px; padding: 1.5rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 2.5rem;">
    <div style="display:flex; align-items:center; gap: 15px;">
        <div style="color:{colors['primary']}; font-size: 2rem; background: {colors['accent_bg']}; padding: 12px; border-radius: 8px; display:flex;">
            {svg_flask}
        </div>
        <div>
            <h4 style="margin:0; font-size: 1.15rem; color: {colors['text_main']}; font-weight: 700;">Prototipo listo para análisis</h4>
            <p style="margin:0; font-size: 0.85rem; color: {colors['text_sub']}; margin-top: 4px;">Todos los módulos están operativos. Ingresa un video para comenzar.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- MODULOS GRID ---
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h3 style="margin:0; font-size:1.25rem; font-weight: 700; color: {colors['text_main']}; letter-spacing: -0.01em;">Módulos principales</h3>
    <p style="margin:0; font-size:0.85rem; color: {colors['text_sub']}; margin-top: 4px;">Flujo de análisis automatizado de comportamiento</p>
</div>
""", unsafe_allow_html=True)

def module_card(icon, title, desc, btn_key, btn_label, target_page):
    st.markdown(f"""
<div class="dash-card" style="margin-bottom: 1.2rem;">
    <div class="dash-card-header">
        <div class="dash-card-icon" style="background: {colors['accent_bg']}; color: {colors['primary']}; padding: 10px; border-radius: 6px;">{icon}</div>
        <h4 class="dash-card-title">{title}</h4>
    </div>
    <div class="dash-card-body" style="color: {colors['text_sub']}; padding-left: 2px;">{desc}</div>
""", unsafe_allow_html=True)
    col_space, col_b = st.columns([1, 1])
    with col_b:
        if st.button(btn_label + " →", key=btn_key, use_container_width=True, type="primary"):
            st.switch_page(target_page)
    st.markdown('</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1:
    module_card(svg_video, "Ingesta de video", "Sube y procesa tus videos experimentales", "btn_m1", "Comenzar", "pages/01_Ingesta_de_Video.py")
with m2:
    module_card(svg_keypoints, "Extracción de keypoints", "Detección y marcaje de puntos corporales.", "btn_m2", "Procesar", "pages/02_Keypoints.py")
with m3:
    module_card(svg_zones, "Configuración de zonas", "Define regiones de interés del EPM", "btn_m3", "Configurar", "pages/03_Configuracion_Zonas.py")

m4, m5, m6 = st.columns(3)
with m4:
    module_card(svg_analysis, "Análisis final", "Ejecución del modelo YOLO + LSTM", "btn_m4", "Analizar", "pages/04_Analisis_Final.py")
with m5:
    module_card(svg_chart, "Resultados y estadísticas", "Métricas, heatmaps y reportes", "btn_m5", "Ver resultados", "pages/05_Resultados_y_Estadisticas.py")
with m6:
    module_card(svg_compare, "Comparación de grupos", "Consolidado estadístico para ANOVA", "btn_m6", "Comparar", "pages/06_Comparacion.py")

# Módulos administrativos
if st.session_state.get("role") == "admin":
    m7, m8, m9 = st.columns(3)
    with m7:
        module_card(svg_user, "Panel de administración", "Gestión de usuarios e investigadores.", "btn_m7", "Administrar", "pages/99_Admin_Panel.py")
    with m8:
        st.empty()
    with m9:
        st.empty()

render_footer()
