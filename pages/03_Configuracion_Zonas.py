import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from moviepy.editor import VideoFileClip
import os
import sys

# REGLA #1: set_page_config SIEMPRE primero
st.set_page_config(page_title="Configuración de Zonas - TT 2026", page_icon="⚙️", layout="wide")

if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

from ui_components import generic_splash_loader
from session_utils import load_session, save_session
from simba_roi_bridge import sync_streamlit_rois_to_simba
from access_control import require_researcher
from sidebar_control import apply_sidebar_visibility

SIMBA_PROJECT_FOLDER = os.path.abspath(
    os.path.join(
        "data",
        "simba_projects",
        "New folder",
        "thigmotaxis_optimizado",
        "project_folder",
    )
)

# Cargar sesión antes de validar login
load_session()

# Aplicar control de sidebar
apply_sidebar_visibility()

# =============== 1. VERIFICAR LOGIN Y ROL ==================
require_researcher()  # Solo investigadores y estudiantes, NO admins

# =============== 2. TEMA Y ESTILOS =================
from ui_theme import use_theme
use_theme()

def _infer_zone_family(zone_type: str | None, zone_name: str | None = None) -> str | None:
    label = str(zone_name or "").strip().lower()
    zone_type_lower = str(zone_type or "").strip().lower()

    if "abierto" in label or "abierto" in zone_type_lower or "open" in label:
        return "Brazo Abierto"
    if "cerrado" in label or "cerrado" in zone_type_lower or "closed" in label:
        return "Brazo Cerrado"
    if "centro" in label or "center" in label or zone_type_lower == "centro":
        return "Centro"
    if "pared" in label or "muro" in label or "wall" in label or "pared" in zone_type_lower or "muro" in zone_type_lower:
        return "Pared"
    return None


def _format_zone_name(zone_family: str, index: int) -> str:
    if zone_family == "Centro" and index == 1:
        return "Centro"
    return f"{zone_family} {index}"


def _next_default_zone_name(zone_type: str, existing_names: list[str]) -> str:
    zone_family = _infer_zone_family(zone_type, zone_type) or zone_type
    family_count = sum(
        1 for existing_name in existing_names
        if _infer_zone_family(None, existing_name) == zone_family
    )
    return _format_zone_name(zone_family, family_count + 1)


def _normalize_saved_zone_names(zonas_list: list[dict]) -> list[dict]:
    normalized_zones: list[dict] = []
    family_counts: dict[str, int] = {}

    for zone in zonas_list:
        zone_copy = dict(zone)
        zone_family = _infer_zone_family(zone_copy.get("type"), zone_copy.get("Nombre Zona"))
        if not zone_family:
            normalized_zones.append(zone_copy)
            continue

        family_counts[zone_family] = family_counts.get(zone_family, 0) + 1
        zone_copy["Nombre Zona"] = _format_zone_name(zone_family, family_counts[zone_family])
        normalized_zones.append(zone_copy)

    return normalized_zones


def zones_loading_sequence():
    """Generador para el splash screen de Configuración de Zonas."""
    yield 10, "Validando contexto del video..."
    if "ruta_video_actual" not in st.session_state:
        yield 100, "Error: No hay video cargado"
        return None
    
    ruta_video = st.session_state["ruta_video_actual"]
    
    # Verificar que el archivo existe
    if not os.path.exists(ruta_video):
        yield 100, "Error: Archivo de video no encontrado"
        return None
    
    tiempo_inicio = st.session_state.get("inicio_recorte", 0)
    
    yield 40, "Inicializando motor de video (MoviePy)..."
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(ruta_video)
        
        yield 80, "Extrayendo fotograma de referencia..."
        ancho_real, alto_real = clip.size
        frame_array = clip.get_frame(tiempo_inicio)
        image_original = Image.fromarray(frame_array)
        clip.close()
        
        yield 100, "Zonas listas."
        return {
            "image": image_original,
            "size": (ancho_real, alto_real)
        }
    except Exception as e:
        yield 100, f"Error cargando video: {str(e)}"
        return None

# ================== 2. EJECUCIÓN DEL SPLASH SCREEN (ZONAS) ==================
if "zones_loaded" not in st.session_state:
    st.session_state["_zones_cache"] = generic_splash_loader(zones_loading_sequence())
    st.session_state.zones_loaded = True

# =============== 3. CSS GLOBAL =================
st.markdown(
    """
    <style>
    .tt-zonas-title {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 1.9rem;
        color: var(--text-main);
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }

    .tt-zonas-subtitle {
        font-size: 0.95rem;
        color: var(--text-main);
        opacity: 0.9;
        margin-bottom: 1.0rem;
    }

    .tt-card {
        background-color: var(--card-bg);
        border-radius: 0.5rem;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 4px 15px var(--shadow);
        border: 1px solid var(--card-border);
        border-top: 3px solid var(--primary);
        margin-bottom: 1.4rem;
        color: var(--text-main);
    }
    
    .tt-card p,
    .tt-card span,
    .tt-card div {
        color: var(--text-main) !important;
    }

    .tt-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 0.6rem;
    }

    /* Hacemos que los st.info/st.warning usen texto oscuro/claro */
    .stAlert {
        color: var(--text-main) !important;
        border-radius: 0.5rem;
    }

    /* Tabla/Editor: textos en color del tema */
    .stDataFrame, .stDataEditor div, .stDataEditor span, .stDataEditor label {
        color: var(--text-main) !important;
    }
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

# Datos recuperados del splash
if not st.session_state.get("_zones_cache"):
    st.error("❌ Error cargando recursos de video.")
    st.info("💡 Verifica que hayas cargado un video en la página **Ingesta de Video** primero.")
    if st.button("🔄 Reintentar carga"):
        if "zones_loaded" in st.session_state:
            del st.session_state["zones_loaded"]
        st.rerun()
    st.stop()

image_original = st.session_state["_zones_cache"]["image"]
ancho_real, alto_real = st.session_state["_zones_cache"]["size"]

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
    "Tipo para la **siguiente** zona/trazo:",
    ("Brazo Abierto", "Brazo Cerrado", "Centro", "Muro / Pared"),
)

# El usuario puede alternar entre modo creación (dibujar rectángulos) y
# modo edición (seleccionar y transformar los rectángulos existentes).
modo_interaccion = st.sidebar.radio(
    "Operación:",
    ("Agregar zonas", "Editar/mover zonas"),
)

colores = {
    "Brazo Abierto": "rgba(244, 63, 94, 0.35)",  # fill color 
    "Brazo Cerrado": "rgba(59, 130, 246, 0.35)",
    "Centro": "rgba(234, 179, 8, 0.35)",
    "Muro / Pared": "rgba(6, 182, 212, 1.0)",     # Cyan sólido para la línea
}
color_actual = colores.get(tipo_zona_visual, "rgba(148, 163, 184, 0.35)")

drawing_mode_actual = "line" if tipo_zona_visual == "Muro / Pared" else "rect"

st.markdown(
    '<div class="tt-card">'
    '<div class="tt-section-title">🖊️ Dibujo de ROIs sobre el fotograma</div>'
    '<p>Haz clic y arrastra para dibujar rectángulos sobre el laberinto. '
    'Cuando termines puedes cambiar al modo <strong>Editar/mover zonas</strong> ' 
    'para seleccionar cualquier rectángulo y ajustar sus esquinas a tu ' 
    'elección.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# =============== 7.5 HERRAMIENTAS DE PLANTILLA =================
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Plantillas")

import zone_templates as template_manager

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
    st.session_state["lista_nombres_zonas"] = ["Centro", "Brazo Cerrado 1", "Brazo Cerrado 2", "Brazo Abierto 1", "Brazo Abierto 2"]
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
st.caption("*(Selecciona Muro / Pared para dibujar con líneas rectas presionando click y arrastrando. Para Regiones, usa rectángulos).*")
# elegir modo de dibujo según lo seleccionado en la barra lateral
if modo_interaccion == "Editar/mover zonas":
    canvas_drawing_mode = "transform"
else:
    canvas_drawing_mode = drawing_mode_actual
canvas_result = st_canvas(
    fill_color=color_actual if drawing_mode_actual == "rect" else "transparent",
    stroke_width=2 if drawing_mode_actual == "rect" else 4,
    stroke_color="#ffffff" if drawing_mode_actual == "rect" else color_actual,
    background_image=image_display,
    update_streamlit=True,
    height=ALTO_CANVAS,
    width=ANCHO_CANVAS,
    drawing_mode=canvas_drawing_mode,
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
            st.session_state["lista_nombres_zonas"].append(
                _next_default_zone_name(
                    tipo_zona_visual,
                    st.session_state["lista_nombres_zonas"],
                )
            )
    elif num_cajas < num_nombres:
        st.session_state["lista_nombres_zonas"] = st.session_state["lista_nombres_zonas"][:num_cajas]

    normalized_name_rows = _normalize_saved_zone_names(
        [
            {
                "type": canvas_result.json_data["objects"][idx].get("type", "rect"),
                "Nombre Zona": st.session_state["lista_nombres_zonas"][idx],
            }
            for idx in range(len(st.session_state["lista_nombres_zonas"]))
        ]
    )
    normalized_names = [zone["Nombre Zona"] for zone in normalized_name_rows]
    if normalized_names != st.session_state["lista_nombres_zonas"]:
        st.session_state["lista_nombres_zonas"] = normalized_names

    if not objects.empty:
        st.markdown('<div class="tt-card">', unsafe_allow_html=True)
        
        c_table, c_actions = st.columns([2, 1])
        
        with c_table:
            st.markdown('<div class="tt-section-title">📝 Zonas identificadas</div>', unsafe_allow_html=True)
            # Calcular Coordenadas Reales (Escaladas) para visualización
            datos_visuales = objects[["left", "top", "width", "height"]].copy()
            datos_visuales["Nombre Zona"] = st.session_state["lista_nombres_zonas"]

            # Añadir columnas de coordenadas reales (Solo lectura)
            # Manejamos caso híbrido de lineas/rectangulos
            if "x1" in datos_visuales.columns:
                datos_visuales["Real X"] = datos_visuales.apply(lambda r: (r["left"] if pd.isna(r.get("x1")) else r["x1"]) * factor_escala, axis=1).astype(int)
                datos_visuales["Real Y"] = datos_visuales.apply(lambda r: (r["top"] if pd.isna(r.get("y1")) else r["y1"]) * factor_escala, axis=1).astype(int)
            else:
                datos_visuales["Real X"] = (datos_visuales["left"] * factor_escala).astype(int)
                datos_visuales["Real Y"] = (datos_visuales["top"] * factor_escala).astype(int)
            
            datos_visuales["Real W"] = datos_visuales.get("width", 0).fillna(0).astype(float) * factor_escala
            datos_visuales["Real H"] = datos_visuales.get("height", 0).fillna(0).astype(float) * factor_escala

            df_editado = st.data_editor(
                datos_visuales,
                num_rows="fixed",
                column_config={
                    "left": st.column_config.NumberColumn("Canvas X", disabled=True),
                    "top": st.column_config.NumberColumn("Canvas Y", disabled=True),
                    "width": st.column_config.NumberColumn("Canvas W", disabled=True),
                    "height": st.column_config.NumberColumn("Canvas H", disabled=True),
                    "x1": None, "y1": None, "x2": None, "y2": None, # Hide line primitives
                    "Real X": st.column_config.NumberColumn("REAL X (Video)", disabled=True),
                    "Real Y": st.column_config.NumberColumn("REAL Y (Video)", disabled=True),
                    "Real W": None, "Real H": None,
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
            objects_full = canvas_result.json_data["objects"]
            
            for idx, reg in enumerate(df_editado.to_dict("records")):
                ori_type = objects_full[idx].get("type", "rect")
                
                if ori_type == "line":
                    # Las lineas se guardan con x1,y1 a x2,y2
                    x1 = objects_full[idx]["x1"] + objects_full[idx]["left"]
                    y1 = objects_full[idx]["y1"] + objects_full[idx]["top"]
                    x2 = objects_full[idx]["x2"] + objects_full[idx]["left"]
                    y2 = objects_full[idx]["y2"] + objects_full[idx]["top"]
                    
                    zona_real = {
                        "type": "line",
                        "Nombre Zona": reg["Nombre Zona"],
                        "x1": int(x1 * factor_escala),
                        "y1": int(y1 * factor_escala),
                        "x2": int(x2 * factor_escala),
                        "y2": int(y2 * factor_escala),
                    }
                else:
                    zona_real = {
                        "type": "rect",
                        "Nombre Zona": reg["Nombre Zona"],
                        "left": int(reg["left"] * factor_escala),
                        "top": int(reg["top"] * factor_escala),
                        "width": int(reg["width"] * factor_escala) if not pd.isna(reg["width"]) else 0,
                        "height": int(reg["height"] * factor_escala) if not pd.isna(reg["height"]) else 0,
                    }
                zonas_para_guardar.append(zona_real)

            zonas_para_guardar = _normalize_saved_zone_names(zonas_para_guardar)
            st.session_state["zonas_configuradas"] = zonas_para_guardar
            st.session_state["lista_nombres_zonas"] = [zona["Nombre Zona"] for zona in zonas_para_guardar]
            save_session()
            base_name = os.path.splitext(os.path.basename(st.session_state["ruta_video_actual"]))[0]
            video_name_simba = f"{base_name}_full"

            roi_sync_result = None
            roi_sync_error = None
            try:
                roi_sync_result = sync_streamlit_rois_to_simba(
                    project_folder=SIMBA_PROJECT_FOLDER,
                    video_name=video_name_simba,
                    zonas_list=zonas_para_guardar,
                    video_path=st.session_state["ruta_video_actual"],
                    include_model_aliases=True,
                )
                st.session_state["simba_roi_sync"] = roi_sync_result
            except Exception as error:
                roi_sync_error = error

            st.success("✅ Configuración guardada y reescalada a la resolución del video.")
            if roi_sync_result:
                st.info(
                    "SimBA sincronizado con "
                    f"{len(roi_sync_result['canonical_roi_names'])} ROIs canónicas de pared."
                )
                if roi_sync_result["canonical_roi_names"]:
                    st.caption(
                        "SimBA guarda sólo las paredes del modelo: "
                        + ", ".join(roi_sync_result["canonical_roi_names"])
                    )
                st.caption(
                    "Las zonas de brazos y centro se conservan en Streamlit para YOLO, "
                    "pero no se escriben como ROIs extra dentro de SimBA."
                )
            elif roi_sync_error:
                st.warning(
                    "La configuración se guardó en Streamlit, pero no se pudo escribir "
                    f"ROI_definitions.h5 en SimBA: {roi_sync_error}"
                )
            st.json(zonas_para_guardar)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.session_state["lista_nombres_zonas"] = []
