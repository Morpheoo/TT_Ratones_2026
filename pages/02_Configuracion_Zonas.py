import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from moviepy.editor import VideoFileClip
import os
import sys

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

# =============== 2. SELECTOR DE TEMA =================
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

st.sidebar.markdown("### Herramientas de Zonas")

# =============== 3. CSS GLOBAL =================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {colors["page_bg"]};
    }}

    .tt-zonas-title {{
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: {colors["text_main"]};
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }}

    .tt-zonas-subtitle {{
        font-size: 0.95rem;
        color: {colors["text_main"]};
        opacity: 0.9;
        margin-bottom: 1.0rem;
    }}

    .tt-card {{
        background-color: {colors["card_bg"]};
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 14px 30px {colors["shadow"]};
        border: 1px solid rgba(15,23,42,0.18);
        margin-bottom: 1.4rem;
        color: {colors["text_main"]};
    }}
    /* TODO el texto dentro de la tarjeta en verde oscuro / claro */
    .tt-card p,
    .tt-card span,
    .tt-card div {{
        color: {colors["text_main"]} !important;
    }}

    .tt-section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {colors["text_main"]};
        margin-bottom: 0.6rem;
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

    /* Hacemos que los st.info/st.warning usen texto verde también */
    .stAlert {{
        color: {colors["text_main"]} !important;
        border-radius: 14px;
    }}

    /* Tabla/Editor: textos en color del tema */
    .stDataFrame, .stDataEditor div, .stDataEditor span, .stDataEditor label {{
        color: {colors["text_main"]} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============== 4. ENCABEZADO =================
st.markdown(
    '<div class="tt-zonas-title">⚙️ Configuración de Zonas (ROI)</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="tt-zonas-subtitle">'
    'Dibuja las regiones de interés (brazos abiertos, cerrados y zona central) '
    'sobre un fotograma del laberinto en cruz elevado. Las coordenadas se '
    'escalarán automáticamente a la resolución original del video.'
    '</div>',
    unsafe_allow_html=True,
)

# =============== 5. CARGA DEL VIDEO =================
if "ruta_video_actual" not in st.session_state:
    st.warning("⚠️ No hay video cargado. Ve a **Ingesta de Video** primero.")
    st.stop()

ruta_video = st.session_state["ruta_video_actual"]
tiempo_inicio = st.session_state.get("inicio_recorte", 0)

try:
    clip = VideoFileClip(ruta_video)
    ancho_real, alto_real = clip.size
    frame_array = clip.get_frame(tiempo_inicio)
    image_original = Image.fromarray(frame_array)
    clip.close()
except Exception as e:
    st.error(f"Error al cargar el video: {e}")
    st.stop()

# =============== 6. CÁLCULO DE ESCALA =================
ANCHO_CANVAS = 800
factor_escala = ancho_real / ANCHO_CANVAS
ALTO_CANVAS = int(alto_real / factor_escala)
image_display = image_original.resize((ANCHO_CANVAS, ALTO_CANVAS))

st.info(
    f"📏 Resolución original: {ancho_real}×{alto_real} px · "
    f"Canvas de dibujo: {ANCHO_CANVAS}×{ALTO_CANVAS} px (factor de escala ≈ {factor_escala:.2f}×)."
)

# =============== 7. HERRAMIENTAS EN SIDEBAR =================
tipo_zona_visual = st.sidebar.radio(
    "Tipo para la **siguiente** zona:",
    ("Brazo Abierto", "Brazo Cerrado", "Centro"),
)

colores = {
    "Brazo Abierto": "rgba(244, 63, 94, 0.35)",
    "Brazo Cerrado": "rgba(59, 130, 246, 0.35)",
    "Centro": "rgba(234, 179, 8, 0.35)",
}
color_actual = colores.get(tipo_zona_visual, "rgba(148, 163, 184, 0.35)")

st.markdown(
    '<div class="tt-card">'
    '<div class="tt-section-title">🖊️ Dibujo de ROIs sobre el fotograma</div>'
    '<p>Haz clic y arrastra para dibujar rectángulos sobre el laberinto. '
    'Puedes cambiar el tipo de zona en el menú lateral.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# =============== 7.5 HERRAMIENTAS DE PLANTILLA =================
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Plantillas")

import src.zone_templates as template_manager

# =============== 7.5 HERRAMIENTAS DE PLANTILLA =================
st.sidebar.markdown("---")
st.sidebar.markdown("### 💾 Gestor de Plantillas")

if "canvas_key" not in st.session_state:
    st.session_state["canvas_key"] = "canvas_zonas_v1"



# --- Cargar / Borrar Plantilla ---
plantillas_disponibles = template_manager.list_templates()
if plantillas_disponibles:
    st.sidebar.markdown("---")
    st.sidebar.caption("Mis Plantillas")
    p_seleccionada = st.sidebar.selectbox("Seleccionar", plantillas_disponibles)
    
    col_p1, col_p2 = st.sidebar.columns(2)
    if col_p1.button("📂 Cargar"):
        data = template_manager.load_template(p_seleccionada)
        if data:
            st.session_state["canvas_initial_json"] = data["canvas"]
            st.session_state["lista_nombres_zonas"] = data["names"]
            import uuid
            st.session_state["canvas_key"] = f"canvas_zonas_{uuid.uuid4()}"
            st.rerun()
            
    if col_p2.button("🗑️ Borrar"):
        template_manager.delete_template(p_seleccionada)
        st.rerun()
else:
    st.sidebar.info("No hay plantillas guardadas.")

st.sidebar.markdown("---")
if st.sidebar.button("🧩 Cargar Default (Cruz EPM)"):
    # Valores por defecto optimizados (+35px X offset, brazos ajustados)
    cx = (ANCHO_CANVAS // 2) + 35
    cy = ALTO_CANVAS // 2
    
    ancho_brazo = 80
    largo_abierto = 180
    largo_cerrado = 220 
    
    # Colores
    color_abierto = "rgba(244, 63, 94, 0.35)"
    color_cerrado = "rgba(59, 130, 246, 0.35)" # Azul
    color_centro = "rgba(234, 179, 8, 0.35)"   # Amarillo

    preset_objects = [
        {"type": "rect", "left": cx - ancho_brazo//2, "top": cy - ancho_brazo//2, 
         "width": ancho_brazo, "height": ancho_brazo, "fill": color_centro, "stroke": "#ffffff", "strokeWidth": 2},
        {"type": "rect", "left": cx - ancho_brazo//2, "top": cy - ancho_brazo//2 - largo_cerrado, 
         "width": ancho_brazo, "height": largo_cerrado, "fill": color_cerrado, "stroke": "#ffffff", "strokeWidth": 2},
        {"type": "rect", "left": cx - ancho_brazo//2, "top": cy + ancho_brazo//2, 
         "width": ancho_brazo, "height": largo_cerrado, "fill": color_cerrado, "stroke": "#ffffff", "strokeWidth": 2},
        {"type": "rect", "left": cx - ancho_brazo//2 - largo_abierto, "top": cy - ancho_brazo//2, 
         "width": largo_abierto, "height": ancho_brazo, "fill": color_abierto, "stroke": "#ffffff", "strokeWidth": 2},
        {"type": "rect", "left": cx + ancho_brazo//2, "top": cy - ancho_brazo//2, 
         "width": largo_abierto, "height": ancho_brazo, "fill": color_abierto, "stroke": "#ffffff", "strokeWidth": 2},
    ]
    
    plantilla_json = {"version": "4.4.0", "objects": preset_objects}
    st.session_state["canvas_initial_json"] = plantilla_json
    st.session_state["lista_nombres_zonas"] = ["Centro 1", "Brazo Cerrado 1", "Brazo Cerrado 2", "Brazo Abierto 1", "Brazo Abierto 2"]
    import uuid
    st.session_state["canvas_key"] = f"canvas_zonas_{uuid.uuid4()}"
    st.rerun()


if st.sidebar.button("🗑️ Limpiar Pantalla"):
    st.session_state["canvas_initial_json"] = None
    st.session_state["lista_nombres_zonas"] = []
    # Force reload
    import uuid
    st.session_state["canvas_key"] = f"canvas_zonas_{uuid.uuid4()}"
    st.rerun()

# =============== 8. CANVAS =================
st.markdown('<div class="tt-card">', unsafe_allow_html=True)
canvas_result = st_canvas(
    fill_color=color_actual,
    stroke_width=2,
    stroke_color="#ffffff",
    background_image=image_display,
    update_streamlit=True,
    height=ALTO_CANVAS,
    width=ANCHO_CANVAS,
    drawing_mode="rect",
    initial_drawing=st.session_state.get("canvas_initial_json", None),
    key=st.session_state["canvas_key"],
)
st.markdown("</div>", unsafe_allow_html=True)

# --- Guardar Plantilla Actual (Debe ir después del canvas para leer canvas_result) ---
with st.sidebar.expander("Guardar Actual"):
    nombre_plantilla = st.text_input("Nombre de la plantilla")
    if st.button("Guardar"):
        if canvas_result.json_data and nombre_plantilla:
            template_manager.save_template(
                nombre_plantilla, 
                canvas_result.json_data, 
                st.session_state.get("lista_nombres_zonas", [])
            )
            st.toast(f"Plantilla '{nombre_plantilla}' guardada!")
        else:
            st.error("Dibuja algo o ponle nombre.")

# =============== 9. NOMBRES Y EDICIÓN/BORRADO =================
if canvas_result.json_data is not None:
    objects = pd.json_normalize(canvas_result.json_data["objects"])

    if "lista_nombres_zonas" not in st.session_state:
        st.session_state["lista_nombres_zonas"] = []

    # Sincronización básica de longitud
    num_cajas = len(objects)
    num_nombres = len(st.session_state["lista_nombres_zonas"])

    if num_cajas > num_nombres:
        diferencia = num_cajas - num_nombres
        for _ in range(diferencia):
            st.session_state["lista_nombres_zonas"].append(f"{tipo_zona_visual} {len(st.session_state['lista_nombres_zonas']) + 1}")
    elif num_cajas < num_nombres:
        st.session_state["lista_nombres_zonas"] = st.session_state["lista_nombres_zonas"][:num_cajas]

    if not objects.empty:
        st.markdown('<div class="tt-card">', unsafe_allow_html=True)
        
        c_table, c_actions = st.columns([2, 1])
        
        with c_table:
            st.markdown('<div class="tt-section-title">📝 Zonas identificadas</div>', unsafe_allow_html=True)
            datos_visuales = objects[["left", "top", "width", "height"]].copy()
            datos_visuales["Nombre Zona"] = st.session_state["lista_nombres_zonas"]

            df_editado = st.data_editor(
                datos_visuales,
                num_rows="fixed",
                column_config={
                    "left": st.column_config.NumberColumn("X", disabled=True),
                    "top": st.column_config.NumberColumn("Y", disabled=True),
                    "Nombre Zona": st.column_config.TextColumn("Nombre", disabled=False),
                },
                key="editor_zonas_auto",
            )
            # Actualizar nombres en tiempo real
            st.session_state["lista_nombres_zonas"] = df_editado["Nombre Zona"].tolist()

        with c_actions:
            st.markdown('<div class="tt-section-title">🗑️ Eliminar Específicas</div>', unsafe_allow_html=True)
            to_delete = st.multiselect("Seleccionar zonas para borrar:", options=df_editado["Nombre Zona"])
            
            if st.button("Eliminar Seleccionadas") and to_delete:
                # Lógica de borrado: Mapear nombres a índices, remover de la lista de objetos y recargar
                indices_to_delete = [i for i, name in enumerate(st.session_state["lista_nombres_zonas"]) if name in to_delete]
                
                # Filtrar objetos JSON
                current_objects = canvas_result.json_data["objects"]
                new_objects = [obj for i, obj in enumerate(current_objects) if i not in indices_to_delete]
                
                # Filtrar nombres
                new_names = [name for i, name in enumerate(st.session_state["lista_nombres_zonas"]) if i not in indices_to_delete]
                
                # Actualizar Estado
                updated_json = canvas_result.json_data.copy()
                updated_json["objects"] = new_objects
                
                st.session_state["canvas_initial_json"] = updated_json
                st.session_state["lista_nombres_zonas"] = new_names
                
                import uuid
                st.session_state["canvas_key"] = f"canvas_zonas_{uuid.uuid4()}"
                st.rerun()

        st.markdown("---")
        if st.button("💾 Guardar configuración final del experimento"):
            zonas_para_guardar = []
            for reg in df_editado.to_dict("records"):
                zona_real = {
                    "Nombre Zona": reg["Nombre Zona"],
                    "left": int(reg["left"] * factor_escala),
                    "top": int(reg["top"] * factor_escala),
                    "width": int(reg["width"] * factor_escala),
                    "height": int(reg["height"] * factor_escala),
                }
                zonas_para_guardar.append(zona_real)

            st.session_state["zonas_configuradas"] = zonas_para_guardar
            save_session()
            st.success("✅ Configuración guardada y reescalada a la resolución del video.")
            st.json(zonas_para_guardar)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.session_state["lista_nombres_zonas"] = []
