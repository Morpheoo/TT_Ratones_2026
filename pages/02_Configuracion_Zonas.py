import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from moviepy.editor import VideoFileClip

# =============== 1. VERIFICAR LOGIN ==================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Debes iniciar sesión en la página 🔐 Login antes de usar el prototipo.")
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
    key="canvas_zonas",
)
st.markdown("</div>", unsafe_allow_html=True)

# =============== 9. NOMBRES Y REESCALADO =================
if canvas_result.json_data is not None:
    objects = pd.json_normalize(canvas_result.json_data["objects"])

    if "lista_nombres_zonas" not in st.session_state:
        st.session_state["lista_nombres_zonas"] = []

    num_cajas = len(objects)
    num_nombres = len(st.session_state["lista_nombres_zonas"])

    if num_cajas > num_nombres:
        diferencia = num_cajas - num_nombres
        for _ in range(diferencia):
            tipo_base = tipo_zona_visual
            conteo_previo = sum(
                1 for nombre in st.session_state["lista_nombres_zonas"]
                if nombre.startswith(tipo_base)
            )
            nuevo_nombre = f"{tipo_base} {conteo_previo + 1}"
            st.session_state["lista_nombres_zonas"].append(nuevo_nombre)
    elif num_cajas < num_nombres:
        st.session_state["lista_nombres_zonas"] = st.session_state["lista_nombres_zonas"][:num_cajas]

    if not objects.empty:
        st.markdown('<div class="tt-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="tt-section-title">📝 Zonas identificadas</div>',
            unsafe_allow_html=True,
        )

        datos_visuales = objects[["left", "top", "width", "height"]].copy()
        datos_visuales["Nombre Zona"] = st.session_state["lista_nombres_zonas"]

        df_editado = st.data_editor(
            datos_visuales,
            num_rows="dynamic",
            column_config={
                "left": st.column_config.NumberColumn("X (canvas)", disabled=True),
                "top": st.column_config.NumberColumn("Y (canvas)", disabled=True),
                "width": "Ancho",
                "height": "Alto",
                "Nombre Zona": st.column_config.TextColumn("Nombre", disabled=False),
            },
            key="editor_zonas_auto",
        )

        st.session_state["lista_nombres_zonas"] = df_editado["Nombre Zona"].tolist()

        if st.button("💾 Guardar configuración final"):
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
            st.success("✅ Configuración guardada y reescalada a la resolución del video.")
            st.write(f"Factor de escala aplicado: **{factor_escala:.2f}×**")
            st.json(zonas_para_guardar)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.session_state["lista_nombres_zonas"] = []
