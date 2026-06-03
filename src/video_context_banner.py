"""
video_context_banner.py
─────────────────────────────────────────────────────────────────────────────
Componente reutilizable: Banner de contexto del video activo.

Muestra de forma prominente qué video se está procesando en cada módulo,
evitando la confusión entre videos del mismo escenario.

Uso:
    from src.video_context_banner import render_video_banner, render_video_banner_mini
    render_video_banner()        # Banner completo (para módulos de análisis)
    render_video_banner_mini()   # versión compacta (para cabeceras de página)
"""

import os
import streamlit as st

# CSS embebido del banner (inyectado una sola vez por sesión)
_BANNER_CSS = """
<style>
.vid-banner {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border: 1px solid rgba(99, 179, 237, 0.35);
    border-left: 4px solid #63b3ed;
    border-radius: 10px;
    padding: 0.9rem 1.3rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.vid-banner.warning {
    border-left-color: #F6AD55;
    background: linear-gradient(135deg, #1a1400 0%, #2d2000 100%);
}
.vid-banner-icon { font-size: 2rem; line-height: 1; flex-shrink: 0; }
.vid-banner-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #63b3ed;
    margin-bottom: 0.15rem;
}
.vid-banner.warning .vid-banner-label { color: #F6AD55; }
.vid-banner-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #EDF2F7;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    word-break: break-all;
}
.vid-banner-path {
    font-size: 0.72rem;
    color: rgba(237,242,247,0.5);
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    margin-top: 0.1rem;
}
.vid-banner-mini {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(99,179,237,0.12);
    border: 1px solid rgba(99,179,237,0.3);
    border-radius: 6px;
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    color: #63b3ed;
    font-weight: 600;
    margin-bottom: 0.7rem;
}
</style>
"""

def _inject_css():
    if "_vid_banner_css_injected" not in st.session_state:
        st.markdown(_BANNER_CSS, unsafe_allow_html=True)
        st.session_state["_vid_banner_css_injected"] = True


def render_video_banner(module_label: str = "Video en análisis") -> bool:
    """
    Renderiza el banner completo de contexto de video.
    
    Muestra:
      - Nombre del archivo (prominente, monospace)
      - Ruta completa (sutil)
    
    Devuelve True si hay video cargado, False si no.
    """
    _inject_css()
    ruta = st.session_state.get("ruta_video_actual", "")

    if ruta:
        nombre = os.path.basename(ruta)
        ruta_display = ruta if len(ruta) <= 80 else f"...{ruta[-77:]}"
        st.markdown(
            f"""
            <div class="vid-banner">
                <div class="vid-banner-icon">[VIDEO]</div>
                <div>
                    <div class="vid-banner-label">{module_label}</div>
                    <div class="vid-banner-name">{nombre}</div>
                    <div class="vid-banner-path">{ruta_display}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return True
    else:
        st.markdown(
            """
            <div class="vid-banner warning">
                <div class="vid-banner-icon">[WARN]</div>
                <div>
                    <div class="vid-banner-label">Sin video cargado</div>
                    <div class="vid-banner-name">Ningún video seleccionado</div>
                    <div class="vid-banner-path">Ve a 01 · Ingesta de Video para cargar un video</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return False


def render_video_banner_mini() -> bool:
    """
    versión compacta del indicador de video (badge inline).
    Útil para cabeceras donde el espacio es limitado.
    Devuelve True si hay video cargado.
    """
    _inject_css()
    ruta = st.session_state.get("ruta_video_actual", "")
    if ruta:
        nombre = os.path.basename(ruta)
        st.markdown(
            f'<div class="vid-banner-mini">{nombre}</div>',
            unsafe_allow_html=True,
        )
        return True
    return False
