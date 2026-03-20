import streamlit as st
import base64
import os
import sys
import time

# ================= 0. PERSISTENCIA Y GUARDIA CPU =================
# Seteamos la ruta de src para importar utilerías
sys.path.append(os.path.join(os.getcwd(), "src"))
from session_utils import load_session, save_session, clear_session
from ui_components import generic_splash_loader

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
from ui_theme import use_theme
colors = use_theme()

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

st.markdown(
    """
    <style>
    /* HERO SECTION */
    .hero-container {
        background: var(--card-bg);
        padding: 4rem 2rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 4px 15px var(--shadow);
        margin-bottom: 3rem;
        border: 1px solid var(--card-border);
        border-top: 4px solid var(--primary);
        animation: fadeIn 0.8s ease-in-out;
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        color: var(--text-main);
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: var(--text-sub);
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* GRID DE MÓDULOS */
    .modules-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        padding: 1rem 0;
    }

    .module-card {
        background-color: var(--card-bg);
        border-radius: 0.5rem;
        padding: 2rem;
        box-shadow: 0 4px 10px var(--shadow);
        border: 1px solid var(--card-border);
        border-top: 4px solid var(--card-border);
        transition: all 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }

    .module-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px var(--shadow);
        border-top-color: var(--primary); /* Hover revela el guinda fuerte */
    }

    .card-icon {
        font-size: 2.2rem;
        margin-bottom: 1rem;
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 0.8rem;
    }

    .card-desc {
        font-size: 0.95rem;
        color: var(--text-sub);
        line-height: 1.5;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .session-box {
        background-color: var(--page-bg);
        padding: 0.8rem 1.5rem;
        border-radius: 2rem;
        border: 1px solid var(--card-border);
        display: inline-block;
        margin-top: 1rem;
    }
    .session-text {
        color: var(--text-main);
        font-weight: 600;
    }

    .footer {
        text-align: center;
        margin-top: 4rem;
        padding: 2rem;
        color: var(--text-sub);
        font-size: 0.85rem;
        border-top: 1px solid var(--card-border);
    }

    /* STATUS BADGES */
    .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .status-item {
        background: var(--card-bg);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid var(--card-border);
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .status-ok { background-color: #10b981; }
    .status-error { background-color: #ef4444; }
    .status-warn { background-color: #f59e0b; }
    
    .status-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-main);
    }
    .status-val {
        font-size: 0.75rem;
        color: var(--text-sub);
    }
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
# Logos institucionales Placeholders
LOGO_PATH = "logo_ria_desktop.png"
img_base64 = get_img_as_base64(LOGO_PATH)
if img_base64:
    system_logo_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 100px; height: auto;">'
else:
    system_logo_html = '<div style="font-size: 3rem;">🐁</div>'

# Logos institucionales
IPN_LOGO_PATH = os.path.join("assets", "logos", "logo_ipn.webp")
ESCOM_LOGO_PATH = os.path.join("assets", "logos", "logo_escom.webp")

ipn_img_base64 = get_img_as_base64(IPN_LOGO_PATH)
if ipn_img_base64:
    # IPN logo significantly larger
    ipn_logo_html = f'<img src="data:image/webp;base64,{ipn_img_base64}" class="institucional-logo" style="width: 250px; height: auto;">'
else:
    ipn_logo_html = '<div style="width:250px; height:250px; border-radius:50%; background-color:var(--primary); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:24px; margin: 0 auto;">IPN</div>'

escom_img_base64 = get_img_as_base64(ESCOM_LOGO_PATH)
if escom_img_base64:
    # ESCOM logo smaller
    escom_logo_html = f'<img src="data:image/webp;base64,{escom_img_base64}" class="institucional-logo" style="width: 120px; height: auto;">'
else:
    escom_logo_html = '<div style="width:120px; height:120px; border-radius:50%; background-color:var(--primary); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:16px; margin: 0 auto;">ESCOM</div>'

# ================= 4. LAYOUT =================

# Estilos CSS específicos para la alineación de logos institucionales
st.markdown(
    f"""
    <style>
    .logos-container {{
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        width: 100%;
        margin-bottom: 2rem;
    }}
    .logo-left, .logo-right {{
        flex: 1;
        flex-basis: 33%;
        display: flex;
    }}
    .logo-left {{
        justify-content: flex-start;
    }}
    .logo-right {{
        justify-content: flex-end;
    }}
    .logo-center {{
        flex: 1;
        flex-basis: 33%;
        display: flex;
        justify-content: center;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# HERO
st.markdown(
    f"""
    <div class="hero-container">
        <div class="logos-container">
            {ipn_logo_html}
            {system_logo_html}
            {escom_logo_html}
        </div>
        <div class="hero-title" style="color: var(--primary);">INSTITUTO POLITÉCNICO NACIONAL</div>
        <div class="hero-subtitle" style="font-weight: 700; margin-bottom: 1rem; color: var(--primary); opacity: 0.9;">Escuela Superior de Cómputo</div>
        <div class="hero-subtitle" style="font-size: 1.05rem; max-width: 700px; color: var(--text-main);">
            Plataforma Institucional para Análisis Automatizado y Visualización de Comportamiento
            de Especímenes en Modelos de Ansiedad (TT 2026).
        </div>
        {'<div style="margin-top: 2rem;"><span class="session-box" style="border-left: 4px solid var(--primary);"><span class="session-text">✅ Autenticado como investigador: ' + st.session_state.user + '</span></span></div>' if st.session_state.get("logged_in") else ''}
    </div>
    """,
    unsafe_allow_html=True
)

# ================= 5. DIAGNÓSTICO DE SISTEMA =================
def _check_docker_status():
    """Solo VERIFICA el estado de Docker (sin intentar levantarlo).
    El levantamiento ocurre en start_services.py antes de que Streamlit inicie."""
    import subprocess
    CF = 0x08000000 if sys.platform == "win32" else 0

    # 1. Verificar Docker daemon
    try:
        subprocess.check_output(
            ["docker", "info"],
            stderr=subprocess.STDOUT,
            creationflags=CF,
            timeout=5
        )
    except Exception as e:
        return False, f"Docker daemon: {str(e)[:15]}"

    # 2. Verificar contenedor específico
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-a", "--filter", "name=tt_ratones_db", "--format", "{{.Status}}"],
            stderr=subprocess.STDOUT,
            creationflags=CF,
            timeout=5
        ).decode().strip()
        
        if not out:
            return False, "Contenedor no existe"
        
        if "Up" in out:
            return True, "PostgreSQL activo"
        elif "Exited" in out or "exited" in out:
            return False, "Contenedor detenido - ejecuta launcher.bat"
        else:
            return False, f"Estado: {out[:20]}"
    except Exception as e:
        return False, f"Error: {str(e)[:20]}"


def check_system_status_incremental():
    """Realiza el diagnóstico paso a paso para el Splash Screen."""
    status = {}
    
    # 0. Prep
    yield 10, "Inicializando entorno..."
    time.sleep(0.5)

    # 1. Docker
    yield 30, "Verificando contenedores Docker..."
    docker_ok, docker_msg = _check_docker_status()
    if docker_ok:
        status["docker"] = ("OK", "status-ok", docker_msg)
    else:
        status["docker"] = ("Error", "status-error", docker_msg)
    yield 55, "Docker verificado."

    # 2. Base de Datos
    yield 65, "Conectando a PostgreSQL..."
    status["db"] = ("Error", "status-error", "Error de inicio")
    try:
        from src.db.connection import get_db_engine
        from sqlalchemy import text
        engine = get_db_engine()
        if engine and not isinstance(engine, str):
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["db"] = ("OK", "status-ok", "PostgreSQL conectado")
        else:
            status["db"] = ("Error", "status-error", "Motor SQL no creado")
    except Exception as e:
        status["db"] = ("Error", "status-error", f"Error SQL: {str(e)[:20]}")
    yield 85, "Base de datos verificada."

    # 3. GPU
    yield 95, "Detectando hardware de IA..."
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            status["gpu"] = ("CUDA", "status-ok", name)
        else:
            status["gpu"] = ("CPU", "status-warn", "Sin aceleración GPU")
    except:
        status["gpu"] = ("N/A", "status-error", "Torch no cargado")
    
    yield 100, "¡Listo!"
    time.sleep(0.5)
    return status

# ================= 4. EJECUCIÓN DEL SPLASH SCREEN =================
if "loaded" not in st.session_state:
    st.session_state.sys_status = generic_splash_loader(check_system_status_incremental())
    st.session_state.loaded = True

# Usar el status guardado en sesión
sys_status = st.session_state.get("sys_status", {})

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
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="background-color: var(--card-bg); display: inline-block; padding: 12px 24px; border-radius: 0.5rem; border: 1px solid var(--accent); border-left: 4px solid var(--primary); box-shadow: 0 4px 6px var(--shadow);">
                <span style="color: var(--text-main); font-weight: 500;">🛑 <strong>Acceso Restringido:</strong> Por favor inicie sesión con credenciales institucionales habilitadas en el módulo de Control de Acceso.</span>
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

# ================= 6. INSTITUTIONAL FOOTER =================
st.markdown("---")

footer_col1, footer_col2 = st.columns([1.5, 1])

with footer_col1:
    st.markdown('<h3 style="color:var(--primary); border-bottom: 2px solid var(--primary); padding-bottom:0.5rem; margin-bottom:1rem;">Ubicación y Contacto</h3>', unsafe_allow_html=True)
    st.markdown("""
        **Instituto Politécnico Nacional - Escuela Superior de Cómputo (ESCOM)**<br>
        Av. Juan de Dios Bátiz, Esq. Miguel Othón de Mendizábal,<br>
        Unidad Profesional Adolfo López Mateos, Zacatenco,<br>
        Alcaldía Gustavo A. Madero, C.P. 07738, Ciudad de México.
    """, unsafe_allow_html=True)
    
    # iframe map
    st.markdown("""
        <iframe 
            src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3760.6713833777085!2d-99.14327272494429!3d19.51268313813952!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x85d1f0ebcdbecd15%3A0xa6cd2d03a11545db!2sEscuela%20Superior%20de%20C%C3%B3mputo%20(ESCOM)%20-%20IPN!5e0!3m2!1ses!2smx!4v1700000000000" 
            width="100%" 
            height="200" 
            style="border:0; border-radius:8px; margin-top:10px;" 
            allowfullscreen="" 
            loading="lazy" 
            referrerpolicy="no-referrer-when-downgrade">
        </iframe>
    """, unsafe_allow_html=True)

with footer_col2:
    st.markdown('<h3 style="color:var(--primary); border-bottom: 2px solid var(--primary); padding-bottom:0.5rem; margin-bottom:1rem;">Redes Sociales</h3>', unsafe_allow_html=True)
    st.markdown("""
        Fortalece la vinculación con nuestra comunidad. Síguenos y sé parte de la comunidad Politécnica.
    """)
    st.markdown("""
        <div style="display:flex; gap:15px; margin-top:15px; flex-wrap: wrap;">
            <a href="https://www.facebook.com/ipn.mx" target="_blank" style="text-decoration:none;">
                <div style="background-color:#3b5998; color:white; width:45px; height:45px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:24px;"><b>f</b></div>
            </a>
            <a href="https://twitter.com/IPN_MX" target="_blank" style="text-decoration:none;">
                <div style="background-color:#000000; color:white; width:45px; height:45px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:24px;"><b>𝕏</b></div>
            </a>
            <a href="https://www.instagram.com/ipn_oficial/" target="_blank" style="text-decoration:none;">
                <div style="background: linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%); color:white; width:45px; height:45px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:24px;"><b>ig</b></div>
            </a>
            <a href="https://www.youtube.com/user/IPNoficial" target="_blank" style="text-decoration:none;">
                <div style="background-color:#ff0000; color:white; width:45px; height:45px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:24px;"><b>▶</b></div>
            </a>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.85rem; color:var(--text); opacity:0.7;"><i>La identidad web institucional del Politécnico la construimos y la cuidamos todos.</i></p>', unsafe_allow_html=True)

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
