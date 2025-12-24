import streamlit as st
import cv2
import numpy as np
import tempfile
import pandas as pd
import time
from ultralytics import YOLO

# ================== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
    st.stop()

# OJO: el set_page_config ya se hace en Login/Home.
# No lo repetimos aquí para evitar errores.
# st.set_page_config(page_title="Análisis IA", layout="wide")

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
st.markdown(
    '<div class="tt-ia-title">🧠 Procesamiento de Comportamiento (YOLOv8)</div>',
    unsafe_allow_html=True,
)
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
    usar_modelo_real = st.toggle("Usar modelo YOLO real (.pt)", value=False)
    modelo_path = st.text_input("Ruta del modelo (.pt):", "yolov8n.pt")
    confianza = st.slider("Umbral de confianza", 0.0, 1.0, 0.5)
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
    # Cargar modelo (solo si se pide)
    model = None
    if usar_modelo_real:
        try:
            model = YOLO(modelo_path)
            st.success(f"Modelo `{modelo_path}` cargado correctamente.")
        except Exception as e:
            st.error(f"Error cargando modelo: {e}")
            st.stop()

    cap = cv2.VideoCapture(ruta_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Saltamos al segundo de inicio del recorte
    cap.set(cv2.CAP_PROP_POS_MSEC, inicio * 1000)

    barra_progreso = st.progress(0)
    historial_zonas = []
    tiempo_limite = max(fin - inicio, 0.1)  # evitar división entre 0

    st.toast("Iniciando análisis frame por frame...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        tiempo_actual_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if tiempo_actual_ms > (fin * 1000):
            break

        centro_raton = (0, 0)

        # --- A. DETECCIÓN (YOLO O SIMULACIÓN) ---
        if usar_modelo_real and model:
            results = model(frame, conf=confianza, verbose=False)
            res = results[0]

            # Recorte con bounding boxes
            frame = res.plot()

            if len(res.boxes) > 0:
                box = res.boxes[0].xywh.cpu().numpy()[0]  # x_centro, y_centro, w, h
                centro_raton = (int(box[0]), int(box[1]))
        else:
            # Simulación de ratón moviéndose en círculo
            h, w, _ = frame.shape
            import math

            t = time.time()
            cx = int(w / 2 + 100 * math.cos(t * 2))
            cy = int(h / 2 + 100 * math.sin(t * 2))
            centro_raton = (cx, cy)
            cv2.circle(frame, centro_raton, 10, (0, 0, 255), -1)

        # --- B. LÓGICA DE ZONAS ---
        zona_actual = checar_zona(centro_raton, zonas)
        historial_zonas.append(zona_actual)

        # --- C. DIBUJAR ZONAS SOBRE EL VIDEO ---
        overlay = frame.copy()
        for z in zonas:
            color = (0, 255, 0) if z["Nombre Zona"] == zona_actual else (255, 0, 0)
            p1 = (int(z["left"]), int(z["top"]))
            p2 = (int(z["left"] + z["width"]), int(z["top"] + z["height"]))
            cv2.rectangle(overlay, p1, p2, color, 2)
            cv2.putText(
                overlay,
                z["Nombre Zona"],
                (p1[0], p1[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        # --- D. ACTUALIZAR INTERFAZ ---
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

        metric_placeholder.metric("Zona actual", zona_actual)

        progreso = (tiempo_actual_ms / 1000 - inicio) / tiempo_limite
        barra_progreso.progress(min(max(progreso, 0.0), 1.0))

    cap.release()
    st.success("✅ Análisis completado.")

    # ================== 9. RESUMEN ==================
    st.markdown('<div class="tt-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="tt-section-title">📊 Resumen de la sesión</div>',
        unsafe_allow_html=True,
    )
    df_res = pd.DataFrame(historial_zonas, columns=["Zona"])
    conteo = df_res["Zona"].value_counts()
    st.bar_chart(conteo)
    st.markdown("</div>", unsafe_allow_html=True)
