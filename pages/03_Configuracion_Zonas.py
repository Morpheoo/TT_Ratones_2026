import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd
import os
import sys
from collections import defaultdict
from pathlib import Path

# ================= 0. SETUP & PERSISTENCE =================
st.set_page_config(page_title="Configuración de zonas", page_icon="assets/logos/logo_ria.png", layout="wide")

if os.path.join(os.getcwd(), "src") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))

from ui_components import load_resource_with_splash
from session_utils import load_session, save_session
import importlib
import ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar, inject_sidebar_profile, render_footer
from simba_roi_bridge import sync_streamlit_rois_to_simba
from sandbox_utils import get_active_simba_project_dir

load_session()
colors = use_theme()

if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

# ================= SIDEBAR =================
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
    
    # Sidebar con navegación
    inject_sidebar_profile(show_admin_button=True)

# ================= 2. VIDEO CHECK & LOGIC =================
if "ruta_video_actual" not in st.session_state:
    st.warning("No hay un video activo en sesión. Regresa a 'Ingesta de video'.")
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
        return "Brazo abierto"
    if "cerrado" in raw_name_lower:
        return "Brazo cerrado"
    if "centro" in raw_name_lower:
        return "Centro"
    if "pared" in raw_name_lower or "muro" in raw_name_lower or obj_type == "line":
        return "Muro / Pared"
    if fill == OPEN_FILL:
        return "Brazo abierto"
    if fill == CLOSED_FILL:
        return "Brazo cerrado"
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
                "Posición en x": _round_int(left),
                "Posición en y": _round_int(top),
                "Ancho": _round_int(width),
                "Alto": _round_int(height),
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
                    "Nombre de la zona": zone.get("Nombre Zona"),
                    "Tipo": zone.get("zone_type"),
                    "Geometría": "Línea",
                    "Coordenada en x del primer punto": zone.get("x1"),
                    "Coordenada en y del primer punto": zone.get("y1"),
                    "Coordenada en x del segundo punto": zone.get("x2"),
                    "Coordenada en y del segundo punto": zone.get("y2"),
                }
            )
        else:
            rows.append(
                {
                    "Nombre de la zona": zone.get("Nombre Zona"),
                    "Tipo": zone.get("zone_type"),
                    "Geometría": "Rectángulo",
                    "Posición en x": zone.get("Posición en x"),
                    "Posición en y": zone.get("Posición en y"),
                    "Ancho": zone.get("Ancho"),
                    "Alto": zone.get("Alto"),
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
            "message": "No se encontró un video activo o analizado para asociar las zonas de interés dentro de SimBA.",
        }

    video_stem = Path(simba_video_path).stem
    # Proyecto SimBA activo: productivo o sandbox segun el selector
    # de la página Keypoints (persistido en st.session_state).
    active_project_dir = get_active_simba_project_dir(
        Path("data/simba_projects").resolve()
    )
    roi_sync_result = sync_streamlit_rois_to_simba(
        project_folder=str(active_project_dir.resolve()),
        video_name=video_stem,
        zonas_list=wall_zones,
        video_path=simba_video_path,
        include_model_aliases=True,
        include_user_zones=False,
    )

    # verificación post-write: confirmar en disco que el archivo .h5 del proyecto
    # SimBA activo (productivo o sandbox) contiene las 6 paredes para
    # este video. Sin esto la UI podria reportar éxito aunque la
    # escritura cayera en otro path o fallara silenciosamente.
    roi_path = roi_sync_result.get("roi_path")
    persisted_count = -1
    persist_error = None
    if roi_path and Path(roi_path).exists():
        try:
            with pd.HDFStore(roi_path, mode="r") as store:
                df = store.get("/rectangles")
            persisted_count = int((df["Video"] == video_stem).sum())
        except Exception as error:
            persist_error = str(error)
    else:
        persist_error = f"No se encontró el archivo .h5 esperado: {roi_path}"

    if persisted_count == 6:
        return {
            "ok": True,
            "message": f"Se importaron correctamente las 6 zonas de interés de paredes a SimBA para `{video_stem}`.",
            "detail": roi_sync_result,
        }
    return {
        "ok": False,
        "message": (
            f"La sincronización reportó éxito pero el archivo .h5 del proyecto activo tiene "
            f"{persisted_count if persisted_count >= 0 else '?'} de 6 paredes para `{video_stem}`. "
            f"Ruta verificada: {roi_path}."
            + (f" Error de lectura: {persist_error}" if persist_error else "")
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
            "message": "No se encontró conexión a la base de datos para guardar las zonas históricas.",
        }

    video_path = st.session_state.get("ruta_video_actual")
    if not video_path:
        return {
            "ok": False,
            "message": "No hay vídeo activo para persistir las zonas en la base de datos.",
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
            f"Se guardaron {result['zones_saved']} zonas en la base de datos para el experimento #{result['experiment_id']}."
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
    yield 100, "Iniciando editor de zonas de interés."
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
    subtitle="Preparando editor de zonas...",
)
if not cache: st.stop()

# ================= 3. CABECERA =================
render_topbar()
st.markdown("### Módulo 03: Configuración de zonas")
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
    st.markdown("#### Herramientas de dibujo")
    tipo_zona = st.radio(
        "Clasificación de zonas de interés:",
        ["Brazo Abierto", "Brazo Cerrado", "Centro", "Muro / Pared"],
        format_func=lambda x: {
            "Brazo Abierto": "Brazo abierto",
            "Brazo Cerrado": "Brazo cerrado",
            "Centro": "Centro",
            "Muro / Pared": "Muro / pared"
        }.get(x, x)
    )
    operacion = st.radio("Modo de interacción:", ["Dibujar rectángulos", "Mover / editar"])
    
    st.divider()
    
    if st.button("Cargar plantilla (EPM)", use_container_width=True):
        st.info("Plantilla de laberinto cargada.")
    
    if st.button("Limpiar lienzo", type="secondary", use_container_width=True):
        st.session_state["canvas_key"] = f"canvas_{os.urandom(4).hex()}"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_main:
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Lienzo de configuración")
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
        st.markdown("#### Zonas Detectadas")
        st.caption("Las coordenadas mostradas abajo ya quedaron convertidas a la resolución real del video.")
        st.dataframe(_zones_dataframe(normalized_zones), use_container_width=True, hide_index=True)
        
        if st.button("Guardar configuración experimental", type="primary", use_container_width=True):
            st.session_state["zonas_configuradas"] = normalized_zones
            save_session()
            db_sync = _persist_zones_to_db(normalized_zones, factor_escala)
            with st.spinner("Sincronizando las 6 paredes a SimBA..."):
                roi_sync = _sync_wall_rois_to_simba(normalized_zones)

            if roi_sync["ok"]:
                st.balloons()
                st.success("Configuración de zonas guardada exitosamente en el prototipo.")
                if db_sync["ok"]:
                    st.success(f"{db_sync['message']}")
                else:
                    st.warning(db_sync["message"])
                st.success(f"{roi_sync['message']}")
                st.info("Solo las 6 paredes se exportaron a SimBA. Las demás zonas quedan disponibles para el módulo de resultado final.")
            else:
                st.warning("La configuración se guardó en la app, pero la sincronización con SimBA no quedó completa.")
                if db_sync["ok"]:
                    st.success(f"{db_sync['message']}")
                else:
                    st.warning(db_sync["message"])
                st.warning(roi_sync["message"])
        st.markdown('</div>', unsafe_allow_html=True)

render_footer()
