import streamlit as st
import cv2
import numpy as np
import tempfile
import pandas as pd
import time
import os
import sys
import threading
# moviepy NO se importa aquí: este módulo delega el procesamiento de video
# a subprocesos externos (venv_310), por lo que el import sería overhead puro.

# ================= 0. PERSISTENCIA =================
# REGLA #1: set_page_config SIEMPRE primero, antes de cualquier st.*
st.set_page_config(page_title="Análisis IA (EPM)", page_icon="🧠", layout="wide")

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from src.session_utils import load_session, save_session
from src.access_control import require_researcher
from src.sidebar_control import apply_sidebar_visibility

# Cargar sesión antes de validar login
load_session()

# Aplicar control de sidebar
apply_sidebar_visibility()

# =============== VERIFICAR ACCESO ==================
require_researcher()  # Solo investigadores y estudiantes

# ================== GUARDIA DE ENTORNO (RTX 5060 FIX) ==================
# Detectamos la GPU sin importar torch (para evitar inicializar CUDA antes de tiempo)
import subprocess

def detect_blackwell_manual():
    try:
        res = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], encoding="utf-8")
        if "RTX 50" in res or "Blackwell" in res:
            return True
    except:
        pass
    return False

is_blackwell = detect_blackwell_manual()

# APLICAR ESCUDO ANTI-CUDA: Si el usuario eligió CPU, bloqueamos TODO acceso a la GPU
if st.session_state.get("dlc_device_opt") == "CPU (Forzar)":
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
    try:
        import torch
        # Monkey-patch para que el código de DeepLabCut crea que no hay GPUs
        torch.cuda.is_available = lambda: False
        torch.cuda.device_count = lambda: 0
        torch.cuda.current_device = lambda: -1
        torch.cuda.get_device_properties = lambda x: None
        torch.cuda.memory_reserved = lambda: 0
    except ImportError:
        pass
else:
    if "CUDA_VISIBLE_DEVICES" in os.environ:
        del os.environ["CUDA_VISIBLE_DEVICES"]
# Los imports pesados (deeplabcut, ultralytics) se cargan DESPUÉS de la guardia
# para asegurar que respetan CUDA_VISIBLE_DEVICES
import traceback
import threading

deeplabcut = None
dlc_import_error = None

# Función para cargar motores bajo demanda
def cargar_motores():
    global deeplabcut, dlc_import_error
    
    # Cargar DeepLabCut
    if deeplabcut is None:
        try:
            # --- HOTFIX: Patch tf_keras to include legacy_tf_layers ---
            import os
            os.environ["TF_USE_LEGACY_KERAS"] = "1"
            import tensorflow as tf
            import tf_keras
            if not hasattr(tf_keras, "legacy_tf_layers"):
                try:
                    tf_keras.legacy_tf_layers = tf.compat.v1.layers
                    print("[HOTFIX] Patched tf_keras.legacy_tf_layers = tf.compat.v1.layers")
                except Exception as e:
                    print(f"[HOTFIX WARNING] Could not patch legacy_tf_layers: {e}")
            # -------------------------------------------------------------

            import deeplabcut as dlc_lib
            deeplabcut = dlc_lib
            
            # --- HOTFIX: Reload modules to apply patches (Windows Path Limit) ---
            import importlib
            try:
                # 1. Reload the patched inference module
                import deeplabcut.modelzoo.api.superanimal_inference
                importlib.reload(deeplabcut.modelzoo.api.superanimal_inference)
                
                # 2. Reload the adapter which uses the inference module
                import deeplabcut.modelzoo.api.spatiotemporal_adapt
                importlib.reload(deeplabcut.modelzoo.api.spatiotemporal_adapt)

                # 3. Reload the predict logic which uses the adapter
                import deeplabcut.pose_estimation_tensorflow.predict_supermodel
                importlib.reload(deeplabcut.pose_estimation_tensorflow.predict_supermodel)
                
                print("[HOTFIX] DeepLabCut modules reloaded successfully.")
            except Exception as e:
                print(f"[HOTFIX WARNING] Could not reload DLC modules: {e}")
            # -------------------------------------------------------------------
            
        except Exception as e:
            dlc_import_error = f"{type(e).__name__}: {str(e)}"
            
    # YOLO se carga globalmente pero solo se usa después

# ================== 1. VERIFICAR LOGIN Y ENTORNO ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
    st.stop()

# Verificar que estemos usando el entorno correcto (3.11 para DLC)
if not sys.version.startswith("3.11"):
    st.error(f"⚠️ **ENTORNO INCORRECTO**: Estás usando Python {sys.version.split()[0]}.")
    st.info("Para usar DeepLabCut, debes cerrar esta pestaña y ejecutar la aplicación desde el entorno `dlc_env_311`.")
    st.code(f"Usa el comando: ..\\DeepLabCut\\DeepLabCut\\dlc_env_311\\Scripts\\python.exe -m streamlit run Home.py")
    if not st.checkbox("Continuar de todos modos (DLC no funcionará)"):
        st.stop()

# ================== 2. CARGAR MOTORES (LAZY) ==================
cargar_motores()

from ultralytics import YOLO # Importar aquí para que respete la env var anterior

st.session_state.init_done = True

from src.auth import check_admin_access

# GUARDIA: ADMINS NO PUEDEN USAR EL MÓDULO EXPERIMENTAL
role = st.session_state.get("role")
if check_admin_access(role):
    st.warning("⛔ El rol de Administrador está limitado a gestión de usuarios.")
    st.info("Para cuidar la integridad de los datos, los administradores no pueden crear ni modificar experimentos.")
    st.stop()

# ================== 2. TEMA CLARO / OSCURO ==================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Oscuro"

theme_mode = st.sidebar.radio(
    "Tema de la interfaz",
    ["Claro", "Oscuro"],
    index=0 if st.session_state.theme_mode == "Claro" else 1,
)
st.session_state.theme_mode = theme_mode

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

# ================== 3. CSS GLOBAL ==================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

/* Labels genéricos */
label {{
    color: {colors["text_main"]} !important;
}}

/* Toggle, sliders, etc. -> usan este contenedor */
[data-testid="stWidgetLabel"] * {{
    color: {colors["text_main"]} !important;
}}

/* Métricas (Zona actual) */
[data-testid="stMetric"] * {{
    color: {colors["text_main"]} !important;
}}

.tt-ia-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: {colors["text_main"]};
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }}

    .tt-ia-subtitle {{
        font-size: 0.95rem;
        color: {colors["text_main"]};
        opacity: 0.9;
        margin-bottom: 1.2rem;
    }}

    .tt-card {{
        background-color: {colors["card_bg"]};
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 14px 30px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.18);
        margin-bottom: 1.2rem;
        color: {colors["text_main"]};
    }}
    .tt-card p, .tt-card span, .tt-card div {{
        color: {colors["text_main"]} !important;
    }}

    .tt-section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {colors["text_main"]};
        margin-bottom: 0.5rem;
    }}

    /* Botones */
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

    /* Alertas (info, warning, etc.) */
    .stAlert {{
        color: {colors["text_main"]} !important;
        border-radius: 14px;
    }}

    /* Labels de inputs (slider, text_input, toggle, etc.) */
    label {{
        color: {colors["text_main"]} !important;
    }}

    /* MÉTRICAS: Zona actual en el mismo color del tema */
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricDelta"] {{
        color: {colors["text_main"]} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ================== 4. ENCABEZADO ==================
header_placeholder = st.empty()
st.markdown(
    '<div class="tt-ia-subtitle">'
    'Ejecuta el modelo de visión por computadora para detectar al espécimen, '
    'asignar su posición a las zonas (ROIs) y obtener métricas de comportamiento.'
    '</div>',
    unsafe_allow_html=True,
)

# ================== 5. VERIFICACIONES DE SEGURIDAD Y CARGA RÁPIDA ==================
import glob
import math

with st.expander("⏩ Carga Rápida de Experimentación (Atajo)", expanded=False):
    st.markdown("Si ya procesaste videos y quieres testear directamente SimBA y YOLO Tracking sin pasar por las pestañas previas, usa estos atajos:")
    col_var1, col_var2 = st.columns(2)
    with col_var1:
        import glob
        # Escanear qué CSVs existen en la carpeta de SimBA para solo mostrar los que ya tienen features extraídas
        features_dir = os.path.join("data", "simba_projects", "New folder", "thigmotaxis_optimizado", "project_folder", "csv", "features_extracted")
        csv_files = glob.glob(os.path.join(features_dir, "*.csv"))
        
        videos_validos = []
        # Buscar en dataset_tt los videos cuyo nombre coincida con los csvs que sí existen
        for csv_path in csv_files:
            csv_basename = os.path.splitext(os.path.basename(csv_path))[0]
            # Puede ser MP4 o MOV, buscamos emparejar
            video_matches = glob.glob(os.path.join("dataset_tt", f"{csv_basename}.*"))
            for v in video_matches:
                if v.lower().endswith(('.mp4', '.mov')):
                    videos_validos.append(v)
        
        videos_disponibles = sorted(list(set(videos_validos)))
        video_rapido = st.selectbox("1. Seleccionar Video Procesado", ["(Usar video del flujo actual)"] + videos_disponibles)
    with col_var2:
        from src.zone_templates import list_templates, load_template
        templates = list_templates()
        template_rapido = st.selectbox("2. Seleccionar Template de Zonas", ["(Usar zonas actuales)"] + templates)

if video_rapido != "(Usar video del flujo actual)":
    st.session_state["ruta_video_actual"] = video_rapido
    st.session_state["inicio_recorte"] = 0
    st.session_state["fin_recorte"] = math.inf # Analizar completo

with col_var2:
    if st.button("✏️ Abrir Ventana de Dibujo Manual (OpenCV)", use_container_width=True):
        if "ruta_video_actual" in st.session_state and st.session_state["ruta_video_actual"]:
            st.info("Revisa la barra de tareas. Se abrirá una ventana llamada 'Ajuste Fino de ROI' para que dibujes zona por zona y la ajustes.")
            import sys
            import os
            if os.getcwd() not in sys.path:
                sys.path.append(os.getcwd())
            from src.scripts.generar_video_prediccion import select_maze_rois
            
            # Esto bloqueará Streamlit hasta que el usuario termine en la ventana local de OpenCV
            roi_result = select_maze_rois(st.session_state.get("ruta_video_actual"))
            
            if roi_result:
                maze_rois, config_cats = roi_result
                zonas_cargadas = []
                for name, coords in maze_rois.items():
                    # OpenCV coords are (x,y,w,h)
                    zonas_cargadas.append({
                        "id": name,
                        "x": coords[0],
                        "y": coords[1],
                        "w": coords[2],
                        "h": coords[3]
                    })
                st.session_state["zonas_configuradas"] = zonas_cargadas
                st.session_state["mostrar_exito_zonas"] = True
                st.rerun()
            else:
                st.warning("Cancelaste el proceso. No se actualizaron las zonas.")
        else:
            st.error("Selecciona un video primero.")

if st.session_state.pop("mostrar_exito_zonas", False):
    st.success("✅ ¡Las 5 Zonas fueron dibujadas interactivamente y se guardaron en memoria con éxito!")

# Indicador visual de que las zonas existen
if "zonas_configuradas" in st.session_state and st.session_state["zonas_configuradas"]:
    nombres_zonas = [z.get('id', z.get('Nombre Zona', 'Zona')) for z in st.session_state["zonas_configuradas"]]
    st.caption(f"📍 Zonas actualmente cargadas en memoria: {', '.join(nombres_zonas)}")

if template_rapido != "(Usar zonas actuales)":
    temp_data = load_template(template_rapido)
    if temp_data:
        canvas_json = temp_data["canvas"]
        names = temp_data.get("names", [])
        zonas_cargadas = []
        if isinstance(canvas_json, dict) and "objects" in canvas_json:
            for i, obj in enumerate(canvas_json["objects"]):
                nombre = names[i] if i < len(names) else f"Zona {i}"
                tipo   = obj.get("type", "rect")

                if tipo == "rect":
                    # ── Formato CANÓNICO (mismo que _02_Configuracion_Zonas.py) ──
                    # scaleX/scaleY pueden no existir en objetos dibujados a mano libre
                    scale_x = obj.get("scaleX", 1) or 1
                    scale_y = obj.get("scaleY", 1) or 1
                    zonas_cargadas.append({
                        "type":       "rect",
                        "Nombre Zona": nombre,
                        "left":   obj.get("left", 0),
                        "top":    obj.get("top",  0),
                        "width":  obj.get("width",  0) * scale_x,
                        "height": obj.get("height", 0) * scale_y,
                    })
                elif tipo == "line":
                    # Muros: reconstruir coordenadas absolutas igual que en _02_
                    lx = obj.get("left", 0)
                    ly = obj.get("top",  0)
                    zonas_cargadas.append({
                        "type":       "line",
                        "Nombre Zona": nombre,
                        "x1": lx + obj.get("x1", 0),
                        "y1": ly + obj.get("y1", 0),
                        "x2": lx + obj.get("x2", 0),
                        "y2": ly + obj.get("y2", 0),
                    })

        st.session_state["zonas_configuradas"] = zonas_cargadas

if "ruta_video_actual" not in st.session_state or not st.session_state["ruta_video_actual"]:
    st.error("⚠️ No hay video seleccionado. Usa la *Carga Rápida* de arriba o ve a **01 · Ingesta de Video**.")
    st.stop()

if "zonas_configuradas" not in st.session_state or not st.session_state["zonas_configuradas"]:
    st.error("⚠️ No hay zonas configuradas. Carga un *Template* arriba o ve a **02 · Configuración de Zonas**.")
    st.stop()

ruta_video = st.session_state["ruta_video_actual"]
zonas = st.session_state["zonas_configuradas"]
inicio = st.session_state.get("inicio_recorte", 0)
fin = st.session_state.get("fin_recorte", math.inf)  # Default ∞ si no hay fin

# ================== 6. LAYOUT PRINCIPAL ==================
col_cfg, col_video = st.columns([1, 2])

# ---- Configuración y, debajo, métrica en vivo
with col_cfg:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">⚙️ Configuración del análisis</div>',
        unsafe_allow_html=True,
    )
    
    motor = st.selectbox(
        "Arquitectura de Análisis",
        [
            "DeepLabCut + YOLO Tracker + SimBA",
            "YOLOv11-Pose + YOLO Tracker + SimBA (Próximamente)",
            "YOLOv8 Tracker Clásico (Tiempo Real)"
        ],
        index=0
    )
    
    # Actualizar encabezado
    header_title = "🧠 Análisis Multimodal" if "SimBA" in motor else "🧠 Análisis Clásico"
    header_placeholder.markdown(
        f'<div class="tt-ia-title">{header_title}</div>',
        unsafe_allow_html=True,
    )
    
    iniciar_completo = False
    iniciar_acelerado = False
    iniciar = False
    has_features = False
    features_csv_path = ""
    
    if motor == "YOLOv8 Tracker Clásico (Tiempo Real)":
        st.info("💡 Rastreo de centro de masa en tiempo real. No clasifica comportamientos complejos.")
        usar_modelo_real = st.toggle("Usar modelo YOLO real (.pt)", value=False)
        modelo_path = st.text_input("Ruta del modelo (.pt):", "yolov8n.pt")
        confianza = st.slider("Umbral de confianza", 0.0, 1.0, 0.5)
        iniciar = st.button("▶️ INICIAR ANÁLISIS")
        
    elif motor == "YOLOv11-Pose + YOLO Tracker + SimBA (Próximamente)":
        st.info("🔜 Este modelo de inferencia ultrarrápida está en fase de entrenamiento. Pronto reducirá el tiempo total a 5 minutos por video.")
        st.stop()
        
    else: # DLC + YOLO Tracker + SimBA
        import glob
        st.info("🧬 Pipeline científico validado: Extrae keypoints, analiza comportamiento y renderiza HUD Multimodal.")
        
        # Buscar features previamente procesadas
        features_dir = os.path.join("data", "simba_projects", "New folder", "thigmotaxis_optimizado", "project_folder", "csv", "features_extracted")
        base_name = os.path.splitext(os.path.basename(ruta_video))[0]
        
        if os.path.exists(features_dir):
            posibles = glob.glob(os.path.join(features_dir, f"{base_name}*.csv"))
            if posibles:
                has_features = True
                features_csv_path = max(posibles, key=os.path.getctime)
        
        st.markdown("---")
        if has_features:
            st.success("✅ **¡Datos Previos Encontrados!**")
            st.write(f"Se detectó extracción de keypoints de DeepLabCut y atributos de SimBA para `{base_name}`.")
            
            iniciar_acelerado = st.button("⚡ RE-ANÁLISIS ACELERADO (~5 min)", type="primary", use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.expander("Opciones Avanzadas"):
                st.write("¿Deseas reconstruir todo desde cero? (Tardará ~4 horas con DLC)")
                iniciar_completo = st.button("🐌 EJECUTAR DESDE CERO (DLC + SIMBA)", use_container_width=True)
        else:
            st.warning("⏳ **No hay datos previos.**")
            st.write(f"Se requiere extraer características con DeepLabCut para `{base_name}`. Esto tomará varias horas.")
            iniciar_acelerado = False
            iniciar_completo = st.button("▶️ EXTRAER Y ANALIZAR DESDE CERO", type="primary", use_container_width=True)
            
        supermodel = "superanimal_topviewmouse"
        video_adapt = True
        confianza = 0.1
        
        if st.session_state.get("dlc_device_opt") == "CPU (Forzar)":
            st.caption("🛡️ MODO SEGURO ACTIVO (CPU)")

    st.markdown("</div>", unsafe_allow_html=True)

    # Placeholder para la métrica de zona actual
    metric_placeholder = st.empty()

# ---- Columna derecha: video
with col_video:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">🎞️ Vista Previa de Zonas / Detecciones</div>',
        unsafe_allow_html=True,
    )
    image_placeholder = st.empty()
    
    # Mostrar preview visual si ya hay zonas cargadas y de momento no ha iniciado un análisis
    if "zonas_configuradas" in st.session_state and st.session_state["zonas_configuradas"] and "ruta_video_actual" in st.session_state:
        import cv2
        try:
            cap = cv2.VideoCapture(st.session_state["ruta_video_actual"])
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                overlay = frame_rgb.copy()
                
                # Pintar overlays de relleno (las lineas no tienen relleno)
                for z in st.session_state["zonas_configuradas"]:
                    if z.get("type") == "line" or "muro" in z.get("id", z.get('Nombre Zona', '')).lower(): continue
                    
                    color = (200, 200, 200)
                    name = z.get('id', z.get('Nombre Zona', 'Zona'))
                    n_l = name.lower()
                    if 'abierto' in n_l: color = (240, 120, 120) # Coral
                    elif 'cerrado' in n_l: color = (0, 250, 255) # Cyan
                    elif 'centro' in n_l: color = (255, 165, 0) # Naranja
                        
                    x = int(z.get('x', z.get('left', 0)))
                    y = int(z.get('y', z.get('top', 0)))
                    w = int(z.get('w', z.get('width', 0)))
                    h = int(z.get('h', z.get('height', 0)))
                    cv2.rectangle(overlay, (x, y), (x+w, y+h), color, -1)
                    
                # Combinar transparencia
                alpha = 0.35
                cv2.addWeighted(overlay, alpha, frame_rgb, 1 - alpha, 0, frame_rgb)
                
                # Pintar bordes gruesos, lineas y nombre
                for z in st.session_state["zonas_configuradas"]:
                    color = (200, 200, 200)
                    name = z.get('id', z.get('Nombre Zona', 'Zona'))
                    n_l = name.lower()
                    if 'abierto' in n_l: color = (240, 120, 120) # Coral
                    elif 'cerrado' in n_l: color = (0, 250, 255) # Cyan
                    elif 'centro' in n_l: color = (255, 165, 0) # Naranja
                        
                    if z.get("type") == "line" or "muro" in n_l:
                        x1 = int(z.get('x1', 0))
                        y1 = int(z.get('y1', 0))
                        x2 = int(z.get('x2', 0))
                        y2 = int(z.get('y2', 0))
                        cv2.line(frame_rgb, (x1, y1), (x2, y2), (0, 255, 255), 3) # Amarillo Cyan fuerte para Muros
                        cv2.putText(frame_rgb, name, (x1, max(0, y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    else:
                        x = int(z.get('x', z.get('left', 0)))
                        y = int(z.get('y', z.get('top', 0)))
                        w = int(z.get('w', z.get('width', 0)))
                        h = int(z.get('h', z.get('height', 0)))
                        cv2.rectangle(frame_rgb, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(frame_rgb, name, (x, max(0, y-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                image_placeholder.image(frame_rgb, use_container_width=True, caption=f"Vista previa: {len(st.session_state['zonas_configuradas'])} Zonas Cargadas")
        except Exception as e:
            pass # Ignorar fallos de la vista previa statica

    st.markdown("</div>", unsafe_allow_html=True)

# ================== 7. FUNCIÓN GEOMÉTRICA ==================
# ================== 7. FUNCIÓN GEOMÉTRICA Y HEURÍSTICAS ==================
from src.analysis_logic import checar_zona, calcular_distancia, detectar_grooming, detectar_thigmotaxis

# ================== 8. BUCLE DE PROCESAMIENTO ==================
if iniciar_completo:
    st.toast("Iniciando Pipeline Completo...")
    status_container = st.status("Ejecutando Full Pipeline (esto tomará varios minutos)...", expanded=True)
    log_area = st.empty()
    
    try:
        # Ruta al script
        script_path = os.path.abspath(os.path.join("src", "scripts", "full_pipeline.py"))
        venv_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))

        if not os.path.exists(venv_python):
             st.error("No se encontró el entorno venv_310")
             st.stop()
        
        # Obtener la ruta del video de la sesión
        video_path = st.session_state.get("ruta_video_actual", "")
        if not video_path or not os.path.exists(video_path):
            st.error("❌ No hay video cargado o el archivo no existe")
            st.stop()
             
        cmd = [venv_python, script_path, "--video", video_path]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        logs = []
        for line in iter(process.stdout.readline, ''):
            clean_line = line.strip()
            logs.append(clean_line)
            # Mantener solo las últimas 20 líneas para no saturar UI
            log_text = "\n".join(logs[-20:]) 
            log_area.code(log_text, language="bash")
            print(f"[Pipeline] {clean_line}")
            
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            status_container.update(label="✅ Pipeline completado con éxito!", state="complete")
            st.success("¡Análisis completo terminado!")
            
            # Buscar video resultante
            # El script full_pipeline guarda en videos/R5B20_01mar24_full_behavior_h264.mp4
            # Pero el nombre depende de la variable en el script.
            # Buscamos el h264 más reciente en la carpeta de videos del proyecto SimBA
            project_videos_dir = os.path.join("data", "simba_projects", "SimBA_EPM_Analysis", "project_folder", "videos")
            if os.path.exists(project_videos_dir):
                files = glob.glob(os.path.join(project_videos_dir, "*_behavior_h264.mp4"))
                if files:
                    latest_video = max(files, key=os.path.getctime)
                    st.info(f"Video generado: {os.path.basename(latest_video)}")
                    st.video(latest_video)
                else:
                    st.warning("No se encontró el video final generado.")
        else:
            status_container.update(label="❌ Error en el pipeline", state="error")
            st.error("El pipeline falló. Revisa los logs arriba.")
            
    except Exception as e:
        status_container.update(label="❌ Error de ejecución", state="error")
        st.error(f"Error lanzando subprocess: {e}")

if iniciar_acelerado:
    st.toast("Iniciando Re-Análisis Acelerado...")
    status_container = st.status("Reconstruyendo video multimodo (esto tomará ~5 minutos)...", expanded=True)
    
    with status_container:
        st.markdown('<div class="tt-section-title">⏱️ Progreso Inteligente</div>', unsafe_allow_html=True)
        smart_status = st.info("Inicializando Motor Python...")
        progress_bar = st.progress(0, text="Calculando...")
        estado_actual = "Inicializando scripts..."
        
        with st.expander("Terminal Interna (Logs Ténicos)", expanded=True):
            log_area = st.empty()
            
    try:
        import json
        script_path = os.path.abspath(os.path.join("src", "scripts", "generar_video_prediccion.py"))
        venv_python = sys.executable 
        base_name = os.path.splitext(os.path.basename(ruta_video))[0]
        
        # Obtener zonas configuradas JSON
        zonas = st.session_state.get("zonas_configuradas", [])
        zonas_json_str = json.dumps(zonas)
        
        # Rutas a modelos validados
        model_thigmo = os.path.join("data", "simba_projects", "New folder", "thigmotaxis_optimizado", "models", "validations", "Thigmotaxis_0.sav")
        model_grooming = os.path.join("data", "simba_projects", "New folder", "thigmotaxis_optimizado", "models", "validations", "Grooming_2.sav")
        output_name = f"{base_name}_STREAMLIT_MULTIMODAL.mp4"
        output_path = os.path.abspath(os.path.join("videos", output_name)) # Guardar en folder genérico videos de la Tesis
        
        if not os.path.exists("videos"):
            os.makedirs("videos")
            
        cmd = [
            venv_python, script_path,
            "--video", ruta_video,
            "--features", features_csv_path,
            "--model_thigmo", model_thigmo,
            "--model_grooming", model_grooming,
            "--output", output_path,
            "--zonas_json", zonas_json_str
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        logs = []
        for line in iter(process.stdout.readline, ''):
            clean_line = line.strip()
            logs.append(clean_line)
            log_text = "\n".join(logs[-10:])  # Mostrar solo las últimas 10 líneas crudas
            log_area.code(log_text, language="bash")
            print(f"[Acelerado] {clean_line}")
            
            # --- INTÉRPRETE INTELIGENTE DE LOGS PARA EL USUARIO ---
            if "Parallel" in clean_line or "Using backend" in clean_line:
                if estado_actual != "📊 Ejecutando Inferencia de Comportamientos (Modelos SimBA)...":
                    estado_actual = "📊 Ejecutando Inferencia de Comportamientos (Modelos SimBA)..."
                    smart_status.info(estado_actual)
            elif "YOLO" in clean_line or "Fusing" in clean_line or "model" in clean_line.lower():
                if estado_actual != "👁️ Inicializando Motores de Visión e IA...":
                    estado_actual = "👁️ Inicializando Motores de Visión e IA..."
                    smart_status.info(estado_actual)
                    progress_bar.progress(0.10, text="Cargando Modelos Pesados en Memoria...")
            elif "Renderizados" in clean_line:
                if estado_actual != "🎞️ Renderizando Video Multimodal...":
                    estado_actual = "🎞️ Renderizando Video Multimodal..."
                    smart_status.info(estado_actual)
                
                # Extraer progreso matemático
                import re
                match = re.search(r'Renderizados (\d+)/(\d+)', clean_line)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    if total > 0:
                        pct = min(1.0, current / total)
                        progress_bar.progress(pct, text=f"Dibujando HUD y exportando: {current} de {total} fotogramas ({int(pct*100)}%)")
            
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            status_container.update(label="✅ Video Multimodal Generado con éxito!", state="complete")
            st.success("¡Análisis Terminado Rápidamente!")
            
            # Cargar la tabla de trayectoria a la sesión para la Pestaña 04
            traj_path = output_path.replace(".mp4", "_trajectory.csv")
            if os.path.exists(traj_path):
                import pandas as pd
                df_trayectoria = pd.read_csv(traj_path)
                st.session_state["resultados_analisis"] = df_trayectoria
                st.info("📊 DataFrame de resultados enviado exitosamente a la pestaña de Estadísticas.")
                
                # --- GUARDAR HISTORIAL EN LA BASE DE DATOS ---
                try:
                    from src.db.connection import get_db_engine
                    from sqlalchemy import text
                    engine = get_db_engine()
                    if engine:
                        with engine.connect() as conn:
                            # 1. Crear Experimento en DB
                            q_exp = text("""
                                INSERT INTO experiments (rat_id, treatment, experiment_date, responsible, video_path)
                                VALUES (:rat_id, :treatment, CURRENT_DATE, :resp, :vpath)
                                RETURNING id
                            """)
                            ex_res = conn.execute(q_exp, {
                                "rat_id": base_name, 
                                "treatment": "Carga Rápida (Re-análisis IA)", 
                                "resp": st.session_state.get("user_name", "Investigador"),
                                "vpath": output_path
                            }).fetchone()
                            
                            if ex_res:
                                new_exp_id = ex_res[0]
                                # ⚡ COMMIT INMEDIATO: Salvamos el experimento ANTES de cualquier
                                # operación que pueda hacer rollback (como ALTER TABLE).
                                # Esto garantiza que el FK experiment_id exista en la DB.
                                conn.commit()
                                
                                # 2. Extraer resúmenes estadísticos rápidos
                                res_z = df_trayectoria.groupby("Zona")["Tiempo (s)"].count() * 0.1
                                open_t = float(res_z.filter(like="Abierto").sum())
                                closed_t = float(res_z.filter(like="Cerrado").sum())
                                center_t = float(res_z.filter(like="Centro").sum())
                                groom_t = float(df_trayectoria["Grooming"].sum() * 0.1 if "Grooming" in df_trayectoria.columns else 0)
                                thigmo_t = float(df_trayectoria["Thigmotaxis"].sum() * 0.1 if "Thigmotaxis" in df_trayectoria.columns else 0)

                                # 3. Actualizar esquema si falta trajectory_path (columna ya existe = ignorar)
                                try:
                                    conn.execute(text("ALTER TABLE analysis_results ADD COLUMN trajectory_path TEXT;"))
                                    conn.commit()
                                except Exception: 
                                    conn.rollback()  # Solo limpia el error del ALTER, el experimento ya fue guardado
                                    
                                # 4. Insertar métricas en DB
                                q_an = text("""
                                    INSERT INTO analysis_results 
                                    (experiment_id, time_open_arms, time_closed_arms, time_center, grooming_duration, thigmotaxis_duration, status, trajectory_path)
                                    VALUES (:eid, :topen, :tclosed, :tcen, :tgroom, :tthigmo, 'completed', :tpath)
                                """)
                                conn.execute(q_an, {
                                    "eid": new_exp_id, "topen": open_t, "tclosed": closed_t,
                                    "tcen": center_t, "tgroom": groom_t, "tthigmo": thigmo_t,
                                    "tpath": traj_path
                                })
                                conn.commit()
                                st.toast(f"✅ Historial guardado correctamente (ID: {new_exp_id})")
                except Exception as db_err:
                    st.warning(f"No se pudo guardar e historial en BD: {db_err}")
                # ---------------------------------------------
            else:
                st.warning("Video creado, pero no se encontró la tabla de trayectoria para las estadísticas.")

            # Cargar en UI
            st.video(output_path)
            
            with open(output_path, "rb") as file:
                btn = st.download_button(
                    label="⬇️ Descargar Video Predictivo",
                    data=file,
                    file_name=output_name,
                    mime="video/mp4",
                    type="primary"
                )
        else:
            status_container.update(label="❌ Error en el re-análisis", state="error")
            st.error("El proceso acelerado falló. Valida las zonas o el .h5")
    except Exception as e:
        status_container.update(label="❌ Error Crítico", state="error")
        st.error(f"Excepción: {e}")

if iniciar:
    if motor == "DeepLabCut SuperAnimal":
        # --- MODO DEEPLABCUT ---
        st.toast("Iniciando análisis con DeepLabCut SuperAnimal...")
        
        # Contenedores para el progreso
        status_container = st.status("Preparando motor DeepLabCut...", expanded=True)
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        # Variable para capturar el resultado/error del hilo
        analysis_state = {"done": False, "error": None}
        
        # Capturar parámetros ANTES de lanzar el hilo (st.session_state no es accesible dentro del thread)
        t_start_val = st.session_state.get("inicio_recorte", 0)
        t_end_val = st.session_state.get("fin_recorte")
        force_cpu_val = st.session_state.get("dlc_device_opt") == "CPU (Forzar)"
        ruta_video_val = ruta_video
        supermodel_val = supermodel
        video_adapt_val = video_adapt
        dest_folder_val = os.path.dirname(ruta_video)

        def run_dlc_analysis(t_start, t_end, force_cpu, video_path, model_name, adapt, dest):
            try:
                # 1. Definir rutas
                video_para_analizar = video_path
                
                # 2. ESCUDO DE HILO: Forzamos CPU si el usuario lo pidió
                if force_cpu:
                    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
                    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
                    try:
                        import torch
                        torch.cuda.is_available = lambda: False
                        torch.cuda.device_count = lambda: 0
                        torch.cuda.current_device = lambda: -1
                        torch.cuda.get_device_properties = lambda x: None
                    except:
                        pass
                
                # 3. RECORTE FÍSICO (Si hay rango seleccionado)
                # Siempre recortamos si t_end está definido (significa que el usuario pasó por Ingesta)
                print(f"[DLC] Valores de recorte recibidos: t_start={t_start}, t_end={t_end}")
                
                # Cargar el clip para obtener la duración real
                original_clip = VideoFileClip(video_path)
                duracion_total = original_clip.duration
                
                # Solo recortamos si el rango es diferente al video completo
                necesita_recorte = (t_start > 0) or (t_end is not None and t_end < duracion_total - 1)
                
                if necesita_recorte:
                    print(f"[DLC] Aplicando recorte: {t_start}s a {t_end}s (de {duracion_total}s total)")
                    if t_end is None:
                        t_end = duracion_total
                    
                    # Generar nombre temporal para el recorte
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    trimmed_name = f"{base_name}_trimmed_{int(t_start)}_{int(t_end)}.mp4"
                    video_para_analizar = os.path.join(dest, trimmed_name)
                    
                    if not os.path.exists(video_para_analizar):
                        subclip = original_clip.subclip(t_start, t_end)
                        # Usamos codec libx264 rápido para no perder mucha calidad ni tiempo
                        subclip.write_videofile(video_para_analizar, codec="libx264", audio=False)
                    else:
                        print(f"[DLC] Usando recorte existente: {video_para_analizar}")
                else:
                    print(f"[DLC] Sin recorte necesario, analizando video completo")
                
                original_clip.close()
                
                # 4. EJECUTAR ANÁLISIS EN SUBPROCESO (GPU ENV)
                print("[DLC] Preparando ejecución en entorno GPU (venv_310)...")
                
                # Definir rutas del entorno GPU
                venv_python = os.path.abspath(os.path.join("venv_310", "Scripts", "python.exe"))
                script_path = os.path.abspath(os.path.join("src", "scripts", "run_superanimal.py"))
                
                if not os.path.exists(venv_python):
                   raise FileNotFoundError(f"No se encontró el entorno GPU en: {venv_python}")
                
                # Construir comando
                cmd = [
                    venv_python,
                    script_path,
                    "--video", video_para_analizar,
                    "--model", model_name
                ]
                
                print(f"[DLC] Ejecutando comando: {' '.join(cmd)}")
                
                # Ejecutar subprocess y capturar salida en tiempo real
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Leer salida línea por línea para logs
                for line in iter(process.stdout.readline, ''):
                    print(f"[Subprocess] {line.strip()}")
                    # Podríamos parsear % aquí si el script lo escupiera
                
                process.stdout.close()
                return_code = process.wait()
                
                if return_code != 0:
                    raise Exception(f"El análisis falló con código de salida {return_code}. Revisa la consola para más detalles.")

                # Guardar el resultado en el diccionario compartido
                analysis_state["video_final"] = video_para_analizar
                analysis_state["done"] = True
            except Exception as e:
                analysis_state["error"] = str(e)
                analysis_state["done"] = True

        # Lanzar el hilo de análisis con los parámetros capturados
        dlc_thread = threading.Thread(
            target=run_dlc_analysis, 
            args=(t_start_val, t_end_val, force_cpu_val, ruta_video_val, supermodel_val, video_adapt_val, dest_folder_val)
        )
        dlc_thread.start()
        
        # Bucle de actualización de UI (Progreso aproximado)
        progreso_simulado = 0.0
        while not analysis_state["done"]:
            # Incremento lento y asintótico para no llegar al 100% antes de tiempo
            if progreso_simulado < 0.3: # Carga de modelo (30%)
                progreso_simulado += 0.005
                progress_text.text(f"⏳ Cargando pesos del modelo ({int(progreso_simulado*100)}%)...")
            elif progreso_simulado < 0.9: # Procesamiento (30% -> 90%)
                progreso_simulado += 0.001
                progress_text.text(f"🧠 Analizando frames con SuperAnimal ({int(progreso_simulado*100)}%)...")
            
            progress_bar.progress(min(progreso_simulado, 0.99))
            time.sleep(1) # Actualizar cada segundo
            
        # Al finalizar el hilo
        if analysis_state["error"]:
            st.error(f"Error durante el análisis de DLC: {analysis_state['error']}")
            st.stop()
        
        # Sincronizar el video final analizado (especialmente si fue un recorte)
        if "video_final" in analysis_state:
            st.session_state["ultimo_video_analizado"] = analysis_state["video_final"]
            save_session()
        
        progress_bar.progress(1.0)
        progress_text.success("🏁 ¡Procesamiento completado!")
        status_container.update(label="✅ Inferencia completada. Cargando resultados...", state="complete")
        
        try:
            # Buscar el archivo .h5 o .csv generado
            import glob
            dest_folder = os.path.dirname(ruta_video)
            video_usado = st.session_state.get("ultimo_video_analizado", ruta_video)
            base_name_usado = os.path.splitext(os.path.basename(video_usado))[0]
            
            # Buscar archivos que empiecen con el nombre del video analizado
            possible_files = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*.csv"))
            if not possible_files:
                # Intentar convertir de h5 a csv si solo existe h5
                h5_files = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*.h5"))
                if h5_files:
                    deeplabcut.analyze_videos_converth5_to_csv([video_usado], videotype='mp4', listofvideos=True)
                    possible_files = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*.csv"))

                # Cargar el archivo con más reciente (usualmente el adaptado si existe)
                latest_csv = max(possible_files, key=os.path.getctime)
                
                # --- INTEGRACIÓN NUEVA: GENERACIÓN DE VIDEO PERSONALIZADO ---
                try:
                    import json
                    import sys
                    status_container.update(label="🎨 Generando video etiquetado (esto puede tardar unos minutos)...", state="running")
                    
                    zones_json = json.dumps(st.session_state.get("zonas_configuradas", []))
                    render_script = os.path.abspath(os.path.join("src", "scripts", "render_video.py"))
                    
                    # Usamos el mismo python de la app (venv_311) para asegurar dependencias de cv2/moviepy
                    render_cmd = [
                        sys.executable, 
                        render_script,
                        "--video", video_usado,
                        "--csv", latest_csv,
                        "--zones", zones_json
                    ]
                    
                    print(f"[App] Ejecutando renderizado: {render_cmd}")
                    subprocess.run(render_cmd, check=True)
                    st.toast("✅ Video etiquetado generado correctamente")
                    
                except Exception as e:
                    print(f"Error generando video: {e}")
                    st.error(f"Error generando video etiquetado: {e}")
                # -------------------------------------------------------------

                df_dlc = pd.read_csv(latest_csv, header=[0, 1, 2], index_col=0)
                # Convertir formato DLC a formato de la App
                scorer = df_dlc.columns.get_level_values(0)[0]
                bodyparts = df_dlc.columns.get_level_values(1).unique()
                # Intentar encontrar la nariz o centro
                rep_bp = 'snout' if 'snout' in bodyparts else bodyparts[0]
                resultados_data = []
                cap = cv2.VideoCapture(ruta_video)
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                for i, (idx, row) in enumerate(df_dlc.iterrows()):
                    # El tiempo en el CSV es relativo al recorte. Sumamos 'inicio' para tiempo real.
                    time_s = (i / fps) + inicio
                    # Como ya es un recorte físico, no necesitamos filtrar por inicio/fin aquí,
                    # pero lo dejamos por seguridad si algo falló en el recorte.
                    if time_s > fin + 0.5: break # Margen de error
                    x = row[(scorer, rep_bp, 'x')]
                    y = row[(scorer, rep_bp, 'y')]
                    
                    # --- NUEVA LÓGICA DE COMPORTAMIENTO ---
                    is_grooming = False
                    is_thigmotaxis = False
                    
                    if not (np.isnan(x) or np.isnan(y)):
                        zona_actual = checar_zona((x, y), zonas)
                        
                        # Thigmotaxis
                        is_thigmotaxis = detectar_thigmotaxis((x,y), zona_actual, zonas)
                        
                        # Grooming (Requiere cola)
                        # Buscamos 'tailbase' o 'tail_base' o el último punto
                        tail_bp = next((bp for bp in bodyparts if 'tail' in bp), bodyparts[-1])
                        tx = row[(scorer, tail_bp, 'x')]
                        ty = row[(scorer, tail_bp, 'y')]
                        
                        if i > 0:
                            # Velocidad aprox (distancia desde frame anterior / tiempo)
                            prev_row = df_dlc.iloc[i-1]
                            prev_x = prev_row[(scorer, rep_bp, 'x')]
                            prev_y = prev_row[(scorer, rep_bp, 'y')]
                            if not (np.isnan(prev_x) or np.isnan(prev_y)):
                                dist_frame = calcular_distancia((x,y), (prev_x, prev_y))
                                vel = dist_frame * fps # px/s
                                is_grooming = detectar_grooming((x,y), (tx,ty), vel)
                    else:
                        zona_actual = "No detectado"

                    resultados_data.append({
                        "Tiempo (s)": time_s,
                        "Zona": zona_actual,
                        "x": x,
                        "y": y,
                        "Grooming": is_grooming,
                        "Thigmotaxis": is_thigmotaxis
                    })
                # Mostrar video procesado si existe
                labeled_video = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*labeled.mp4"))
                if labeled_video:
                    video_path = labeled_video[0]
                    st.info(f"📁 Cargando video desde: `{os.path.basename(video_path)}`")
                    
                    # Leemos el archivo como bytes
                    try:
                        with open(video_path, 'rb') as vf:
                            video_bytes = vf.read()
                        
                        # Usamos un key único basado en el tiempo para forzar recarga en el navegador
                        import time
                        st.video(video_bytes, format="video/mp4")
                        
                        # Botón de descarga de respaldo
                        st.download_button(
                            label="⬇️ Descargar Video Etiquetado (Si no se reproduce arriba)",
                            data=video_bytes,
                            file_name=os.path.basename(video_path),
                            mime="video/mp4"
                        )
                    except Exception as ev:
                        st.error(f"Error leyendo video: {ev}")
            else:
                st.error("No se encontraron archivos de resultados de DeepLabCut.")
                st.stop()
        except Exception as e:
            st.error(f"Error al cargar resultados de DLC: {e}")
            st.stop()
    else:
        # --- MODO YOLO (EXISTENTE) ---
        # Cargar modelo (pose preferido)
        model = None
        if usar_modelo_real:
            try:
                # Intentar cargar best.pt o yolov8n-pose.pt por defecto si es real
                model_target = modelo_path
                if model_target == "yolov8n.pt":  # Sugerir pose si usan el default n
                     st.info("💡 Consejo: Usa un modelo '-pose.pt' para detección postural.")
                
                model = YOLO(model_target)
                st.success(f"Modelo `{model_target}` cargado correctamente.")
            except Exception as e:
                st.error(f"Error cargando modelo: {e}")
                st.stop()

        cap = cv2.VideoCapture(ruta_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30 # Fallback
        
        frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Saltamos al segundo de inicio del recorte
        cap.set(cv2.CAP_PROP_POS_MSEC, inicio * 1000)

        barra_progreso = st.progress(0)
        
        # Estructura para resultados reales: [tiempo, zona, x, y, nose_x, nose_y, tail_x, tail_y]
        resultados_data = [] 
        
        tiempo_limite = max(fin - inicio, 0.1)  # evitar división entre 0
        st.toast("Iniciando análisis con YOLO...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            tiempo_actual_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            tiempo_s = tiempo_actual_ms / 1000.0
            
            if tiempo_s > fin:
                break

            centro_raton = (0, 0)
            nose_pt = (0, 0)
            tail_pt = (0, 0)

            # --- A. DETECCIÓN (YOLO O SIMULACIÓN) ---
            if usar_modelo_real and model:
                results = model(frame, conf=confianza, verbose=False)
                res = results[0]
                
                # Dibujar detecciones
                frame = res.plot()

                if len(res.boxes) > 0:
                    # Centro por defecto (bounding box)
                    box = res.boxes[0].xywh.cpu().numpy()[0]
                    centro_raton = (int(box[0]), int(box[1]))
                    
                    # Si es modelo Pose, extraemos puntos clave
                    if hasattr(res, "keypoints") and res.keypoints is not None:
                        try:
                            pts = res.keypoints.xy.cpu().numpy()[0] # [N, 2]
                            if len(pts) > 0:
                                # YOLOv8-Pose suele tener: 0: Nariz, 1-2: Ojos, 3-4: Orejas... 
                                # Pero esto depende del entrenamiento. Asumiremos 0 como nariz.
                                nose_pt = (int(pts[0][0]), int(pts[0][1]))
                                # Usamos la nariz como centro principal si está disponible
                                if nose_pt != (0, 0):
                                    centro_raton = nose_pt
                                
                                # Intentamos agarrar la cola (último punto usualmente en modelos de ratones custom)
                                if len(pts) > 16: # Asumiendo modelo completo
                                    tail_pt = (int(pts[16][0]), int(pts[16][1]))
                        except:
                            pass
            else:
                # Simulación de ratón: Random Walk dentro de las zonas configuradas
                if zonas:
                    import random
                    if "sim_pos" not in st.session_state:
                         # Iniciar en el centro de la primera zona o del frame
                         cx_init = int(zonas[0]["left"] + zonas[0]["width"]/2)
                         cy_init = int(zonas[0]["top"] + zonas[0]["height"]/2)
                         st.session_state["sim_pos"] = [cx_init, cy_init]
                         st.session_state["sim_target"] = [cx_init, cy_init]

                    # Mover hacia el objetivo
                    curr_x, curr_y = st.session_state["sim_pos"]
                    tgt_x, tgt_y = st.session_state["sim_target"]
                    
                    dx = tgt_x - curr_x
                    dy = tgt_y - curr_y
                    dist = (dx**2 + dy**2)**0.5
                    
                    speed = 15  # Pixeles por frame
                    
                    if dist < speed:
                        # Llegó, nuevo objetivo
                        z_dest = random.choice(zonas)
                        tgt_x = z_dest["left"] + random.random() * z_dest["width"]
                        tgt_y = z_dest["top"] + random.random() * z_dest["height"]
                        st.session_state["sim_target"] = [tgt_x, tgt_y]
                    else:
                        # Avanzar
                        curr_x += (dx / dist) * speed
                        curr_y += (dy / dist) * speed
                        st.session_state["sim_pos"] = [curr_x, curr_y]
                    
                    centro_raton = (int(curr_x), int(curr_y))
                else:
                    # Fallback circular si no hay zonas
                    h, w, _ = frame.shape
                    import math
                    t = time.time()
                    cx = int(w / 2 + 150 * math.cos(t * 1.5))
                    cy = int(h / 2 + 100 * math.sin(t * 1.5))
                    centro_raton = (cx, cy)
                
                cv2.circle(frame, centro_raton, 10, (0, 0, 255), -1)

            # --- B. LÓGICA DE ZONAS Y COMPORTAMIENTO ---
            zona_actual = checar_zona(centro_raton, zonas)
            
            # Thigmotaxis
            is_thigmotaxis = detectar_thigmotaxis(centro_raton, zona_actual, zonas)
            
            # Grooming
            # Necesitamos velocidad. Usamos variable estática o session state para frame anterior
            if 'prev_pos' not in st.session_state:
                st.session_state.prev_pos = centro_raton
            
            dist_frame = calcular_distancia(centro_raton, st.session_state.prev_pos)
            vel = dist_frame * fps # px/s aprox
            st.session_state.prev_pos = centro_raton
            
            is_grooming = False
            if nose_pt != (0,0) and tail_pt != (0,0):
                is_grooming = detectar_grooming(nose_pt, tail_pt, vel)

            # Guardamos en la lista para el DataFrame final
            resultados_data.append({
                "Tiempo (s)": tiempo_s,
                "Zona": zona_actual,
                "x": centro_raton[0],
                "y": centro_raton[1],
                "Grooming": is_grooming,
                "Thigmotaxis": is_thigmotaxis
            })

            # --- C. DIBUJAR ZONAS SOBRE EL VIDEO ---
            overlay = frame.copy()
            for z in zonas:
                color = (0, 255, 0) if z["Nombre Zona"] == zona_actual else (255, 0, 0)
                p1 = (int(z["left"]), int(z["top"]))
                p2 = (int(z["left"] + z["width"]), int(z["top"] + z["height"]))
                cv2.rectangle(overlay, p1, p2, color, 2)
                cv2.putText(overlay, z["Nombre Zona"], (p1[0], p1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

            # --- D. ACTUALIZAR INTERFAZ ---
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            metric_placeholder.metric("Zona actual", zona_actual)

            progreso = (tiempo_s - inicio) / tiempo_limite
            barra_progreso.progress(min(max(progreso, 0.0), 1.0))

        cap.release()
        st.success("✅ Análisis completado.")

    # ================== 9. PERSISTENCIA EN BASE DE DATOS ==================
    df_final = pd.DataFrame(resultados_data)
    st.session_state["resultados_analisis"] = df_final
    
    # Calcular métricas globales
    total_time = len(df_final) / (fps if 'fps' in locals() else 30.0)
    grooming_total = df_final["Grooming"].sum() / (fps if 'fps' in locals() else 30.0)
    thigmo_total = df_final["Thigmotaxis"].sum() / (fps if 'fps' in locals() else 30.0)
    
    time_open = df_final[df_final["Zona"].str.contains("Abierto")]["Tiempo (s)"].count() / fps
    time_closed = df_final[df_final["Zona"].str.contains("Cerrado")]["Tiempo (s)"].count() / fps
    time_center = df_final[df_final["Zona"].str.contains("Centro")]["Tiempo (s)"].count() / fps
    
    # --- Guardar persistencia de CSV detallado ---
    import datetime
    video_basename = os.path.basename(ruta_video)
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"detailed_{timestamp_str}_{video_basename}.csv"
    
    # Crear carpeta si no existe
    results_dir = os.path.join(os.getcwd(), "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    csv_path = os.path.join(results_dir, csv_filename)
    df_final.to_csv(csv_path, index=False)
    print(f"[+] Detalle guardado en: {csv_path}")
    
    # Guardar en PostgreSQL
    try:
        from src.db.connection import get_db_engine
        from sqlalchemy import text
        
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                # 1. Insertar Experimento (si no existe lógica previa de creación, lo creamos aquí)
                # OJO: Idealmente esto se crea en Ingesta, pero por ahora lo registramos al finalizar análisis
                # Asumimos que el usuario actual es el creador.
                usr_email = st.session_state.get("user", "admin")
                
                # Buscar ID de usuario
                res_usr = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": usr_email}).fetchone()
                user_id = res_usr[0] if res_usr else None
                
                # Datos de sesión o defaults
                rat_id = st.session_state.get("id_raton_actual", "Unknown-Rat")
                # Obtener tratamiento guardado por la página de Ingesta (puede venir como 'treatment' o 'tratamiento_text')
                treatment = st.session_state.get("treatment") or st.session_state.get("tratamiento_text") or "Experimental"
                responsible = st.session_state.get("user_name", "Investigador")

                # Evitar duplicados: si ya existe un experimento con este video_path, actualizarlo
                existing = conn.execute(text("SELECT id FROM experiments WHERE video_path = :path LIMIT 1"), {"path": ruta_video}).fetchone()
                if existing:
                    # Actualizar datos y marcar como procesado
                    res_update = conn.execute(text(
                        """
                        UPDATE experiments
                        SET treatment = :treat,
                            experiment_date = CURRENT_DATE,
                            responsible = :resp,
                            duration_seconds = :dur,
                            created_by = COALESCE(:uid, created_by),
                            processed = TRUE
                        WHERE id = :eid
                        RETURNING id
                        """), {
                        "treat": treatment,
                        "resp": responsible,
                        "dur": total_time,
                        "uid": user_id,
                        "eid": existing[0]
                    }).fetchone()
                    exp_id = res_update[0]
                else:
                    insert_exp = text("""
                        INSERT INTO experiments (rat_id, treatment, experiment_date, responsible, video_path, duration_seconds, created_by, processed)
                        VALUES (:rid, :treat, CURRENT_DATE, :resp, :path, :dur, :uid, TRUE)
                        RETURNING id
                    """)
                    res_exp = conn.execute(insert_exp, {
                        "rid": rat_id,
                        "treat": treatment,
                        "resp": responsible,
                        "path": ruta_video,
                        "dur": total_time,
                        "uid": user_id
                    }).fetchone()
                    exp_id = res_exp[0]
                
                # 2. Insertar Resultados (Incluyendo trajectory_path)
                insert_res = text("""
                    INSERT INTO analysis_results 
                    (experiment_id, total_distance, time_open_arms, time_closed_arms, time_center, grooming_duration, thigmotaxis_duration, status, trajectory_path)
                    VALUES (:eid, 0, :topen, :tclosed, :tcen, :groom, :thig, 'completed', :path)
                """)
                
                conn.execute(insert_res, {
                    "eid": exp_id,
                    "topen": float(time_open),
                    "tclosed": float(time_closed),
                    "tcen": float(time_center),
                    "groom": float(grooming_total),
                    "thig": float(thigmo_total),
                    "path": csv_path
                })
                conn.commit()
                st.toast("✅ Resultados guardados en Base de Datos exitosamente.")
                print(f"[+] Experimento {exp_id} guardado en BD.")
        else:
            st.error("No se pudo conectar a la BD para guardar resultados.")
            
    except Exception as e:
        st.error(f"Error guardando en BD: {e}")
        print(f"[-] Error DB Save: {e}")
    
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">📊 Resumen Guardado</div>',
        unsafe_allow_html=True,
    )
    st.info(f"Se han procesado {len(df_final)} registros. Los resultados están listos en la pestaña de Dashboard.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Permanencia en Zonas")
        conteo = df_final["Zona"].value_counts()
        st.bar_chart(conteo)
    
    with c2:
        st.subheader("🐭 Comportamientos Avanzados")
        total_time = len(df_final) / (fps if 'fps' in locals() else 30.0)
        grooming_total = df_final["Grooming"].sum() / (fps if 'fps' in locals() else 30.0)
        thigmo_total = df_final["Thigmotaxis"].sum() / (fps if 'fps' in locals() else 30.0)
        
        st.metric("Acicalamiento (Grooming)", f"{grooming_total:.1f} s")
        st.metric("Contacto Paredes (Thigmotaxis)", f"{thigmo_total:.1f} s")
        st.metric("Tiempo Total Analizado", f"{total_time:.1f} s")
    st.markdown("</div>", unsafe_allow_html=True)
