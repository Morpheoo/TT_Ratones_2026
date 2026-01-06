import streamlit as st
import cv2
import numpy as np
import tempfile
import pandas as pd
import time
import os
import sys
import threading
from moviepy.editor import VideoFileClip

# ================= 0. PERSISTENCIA =================
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from src.session_utils import load_session, save_session

# Cargar sesión antes de validar login
load_session()

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
            import deeplabcut as dlc_lib
            deeplabcut = dlc_lib
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

# ================== 5. VERIFICACIONES DE SEGURIDAD ==================
if "ruta_video_actual" not in st.session_state:
    st.error("⚠️ No hay video seleccionado. Ve a la página **01 · Ingesta de Video**.")
    st.stop()

if "zonas_configuradas" not in st.session_state:
    st.error("⚠️ No hay zonas configuradas. Ve a la página **02 · Configuración de Zonas**.")
    st.stop()

ruta_video = st.session_state["ruta_video_actual"]
zonas = st.session_state["zonas_configuradas"]
inicio = st.session_state.get("inicio_recorte", 0)
fin = st.session_state.get("fin_recorte", 10)  # Default 10 segs si no hay fin

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
        "Motor de Análisis",
        ["YOLOv8 (Tiempo Real)", "DeepLabCut SuperAnimal"],
        index=0
    )
    
    # Actualizar encabezado ahora que 'motor' existe
    header_title = "🧠 Análisis con DeepLabCut" if motor == "DeepLabCut SuperAnimal" else "🧠 Análisis con YOLOv8"
    header_placeholder.markdown(
        f'<div class="tt-ia-title">{header_title}</div>',
        unsafe_allow_html=True,
    )
    
    if motor == "YOLOv8 (Tiempo Real)":
        usar_modelo_real = st.toggle("Usar modelo YOLO real (.pt)", value=False)
        modelo_path = st.text_input("Ruta del modelo (.pt):", "yolov8n.pt")
        confianza = st.slider("Umbral de confianza", 0.0, 1.0, 0.5)
    else:
        # Usamos el estado global
        if st.session_state.get("dlc_device_opt") == "CPU (Forzar)":
            st.info("🛡️ **MODO SEGURO**: Se usará la CPU para el análisis. Más lento, pero evita errores de CUDA.")
        else:
            st.warning("🚀 **MODO GPU ACELERADA**: Si experimental errores, cámbiate a CPU en el menú lateral.")
        
        st.info("🧬 DeepLabCut SuperAnimal utiliza modelos pre-entrenados de alta precisión.")
        supermodel = st.selectbox(
            "SuperModel",
            ["superanimal_topviewmouse"],
            index=0
        )
        video_adapt = st.toggle("Adaptación de video (Auto-entrenamiento rápido)", value=True)
        device_opt = st.radio(
            "Dispositivo de cómputo", 
            ["Auto (Recomendado)", "CPU (Forzar)"], 
            index=1 if st.session_state.get("dlc_device_opt") == "CPU (Forzar)" else 0,
            key="dlc_device_opt",
            horizontal=True,
            help="Obligatorio para la serie RTX 50 (Blackwell) por ahora."
        )
        confianza = 0.1 # DLC pcutoff default
        if deeplabcut is None:
            st.error("❌ DeepLabCut no está instalado o no se pudo cargar.")
            if dlc_import_error:
                with st.expander("Ver detalles del error"):
                    st.code(dlc_import_error)
            
    iniciar = st.button("▶️ INICIAR ANÁLISIS")
    st.markdown("</div>", unsafe_allow_html=True)

    # Placeholder para la métrica de zona actual
    metric_placeholder = st.empty()

# ---- Columna derecha: video
with col_video:
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">🎞️ Video con detecciones</div>',
        unsafe_allow_html=True,
    )
    image_placeholder = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

# ================== 7. FUNCIÓN GEOMÉTRICA ==================
def checar_zona(punto_xy, zonas_lista):
    """
    Revisa en qué zona cae el punto (x, y) del ratón.
    Retorna el nombre de la zona o 'Fuera del Laberinto'.
    """
    x, y = punto_xy
    for zona in zonas_lista:
        x_min = zona["left"]
        x_max = zona["left"] + zona["width"]
        y_min = zona["top"]
        y_max = zona["top"] + zona["height"]

        if x_min <= x <= x_max and y_min <= y <= y_max:
            return zona["Nombre Zona"]
    return "Fuera del Laberinto"

# ================== 8. BUCLE DE PROCESAMIENTO ==================
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
                
                # 4. Cargar motores y ejecutar
                cargar_motores()
                
                deeplabcut.video_inference_superanimal(
                    [video_para_analizar],
                    superanimal_name=model_name,
                    model_name="hrnet_w32",
                    detector_name="fasterrcnn_resnet50_fpn_v2",
                    video_adapt=adapt,
                    dest_folder=dest,
                    create_labeled_video=True,
                    device="cpu" if force_cpu else "auto"
                )
                
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
                    deeplabcut.analyze_videos_converth5_to_csv(dest_folder, [video_usado], videotype='mp4')
                    possible_files = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*.csv"))

            if possible_files:
                # Cargar el archivo con más reciente (usualmente el adaptado si existe)
                latest_csv = max(possible_files, key=os.path.getctime)
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
                    if np.isnan(x) or np.isnan(y):
                        zona_actual = "No detectado"
                    else:
                        zona_actual = checar_zona((x, y), zonas)
                    resultados_data.append({
                        "Tiempo (s)": time_s,
                        "Zona": zona_actual,
                        "x": x,
                        "y": y
                    })
                # Mostrar video procesado si existe
                labeled_video = glob.glob(os.path.join(dest_folder, f"{base_name_usado}*labeled.mp4"))
                if labeled_video:
                    st.video(labeled_video[0])
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
                # Simulación de ratón moviéndose en círculo
                h, w, _ = frame.shape
                import math
                t = time.time()
                cx = int(w / 2 + 150 * math.cos(t * 1.5))
                cy = int(h / 2 + 100 * math.sin(t * 1.5))
                centro_raton = (cx, cy)
                cv2.circle(frame, centro_raton, 10, (0, 0, 255), -1)

            # --- B. LÓGICA DE ZONAS ---
            zona_actual = checar_zona(centro_raton, zonas)
            
            # Guardamos en la lista para el DataFrame final
            resultados_data.append({
                "Tiempo (s)": tiempo_s,
                "Zona": zona_actual,
                "x": centro_raton[0],
                "y": centro_raton[1]
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

    # ================== 9. PERSISTENCIA DE RESULTADOS ==================
    df_final = pd.DataFrame(resultados_data)
    st.session_state["resultados_analisis"] = df_final
    
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">📊 Resumen Guardado</div>',
        unsafe_allow_html=True,
    )
    st.info(f"Se han procesado {len(df_final)} registros. Los resultados están listos en la pestaña de Dashboard.")
    conteo = df_final["Zona"].value_counts()
    st.bar_chart(conteo)
    st.markdown("</div>", unsafe_allow_html=True)
