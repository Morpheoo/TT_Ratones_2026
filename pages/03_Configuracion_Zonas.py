import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd
import os
import sys
from collections import defaultdict
from pathlib import Path

# ================= 0. SETUP & PERSISTENCE =================
st.set_page_config(page_title="Configuración de Zonas | IPN", page_icon="assets/logos/logo_ria.png", layout="wide")

if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

from ui_components import load_resource_with_splash
from session_utils import load_session, save_session
import importlib
import ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar
from simba_roi_bridge import sync_streamlit_rois_to_simba
from config import SIMBA_PROJECT_DIR

load_session()
colors = use_theme()

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.warning("Debes iniciar sesión antes de usar el sistema.")
    st.stop()

# ================= 2. VIDEO CHECK & LOGIC =================
if "ruta_video_actual" not in st.session_state:
    st.warning("⚠️ No hay un video activo en sesión. Regresa a 'Ingesta de Video'.")
    st.stop()

OPEN_FILL = "rgba(111,29,70,0.4)"
CLOSED_FILL = "rgba(99,101,105,0.4)"
CENTER_FILL = "rgba(33,37,41,0.4)"
WALL_STROKE = "rgba(255,140,0,1)"


def _normalize_color(value):
    return str(value or "").replace(" ", "").lower()


def _infer_zone_kind(canvas_obj):
    raw_name = str(
        canvas_obj.get("id")
        or canvas_obj.get("name")
        or canvas_obj.get("Nombre Zona")
        or ""
    ).strip()
    raw_name_lower = raw_name.lower()
    obj_type = str(canvas_obj.get("type", "rect")).lower()
    fill = _normalize_color(canvas_obj.get("fill"))
    stroke = _normalize_color(canvas_obj.get("stroke"))

    if "abierto" in raw_name_lower:
        return "Brazo Abierto"
    if "cerrado" in raw_name_lower:
        return "Brazo Cerrado"
    if "centro" in raw_name_lower:
        return "Centro"
    if "pared" in raw_name_lower or "muro" in raw_name_lower or obj_type == "line":
        return "Muro / Pared"
    if fill == OPEN_FILL:
        return "Brazo Abierto"
    if fill == CLOSED_FILL:
        return "Brazo Cerrado"
    if fill == CENTER_FILL:
        return "Centro"
    if stroke == WALL_STROKE:
        return "Muro / Pared"
    return "Zona"


def _make_zone_name(zone_kind, counters):
    counters[zone_kind] += 1
    index = counters[zone_kind]
    if zone_kind == "Muro / Pared":
        return f"Pared {index}"
    if zone_kind == "Centro":
        return "Centro" if index == 1 else f"Centro {index}"
    if zone_kind == "Zona":
        return f"Zona {index}"
    return f"{zone_kind} {index}"


def _round_int(value):
    return int(round(float(value or 0)))


def _build_named_zones(canvas_objects, scale_factor):
    counters = defaultdict(int)
    normalized_zones = []

    for canvas_obj in canvas_objects:
        obj_type = str(canvas_obj.get("type", "rect")).lower()
        zone_kind = _infer_zone_kind(canvas_obj)
        zone_name = _make_zone_name(zone_kind, counters)
        scale_x = float(canvas_obj.get("scaleX", 1) or 1)
        scale_y = float(canvas_obj.get("scaleY", 1) or 1)

        if obj_type == "line":
            left = float(canvas_obj.get("left", 0) or 0)
            top = float(canvas_obj.get("top", 0) or 0)
            x1 = (left + float(canvas_obj.get("x1", 0) or 0) * scale_x) * scale_factor
            y1 = (top + float(canvas_obj.get("y1", 0) or 0) * scale_y) * scale_factor
            x2 = (left + float(canvas_obj.get("x2", 0) or 0) * scale_x) * scale_factor
            y2 = (top + float(canvas_obj.get("y2", 0) or 0) * scale_y) * scale_factor
            normalized_zones.append(
                {
                    "type": "line",
                    "zone_type": zone_kind,
                    "id": zone_name,
                    "name": zone_name,
                    "Nombre Zona": zone_name,
                    "x1": _round_int(x1),
                    "y1": _round_int(y1),
                    "x2": _round_int(x2),
                    "y2": _round_int(y2),
                }
            )
            continue

        left = float(canvas_obj.get("left", 0) or 0) * scale_factor
        top = float(canvas_obj.get("top", 0) or 0) * scale_factor
        width = float(canvas_obj.get("width", 0) or 0) * scale_x * scale_factor
        height = float(canvas_obj.get("height", 0) or 0) * scale_y * scale_factor
        normalized_zones.append(
            {
                "type": "rect",
                "zone_type": zone_kind,
                "id": zone_name,
                "name": zone_name,
                "Nombre Zona": zone_name,
                "left": _round_int(left),
                "top": _round_int(top),
                "width": _round_int(width),
                "height": _round_int(height),
                "x": _round_int(left),
                "y": _round_int(top),
                "w": _round_int(width),
                "h": _round_int(height),
            }
        )

    return normalized_zones


def _zones_dataframe(zones):
    rows = []
    for zone in zones:
        if zone.get("type") == "line":
            rows.append(
                {
                    "Nombre Zona": zone.get("Nombre Zona"),
                    "Tipo": zone.get("zone_type"),
                    "Geometria": "Linea",
                    "x1": zone.get("x1"),
                    "y1": zone.get("y1"),
                    "x2": zone.get("x2"),
                    "y2": zone.get("y2"),
                }
            )
        else:
            rows.append(
                {
                    "Nombre Zona": zone.get("Nombre Zona"),
                    "Tipo": zone.get("zone_type"),
                    "Geometria": "Rectangulo",
                    "left": zone.get("left"),
                    "top": zone.get("top"),
                    "width": zone.get("width"),
                    "height": zone.get("height"),
                }
            )
    return pd.DataFrame(rows)


def _resolve_simba_video_path():
    for candidate in [
        st.session_state.get("ultimo_video_analizado"),
        st.session_state.get("ruta_video_actual"),
    ]:
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)
    return None


def _sync_wall_rois_to_simba(zones):
    wall_zones = [zone for zone in zones if str(zone.get("zone_type", "")).strip().lower() == "muro / pared"]
    simba_video_path = _resolve_simba_video_path()

    if len(wall_zones) != 6:
        return {
            "ok": False,
            "message": f"Se detectaron {len(wall_zones)} paredes. SimBA necesita exactamente 6 para sincronizar.",
        }
    if not simba_video_path:
        return {
            "ok": False,
            "message": "No se encontro un video activo/analizado para asociar las ROIs dentro de SimBA.",
        }

    roi_sync_result = sync_streamlit_rois_to_simba(
        project_folder=str(Path(SIMBA_PROJECT_DIR).resolve()),
        video_name=Path(simba_video_path).stem,
        zonas_list=wall_zones,
        video_path=simba_video_path,
        include_model_aliases=True,
        include_user_zones=False,
    )
    imported_count = len(roi_sync_result.get("canonical_roi_names", []))
    return {
        "ok": imported_count == 6,
        "message": (
            f"Se importaron correctamente las 6 ROIs de paredes a SimBA para `{Path(simba_video_path).stem}`."
            if imported_count == 6
            else f"SimBA recibio {imported_count}/6 paredes para `{Path(simba_video_path).stem}`."
        ),
        "detail": roi_sync_result,
    }


def _persist_zones_to_db(zones, scale_factor):
    try:
        from db.connection import get_db_engine
        from db.experiment_history import persist_zones_for_video
    except Exception as error:
        return {
            "ok": False,
            "message": f"No se pudo cargar la capa de historial de experimentos: {error}",
        }

    engine = get_db_engine()
    if not engine:
        return {
            "ok": False,
            "message": "No se encontro conexion a PostgreSQL para guardar las zonas historicas.",
        }

    video_path = st.session_state.get("ruta_video_actual")
    if not video_path:
        return {
            "ok": False,
            "message": "No hay video activo para persistir las zonas en la BD.",
        }

    rat_id = st.session_state.get("id_raton_actual") or Path(video_path).stem
    treatment = st.session_state.get("treatment") or "Control"
    responsible = st.session_state.get("ingesta_responsable_actual") or st.session_state.get("user_name", "Investigador")

    result = persist_zones_for_video(
        engine,
        video_path=video_path,
        zonas=zones,
        rat_id=rat_id,
        treatment=treatment,
        responsible=responsible,
        username=st.session_state.get("user"),
        scale_factor=scale_factor,
    )
    return {
        "ok": True,
        "message": (
            f"Se guardaron {result['zones_saved']} zonas en la BD para el experimento #{result['experiment_id']}."
        ),
        "detail": result,
    }

def zones_loading_sequence():
    yield 30, "Extrayendo fotograma de referencia..."
    from moviepy.editor import VideoFileClip
    clip = VideoFileClip(st.session_state["ruta_video_actual"])
    frame = clip.get_frame(st.session_state.get("inicio_recorte", 0))
    img = Image.fromarray(frame)
    size = clip.size
    clip.close()
    yield 100, "Iniciando editor ROI."
    return {"image": img, "size": size}

zones_signature = (
    st.session_state.get("ruta_video_actual"),
    st.session_state.get("inicio_recorte", 0),
)
cache = load_resource_with_splash(
    page_id="page_zones",
    state_key="_zones_cache",
    generator_factory=zones_loading_sequence,
    dependency_signature=zones_signature,
    subtitle="TT 2026 - Preparando editor ROI...",
)
if not cache: st.stop()

# ================= 3. CABECERA =================
render_topbar()
st.markdown("### Módulo 03: Configuración de Zonas (ROI)")
st.markdown("""
    Defina los límites anatómicos del laberinto sobre el video experimental. 
    Las coordenadas se escalarán automáticamente a la resolución original del video.
""")
st.caption("Aquí defines las 6 paredes que después se sincronizan a SimBA. Las demás zonas de interés se conservan para el módulo de resultado final.")

st.divider()

image_original = cache["image"]
ancho_real, alto_real = cache["size"]
ANCHO_CANVAS = 800
factor_escala = ancho_real / ANCHO_CANVAS
ALTO_CANVAS = int(alto_real / factor_escala)
image_display = image_original.resize((ANCHO_CANVAS, ALTO_CANVAS))

# ================= 4. EDITOR ROI =================
col_sidebar, col_main = st.columns([1, 1.8])

with col_sidebar:
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### 🖊️ Herramientas de Dibujo")
    tipo_zona = st.radio("Clasificación de ROI:", ["Brazo Abierto", "Brazo Cerrado", "Centro", "Muro / Pared"])
    operacion = st.radio("Modo de Interacción:", ["Dibujar rectángulos", "Mover / Editar"])
    
    st.divider()
    
    if st.button("🧩 CARGAR PLANTILLA (EPM)", use_container_width=True):
        st.info("Plantilla de laberinto cargada.")
    
    if st.button("🗑️ LIMPIAR LIENZO", type="secondary", use_container_width=True):
        st.session_state["canvas_key"] = f"canvas_{os.urandom(4).hex()}"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_main:
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### 📐 Lienzo de Configuración")
    st.caption("*(Dibuja rectángulos de interés sobre el fotograma del video).*")
    
    drawing_mode = "transform" if "Mover" in operacion else ("line" if "Muro" in tipo_zona else "rect")
    color_map = {
        "Brazo Abierto": "rgba(111, 29, 70, 0.4)",  # IPN Guinda
        "Brazo Cerrado": "rgba(99, 101, 105, 0.4)", # IPN Gray
        "Centro": "rgba(33, 37, 41, 0.4)",
        "Muro / Pared": "rgba(255, 140, 0, 1)"
    }
    
    canvas_result = st_canvas(
        fill_color=color_map.get(tipo_zona, "rgba(0,0,0,0.3)"),
        stroke_width=2,
        stroke_color="#FFFFFF" if "Muro" not in tipo_zona else color_map["Muro / Pared"],
        background_image=image_display,
        height=ALTO_CANVAS,
        width=ANCHO_CANVAS,
        drawing_mode=drawing_mode,
        key=st.session_state.get("canvas_key", "canvas_main_ipn"),
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ================= 5. RESULTADOS DE DIBUJO =================
if canvas_result.json_data:
    objects = canvas_result.json_data.get("objects", [])
    if objects:
        normalized_zones = _build_named_zones(objects, factor_escala)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### 📋 Zonas Detectadas")
        st.caption("Las coordenadas mostradas abajo ya quedaron convertidas a la resolucion real del video.")
        st.dataframe(_zones_dataframe(normalized_zones), use_container_width=True, hide_index=True)
        
        if st.button("💾 GUARDAR CONFIGURACIÓN EXPERIMENTAL", type="primary", use_container_width=True):
            st.session_state["zonas_configuradas"] = normalized_zones
            save_session()
            db_sync = _persist_zones_to_db(normalized_zones, factor_escala)
            with st.spinner("Sincronizando las 6 paredes a SimBA..."):
                roi_sync = _sync_wall_rois_to_simba(normalized_zones)

            if roi_sync["ok"]:
                st.balloons()
                st.success("✅ Configuración de zonas guardada exitosamente en el sistema.")
                if db_sync["ok"]:
                    st.success(f"✅ {db_sync['message']}")
                else:
                    st.warning(db_sync["message"])
                st.success(f"✅ {roi_sync['message']}")
                st.info("Solo las 6 paredes se exportaron a SimBA. Las demás zonas quedan disponibles para el módulo de resultado final.")
            else:
                st.warning("La configuración se guardó en la app, pero la sincronización con SimBA no quedó completa.")
                if db_sync["ok"]:
                    st.success(f"✅ {db_sync['message']}")
                else:
                    st.warning(db_sync["message"])
                st.warning(roi_sync["message"])
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; color: {colors['text_sub']}; font-size: 0.8rem;">
        IPN - Escuela Superior de Cómputo 2026
    </div>
""", unsafe_allow_html=True)
