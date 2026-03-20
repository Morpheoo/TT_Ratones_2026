import streamlit as st
import base64
import os
import sys

# ================= 0. PERSISTENCIA Y GUARDIA CPU =================
# Seteamos la ruta de src para importar utilerías
sys.path.append(os.path.join(os.getcwd(), "src"))
from session_utils import load_session, save_session
from sidebar_control import apply_sidebar_visibility

# La guardia DEBE estar antes de cualquier import de torch/dlc
if "init_done" not in st.session_state:
    load_session()
    st.session_state.init_done = True

# Inicializar dlc_device_opt si no existe
if "dlc_device_opt" not in st.session_state:
    st.session_state.dlc_device_opt = "Auto (Recomendado)"

# ================= ENTORNO Y SEGURIDAD =================
# Verificar que estemos usando el entorno correcto (3.11 para DLC)
if not sys.version.startswith("3.11"):
    st.error(f"⚠️ **ENTORNO INCORRECTO**: Estás usando Python {sys.version.split()[0]}.")
    st.info("Para usar DeepLabCut, debes cerrar esta pestaña y ejecutar la aplicación desde el entorno `venv_311`.")
    st.code(f"Usa el comando: .\\venv_311\\Scripts\\python.exe -m streamlit run Home.py")
    if not st.checkbox("Continuar de todos modos (DLC no funcionará)"):
        st.stop()

# ESCUDO ANTI-CUDA (Para RTX 5060 / Blackwell)
# Si el usuario eligió CPU, forzamos a TODO el ecosistema Python a ignorar la GPU
if st.session_state.get("dlc_device_opt") == "CPU (Forzar)":
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
    try:
        import torch
        # Se confía en CUDA_VISIBLE_DEVICES para deshabilitar GPU
    except ImportError:
        pass

# ================= 1. CONFIGURACIÓN =================
st.set_page_config(
    page_title="TT Ratones 2026 - Home",
    page_icon="logo_ria_desktop.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 2. TEMA Y ESTILOS =================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Oscuro"

theme_mode = st.sidebar.radio(
    "Tema de la interfaz",
    ["Claro", "Oscuro"],
    index=0 if st.session_state.get("theme_mode", "Oscuro") == "Claro" else 1,
)
st.session_state.theme_mode = theme_mode

# Estado de Hardware
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Estado de Hardware")

force_cpu = st.session_state.get("dlc_device_opt") == "CPU (Forzar)"

if force_cpu:
    st.sidebar.success("🛡️ MODO SEGURO: GPU Deshabilitada")
    st.sidebar.caption("PyTorch reporta: CPU Only")
else:
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            st.sidebar.info(f"🚀 GPU Activa: {gpu_name}")
        else:
            st.sidebar.warning("⚠️ No se detectó GPU CUDA")
    except:
        st.sidebar.error("❌ Error detectando hardware")

st.sidebar.markdown("---")

if st.sidebar.button("Cerrar Sesión"):
    from session_utils import clear_session
    clear_session()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

device_cpu = st.sidebar.toggle(
    "Modo Alta Estabilidad (CPU)", 
    value=(st.session_state.dlc_device_opt == "CPU (Forzar)"),
    help="Recomendado para RTX 5060 para evitar errores de CUDA."
)

new_device = "CPU (Forzar)" if device_cpu else "Auto (Recomendado)"
if new_device != st.session_state.dlc_device_opt:
    st.session_state.dlc_device_opt = new_device
    save_session()
    st.sidebar.warning("⚠️ El cambio de hardware requiere reiniciar la app para aplicarse al 100%.")

save_session() # Guardar estado al cambiar tema o device

# ================= CONTROL DE NAVEGACIÓN POR ROL =================
# Aplicar control de sidebar basado en rol
apply_sidebar_visibility()

# Definición de paletas
if theme_mode == "Claro":
    colors = {
        "page_bg": "#d1fae5",
        "card_bg": "#ecfdf5",
        "text_main": "#064e3b",
        "text_sub": "#047857",
        "title": "#065f46",
        "shadow": "rgba(15, 23, 42, 0.1)",
        "border": "#6ee7b7",
        "hover": "#dcfce7",
        "icon": "#10b981",
        "hero_bg": "linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)",
    }
else:  # Oscuro
    colors = {
        "page_bg": "#022c22",
        "card_bg": "#064e3b",
        "text_main": "#ecfdf5",
        "text_sub": "#d1fae5",
        "title": "#ffffff",
        "shadow": "rgba(0,0,0,0.4)",
        "border": "#047857",
        "hover": "#065f46",
        "icon": "#34d399",
        "hero_bg": "linear-gradient(135deg, #064e3b 0%, #022c22 100%)",
    }

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

    /* HERO SECTION */
    .hero-container {{
        background: {colors["hero_bg"]};
        padding: 4rem 2rem;
        border-radius: 24px;
        text-align: center;
        box-shadow: 0 10px 30px {colors["shadow"]};
        margin-bottom: 3rem;
        border: 1px solid {colors["border"]};
        animation: fadeIn 0.8s ease-in-out;
    }}
    
    .hero-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 900;
        font-size: 3rem;
        color: {colors["title"]};
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }}
    
    .hero-subtitle {{
        font-size: 1.25rem;
        color: {colors["text_sub"]};
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }}

    /* GRID DE MÓDULOS */
    .modules-container {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        padding: 1rem;
    }}

    .module-card {{
        background-color: {colors["card_bg"]};
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 6px {colors["shadow"]};
        border: 1px solid {colors["border"]};
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }}

    .module-card:hover {{
        transform: translateY(-8px);
        box-shadow: 0 20px 25px {colors["shadow"]};
        border-color: {colors["icon"]};
    }}

    .card-icon {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: {colors["icon"]};
    }}

    .card-title {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {colors["text_main"]};
        margin-bottom: 0.8rem;
    }}

    .card-desc {{
        font-size: 0.95rem;
        color: {colors["text_sub"]};
        line-height: 1.6;
        opacity: 0.9;
    }}

    /* ANIMACIONES */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* CHECK SESIÓN */
    .session-box {{
        background-color: {colors["card_bg"]};
        padding: 1rem 2rem;
        border-radius: 50px;
        border: 1px solid {colors["border"]};
        display: inline-block;
        margin-top: 1rem;
        box-shadow: 0 4px 6px {colors["shadow"]};
    }}
    .session-text {{
        color: {colors["text_main"]};
        font-weight: 600;
    }}

    /* FOOTER */
    .footer {{
        text-align: center;
        margin-top: 4rem;
        padding: 2rem;
        color: {colors["text_sub"]};
        font-size: 0.85rem;
        border-top: 1px solid {colors["border"]};
    }}
    /* STATUS BADGES */
    .status-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }}
    .status-item {{
        background: {colors["card_bg"]};
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid {colors["border"]};
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }}
    .status-dot {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }}
    .status-ok {{ background-color: #10b981; box-shadow: 0 0 10px #10b981; }}
    .status-error {{ background-color: #ef4444; box-shadow: 0 0 10px #ef4444; }}
    .status-warn {{ background-color: #f59e0b; box-shadow: 0 0 10px #f59e0b; }}
    
    .status-label {{
        font-size: 0.85rem;
        font-weight: 600;
        color: {colors["text_main"]};
    }}
    .status-val {{
        font-size: 0.75rem;
        color: {colors["text_sub"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ================= 3. LOGIC & ASSETS =================
def get_img_as_base64(file_path: str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Logo
# Logo
LOGO_PATH = "logo_ria_desktop.png"
img_base64 = get_img_as_base64(LOGO_PATH)
if img_base64:
    logo_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 120px; margin-bottom: 1.5rem;">'
else:
    logo_html = '<div style="font-size: 3rem;">🐁</div>'

# ================= 4. LAYOUT =================

# HERO
st.markdown(
    f"""
    <div class="hero-container">
        {logo_html}
        <div class="hero-title">TT Ratones 2026</div>
        <div class="hero-subtitle">
            Sistema Automatizado de Análisis de Comportamiento en Modelos de Ansiedad (EPM)
            mediante Visión Artificial e Inteligencia Artificial.
        </div>
        {'<div style="margin-top: 2rem;"><span class="session-box"><span class="session-text">✅ Sesión Activa: ' + st.session_state.user + '</span></span></div>' if st.session_state.get("logged_in") else ''}
    </div>
    """,
    unsafe_allow_html=True
)

# ================= 5. DIAGNÓSTICO DE SISTEMA =================
def check_system_status():
    status = {}
    try:
        import subprocess
        # creationflags=0x08000000 evita ventanas de consola en Windows
        subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, creationflags=0x08000000)
        status["docker"] = ("OK", "status-ok", "Docker Desktop activo")
    except:
        status["docker"] = ("Error", "status-error", "Docker no detectado")
    try:
        from src.db.connection import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["db"] = ("OK", "status-ok", "PostgreSQL conectado")
        else:
            status["db"] = ("Error", "status-error", "Motor SQL no creado")
    except:
        status["db"] = ("Error", "status-error", "Error de conexión SQL")
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            status["gpu"] = ("CUDA", "status-ok", name)
        else:
            status["gpu"] = ("CPU", "status-warn", "Sin aceleración GPU")
    except:
        status["gpu"] = ("N/A", "status-error", "Torch no cargado")
    return status

sys_status = check_system_status()

st.markdown(f"""
<div class="status-grid">
    <div class="status-item">
        <div class="status-dot {sys_status['docker'][1]}"></div>
        <div>
            <div class="status-label">Docker Container</div>
            <div class="status-val">{sys_status['docker'][2]}</div>
        </div>
    </div>
    <div class="status-item">
        <div class="status-dot {sys_status['db'][1]}"></div>
        <div>
            <div class="status-label">Base de Datos</div>
            <div class="status-val">{sys_status['db'][2]}</div>
        </div>
    </div>
    <div class="status-item">
        <div class="status-dot {sys_status['gpu'][1]}"></div>
        <div>
            <div class="status-label">Motor de IA</div>
            <div class="status-val">{sys_status['gpu'][2]}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


if not st.session_state.get("logged_in"):
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="background-color: {colors['card_bg']}; display: inline-block; padding: 10px 20px; border-radius: 10px; border: 1px solid {colors['border']};">
                <span style="color: {colors['text_main']};">🔒 Para acceder a las funciones, por favor inicie sesión en el módulo <strong>Login</strong>.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# GRID DE TARJETAS
# Usamos HTML/CSS Grid personalizado para mejor respuesta que st.columns
st.markdown('<div class="modules-container">', unsafe_allow_html=True)

# Módulo 0
st.markdown(
    f"""
    <div class="module-card">
        <div class="card-icon">🔐</div>
        <div class="card-title">00 · Control de Acceso</div>
        <div class="card-desc">
            Seguridad y gestión de usuarios. Autenticación de investigadores y administradores para proteger los datos experimentales y configurar permisos de uso.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Módulo 1
st.markdown(
    f"""
    <div class="module-card">
        <div class="card-icon">📥</div>
        <div class="card-title">01 · Ingesta de Video</div>
        <div class="card-desc">
            Módulo de carga y preprocesamiento. Permite subir grabaciones experimentales (MP4, AVI) y realizar recortes temporales precisos para aislar la sesión de prueba.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Módulo 2
st.markdown(
    f"""
    <div class="module-card">
        <div class="card-icon">⚙️</div>
        <div class="card-title">02 · Configuración de Zonas</div>
        <div class="card-desc">
            Interfaz interactiva para definir las Regiones de Interés (ROI) sobre el laberinto: Brazos Abiertos, Cerrados y Centro. Ajuste automático a la resolución.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Módulo 3
st.markdown(
    f"""
    <div class="module-card">
        <div class="card-icon">🧠</div>
        <div class="card-title">03 · Análisis IA</div>
        <div class="card-desc">
            Motor de procesamiento basado en YOLO. Detecta al espécimen frame a frame, traza su trayectoria y clasifica su comportamiento en tiempo real.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Módulo 4
st.markdown(
    f"""
    <div class="module-card">
        <div class="card-icon">📊</div>
        <div class="card-title">04 · Resultados</div>
        <div class="card-desc">
            Dashboard de analítica avanzada. Visualiza mapas de calor, gráficos de permanencia, índices de ansiedad y permite exportar reportes detallados.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)

# FOOTER
st.markdown(
    f"""
    <div class="footer">
        ESCOM - Instituto Politécnico Nacional<br>
        <strong>Trabajo Terminal 2026</strong><br>
        2025 © Todos los derechos reservados
    </div>
    """,
    unsafe_allow_html=True
)
