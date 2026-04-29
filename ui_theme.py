import streamlit as st
import os
import base64
from session_utils import load_session

def get_image_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode()
    ext = path.split('.')[-1]
    mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"

def _sidebar_nav_css(colors: dict) -> str:
    """
    Genera CSS para mostrar/ocultar ítems del sidebar según el estado de sesión.
    
    Orden de páginas Streamlit (auto-detectadas por nombre de archivo):
     1. Home          (Home.py)
     2. Login         (00_Login.py)
     3. Ingesta       (01_*)
     4. Keypoints     (02_*)
     5. Zonas         (03_*)
     6. Análisis      (04_*)
     7. Resultados    (05_*)
     8. Perfil        (98_*)
     9. Admin         (99_*)
    """
    logged_in = st.session_state.get("logged_in", False)
    is_admin  = st.session_state.get("role", "") == "admin"

    if not logged_in:
        # No autenticado: ocultar TODOS excepto Login (ítem 2)
        return """
    /* === MODO NO AUTENTICADO: solo Login visible === */
    [data-testid="stSidebarNavItems"] li:nth-child(1),
    [data-testid="stSidebarNavItems"] li:nth-child(3),
    [data-testid="stSidebarNavItems"] li:nth-child(4),
    [data-testid="stSidebarNavItems"] li:nth-child(5),
    [data-testid="stSidebarNavItems"] li:nth-child(6),
    [data-testid="stSidebarNavItems"] li:nth-child(7),
    [data-testid="stSidebarNavItems"] li:nth-child(8),
    [data-testid="stSidebarNavItems"] li:nth-child(9) {
        display: none !important;
    }"""
    elif not is_admin:
        # Autenticado pero no admin: ocultar Login y Admin Panel
        return """
    /* === MODO AUTENTICADO (usuario normal) === */
    [data-testid="stSidebarNavItems"] li:nth-child(2),
    [data-testid="stSidebarNavItems"] li:nth-child(9) {
        display: none !important;
    }"""
    else:
        # Admin: ocultar solo Login
        return """
    /* === MODO ADMIN === */
    [data-testid="stSidebarNavItems"] li:nth-child(2) {
        display: none !important;
    }"""

def use_theme():
    """
    Sistema de Diseño Premium Institucional IPN-ESCOM.
    Basado en requerimientos visuales avanzados (Dashboard Científico).
    """
    colors = {
        "primary": "#6A1B3F",       # Guinda principal
        "primary_dark": "#4E1830",  # Guinda profundo
        "primary_light": "#963660", # Guinda claro (hovers)
        "bg_page": "#F6F4F5",       # Fondo general gris muy claro
        "bg_card": "#FFFFFF",       # Superficie blanca brillante
        "border": "#E8E1E5",        # Borde suave, casi invisible
        "text_main": "#1F1F1F",     # Texto oscuro principal (alta legibilidad)
        "text_sub": "#666666",      # Texto gris secundario
        "success": "#2E7D32",       # Verde para estados ok
        "warning": "#B7791F",       # Naranja/Dorado para advertencias
        "danger": "#D32F2F",        # Rojo suave para errores
        "accent_bg": "rgba(106, 27, 63, 0.05)",     # Fondo alternativo sutil
    }

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Variables Globales */
    :root {{
        --p: {colors['primary']};
        --pd: {colors['primary_dark']};
        --pl: {colors['primary_light']};
        --bg: {colors['bg_page']};
        --card: {colors['bg_card']};
        --border: {colors['border']};
        --text: {colors['text_main']};
        --text-sub: {colors['text_sub']};
        --success: {colors['success']};
        --warning: {colors['warning']};
        --danger: {colors['danger']};
    }}

    /* Global App Background */
    .stApp {{
        background-color: var(--bg) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* Eliminar espaciado superior nativo de Streamlit */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }}

    /* === SIDEBAR (Guinda IPN) — SIEMPRE VISIBLE === */
    section[data-testid="stSidebar"] {{
        background-color: {colors['primary']} !important;
        background-image: linear-gradient(180deg, {colors['primary_dark']} 0%, {colors['primary']} 100%) !important;
        border-right: none !important;
        box-shadow: 2px 0 15px rgba(0,0,0,0.1);
        width: 280px !important;
        min-width: 280px !important;
        /* Anular cualquier transform de colapso de Streamlit */
        transform: none !important;
        translate: none !important;
        visibility: visible !important;
        display: block !important;
        position: relative !important;
    }}
    
    /* Anular también el div contenedor interno que Streamlit usa para el colapso */
    section[data-testid="stSidebar"] > div:first-child {{
        width: 280px !important;
        transform: none !important;
    }}
    
    /* Ocultar botones nativos de colapso */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}

    /* === SIDEBAR MINI MODE (clase aplicada via JS) === */
    section[data-testid="stSidebar"].sidebar-mini {{
        width: 52px !important;
        min-width: 52px !important;
        overflow: hidden !important;
    }}
    section[data-testid="stSidebar"].sidebar-mini > div:first-child {{
        width: 52px !important;
    }}
    /* En modo mini: ocultar textos y el logo/branding */
    section[data-testid="stSidebar"].sidebar-mini [data-testid="stSidebarNav"] {{
        display: none !important;
    }}
    section[data-testid="stSidebar"].sidebar-mini .sidebar-brand {{
        display: none !important;
    }}
    /* Ajustar contenido principal cuando el sidebar está mini */
    section[data-testid="stSidebar"].sidebar-mini ~ .main {{
        margin-left: 52px !important;
    }}


    section[data-testid="stSidebar"] * {{
        color: rgba(255,255,255,0.9) !important;
    }}

    /* Nav items en Sidebar */
    [data-testid="stSidebarNav"] li div a {{
        border-radius: 8px !important;
        margin: 0.15rem 1rem !important;
        transition: all 0.2s ease;
        padding: 0.5rem 1rem !important;
    }}
    
    [data-testid="stSidebarNav"] li div a span {{
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }}

    [data-testid="stSidebarNav"] li div a:hover {{
        background-color: rgba(255,255,255,0.1) !important;
    }}

    [data-testid="stSidebarNav"] li div a[aria-current="page"] {{
        background-color: rgba(255,255,255,0.15) !important;
        border-left: 4px solid white !important;
        border-radius: 0 8px 8px 0 !important;
        margin-left: 0 !important;
        padding-left: 1.5rem !important;
    }}
    
    [data-testid="stSidebarNav"] li div a[aria-current="page"] span {{
        font-weight: 700 !important;
        color: white !important;
    }}

    /* Inyección de iconos SVG blancos para el sidebar */
    /* 1. Home */
    [data-testid="stSidebarNavItems"] li:nth-child(1) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 2. Login */
    [data-testid="stSidebarNavItems"] li:nth-child(2) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 3. Ingesta Video */
    [data-testid="stSidebarNavItems"] li:nth-child(3) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 4. Keypoints */
    [data-testid="stSidebarNavItems"] li:nth-child(4) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 5. Zonas */
    [data-testid="stSidebarNavItems"] li:nth-child(5) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 6. Analisis */
    [data-testid="stSidebarNavItems"] li:nth-child(6) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 7. Resultados */
    [data-testid="stSidebarNavItems"] li:nth-child(7) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 8. Perfil */
    [data-testid="stSidebarNavItems"] li:nth-child(8) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}
    /* 9. Admin */
    [data-testid="stSidebarNavItems"] li:nth-child(9) a span:first-child::before {{
        content: url('data:image/svg+xml;utf8,<svg viewBox="0 0 24 24" width="18" height="18" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>');
        display: inline-block; vertical-align: middle; margin-right: 12px; margin-bottom: 2px; opacity: 0.9;
    }}

    /* SVG icons en sidebar nav */
    [data-testid="stSidebarNav"] svg {{
        fill: white !important;
        opacity: 0.8;
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] svg {{
        opacity: 1;
    }}

    {_sidebar_nav_css(colors)}
    
    /* Ocultar elementos nativos molestos */
    #MainMenu, [data-testid="stToolbar"], footer {{ visibility: hidden !important; display: none !important; }}
    
    [data-testid="stSidebarNav"] {{
        padding-bottom: 20px !important; 
    }}
    /* Header: transparente */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        box-shadow: none !important;
        visibility: hidden !important;
    }}

    /* Botón para expandir sidebar cuando está colapsado — visible y guinda */
    [data-testid="collapsedControl"] {{
        display: flex !important;
        visibility: visible !important;
        background-color: {colors['primary']} !important;
        border-radius: 0 6px 6px 0 !important;
        width: 20px !important;
        padding: 8px 4px !important;
        box-shadow: 2px 0 8px rgba(0,0,0,0.2) !important;
        position: fixed !important;
        left: 0 !important;
        top: 50% !important;
        z-index: 99999 !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
    }}
    [data-testid="collapsedControl"] svg {{
        fill: white !important;
        stroke: white !important;
        width: 16px !important;
        height: 16px !important;
    }}

    /* === TIPOGRAFÍA === */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.01em !important;
    }}

    p, span, div {{
        color: var(--text);
    }}

    /* === BOTONES === */
    .stButton > button {{
        background-color: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }}
    
    .stButton > button:hover {{
        border-color: var(--p) !important;
        color: var(--p) !important;
        background-color: rgba(106, 27, 63, 0.03) !important;
    }}

    /* Primary Button (White Institutional style) */
    .stButton > button[kind="primary"],
    .stButton > button[data-baseweb="button"]:has(div:contains("primary")) {{
        background-color: #FFFFFF !important;
        color: {colors['primary']} !important;
        border: 2px solid {colors['primary']} !important;
        box-shadow: 0 4px 10px rgba(106, 27, 63, 0.1) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }}
    
    .stButton > button[kind="primary"] *,
    .stButton > button[data-baseweb="button"]:has(div:contains("primary")) * {{
        color: {colors['primary']} !important;
    }}
    
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-baseweb="button"]:has(div:contains("primary")):hover {{
        background-color: {colors['primary']} !important;
        color: white !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 15px rgba(106, 27, 63, 0.2) !important;
    }}

    .stButton > button[kind="primary"]:hover *,
    .stButton > button[data-baseweb="button"]:has(div:contains("primary")):hover * {{
        color: white !important;
    }}

    /* Tarjetas tipo Dashboard */
    .dash-card {{
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .dash-card:hover {{
        box-shadow: 0 6px 16px rgba(0,0,0,0.05);
        border-color: rgba(106, 27, 63, 0.2);
    }}
    .dash-card-header {{
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.5rem;
    }}
    .dash-card-icon {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--p);
    }}
    .dash-card-icon img {{
        max-width: 100%;
        max-height: 100%;
    }}
    /* Para iconos SVG embebidos */
    .dash-card-icon svg {{
        width: 20px;
        height: 20px;
        fill: var(--p);
    }}
    .dash-card-title {{
        font-weight: 700;
        font-size: 0.95rem;
        color: var(--text);
        margin: 0;
    }}
    .dash-card-body {{
        font-size: 0.85rem;
        color: var(--text-sub);
        line-height: 1.4;
        flex-grow: 1;
        margin-bottom: 1rem;
    }}
    
    /* Topbar superior Custom */
    .topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.8rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid var(--border);
    }}
    .topbar-left {{
        display: flex;
        align-items: center;
        gap: 1rem;
    }}
    .topbar-right {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
        font-size: 0.85rem;
        color: var(--text-sub);
        font-weight: 500;
    }}
    
    /* KPI Cards Row */
    .kpi-container {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }}
    .kpi-icon {{
        width: 40px; height: 40px;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2rem; color: var(--p);
    }}
    .kpi-icon svg {{ width: 22px; height: 22px; fill: var(--p); }}
    
    .kpi-info h4 {{ margin: 0; font-size: 0.95rem; font-weight: 700; color: var(--text); }}
    .kpi-info p {{ margin: 0; font-size: 0.75rem; color: var(--text-sub); margin-top: 2px; line-height: 1.2; }}
    .status-dot {{ display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; }}
    .status-ok {{ background-color: var(--success); }}
    .status-warn {{ background-color: var(--warning); }}

    /* Paneles de Columna Lateral */
    .side-panel {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }}
    .side-panel-title {{
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: var(--text);
    }}
    
    /* Enlaces Rápidos */
    .quick-link {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem;
        border-bottom: 1px solid var(--border);
        color: var(--text);
        font-weight: 500;
        font-size: 0.85rem;
        text-decoration: none;
        transition: background 0.2s;
        border-radius: 6px;
    }}
    .quick-link:last-child {{ border-bottom: none; }}
    .quick-link:hover {{ background: {colors['accent_bg']}; color: var(--p); }}
    
    /* Toggle switch nativo ajuste */
    .stCheckbox > label {{
        font-weight: 600 !important;
        color: var(--text) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
    # JS: borrar estado colapsado del sidebar en localStorage y forzar apertura
    st.markdown("""
<script>
(function() {
    function tryExpand() {
        var sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return false;
        var rect = sidebar.getBoundingClientRect();
        if (rect.width < 100) {
            var selectors = ['[data-testid="collapsedControl"]', '[data-testid="collapsedControl"] button', 'button[kind="header"]'];
            for (var i = 0; i < selectors.length; i++) {
                var btn = window.parent.document.querySelector(selectors[i]);
                if (btn) { btn.click(); return true; }
            }
        }
        return rect.width > 100;
    }
    var attempts = 0;
    function keepTrying() {
        attempts++;
        if (!tryExpand() && attempts < 10) {
            setTimeout(keepTrying, 300);
        }
    }
    setTimeout(keepTrying, 200);
})();
</script>
""", unsafe_allow_html=True)
    
    return colors

def render_topbar(title="Sistema Técnico para Análisis Automatizado de Comportamiento"):
    """Renderiza la barra superior limpia (Topbar) con logos institucionales reales"""
    colors = use_theme()
    
    user_name_raw = st.session_state.get("user_name", "Usuario")
    # Format name, remove numbers and capitalize. If specific user, format nicely.
    user_name = user_name_raw
    if "@" in user_name_raw:
        name_part = user_name_raw.split("@")[0]
        import re
        name_part = re.sub(r'\\d+', '', name_part)
        if name_part.lower() == "hportocarrero":
            user_name = "Habid Portocarrero"
        else:
            user_name = name_part.capitalize()
    
    role = st.session_state.get("role", "Investigador").capitalize()
    
    import datetime
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    now = datetime.datetime.now()
    date_str = f"{now.day} de {meses[now.month-1]}, {now.year}"
    
    logo_ipn_path = os.path.join("assets", "logos", "logo-ipn-guinda.png")
    logo_escom_path = os.path.join("assets", "logos", "logo-escom.png")
    
    ipn_b64 = get_image_base64(logo_ipn_path)
    escom_b64 = get_image_base64(logo_escom_path)
    
    logos_html = ""
    # El logo del IPN debe ser visiblemente equivalente o muy levemente mayor debido a jerarquía
    if ipn_b64 and escom_b64:
        logos_html = (
            f'<img src="{ipn_b64}" style="height: 100px; margin-right: 12px; opacity: 0.95;">'
            f'<div style="width: 1px; height: 50px; background: {colors["border"]}; margin: 0 10px;"></div>'
            f'<img src="{escom_b64}" style="height: 65px; margin-left: 12px; opacity: 0.95;" title="ESCOM">'
        )
    else:
        logos_html = f'<span style="background: {colors["primary"]}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">ESCOM</span> IPN'
    
    st.markdown(f"""
<div class="topbar" style="align-items: center; justify-content: space-between;">
    <div class="topbar-left" style="align-items: center; flex: 1;">
        {logos_html}
        <div style="width: 1px; height: 35px; background: {colors['border']}; margin: 0 20px;"></div>
        <div style="color: {colors['text_main']}; font-size: 1.25rem; font-weight: 700;">{title}</div>
    </div>
    <div class="topbar-right" style="align-items: center; gap: 2rem;">
        <div style="text-align: right;">
            <div style="color: {colors['text_main']}; font-weight: 700; line-height: 1.1;">{user_name}</div>
            <div style="color: {colors['text_sub']}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">{role}</div>
        </div>
        <div style="width: 1px; height: 30px; background: {colors['border']};"></div>
        <div style="color: {colors['text_sub']}; font-weight: 500; font-size: 0.85rem;">{date_str}</div>
    </div>
</div>
""", unsafe_allow_html=True)

def inject_sidebar_profile(show_admin_button=False):
    """Inyecta el layout HTML para la cabecera y branding en el sidebar."""
    colors = use_theme()
    # --- 1. CABECERA (TÍTULO) ---
    st.sidebar.markdown('<div style="text-align:center; font-weight:800; color:white; letter-spacing:1px; padding-top:0.2rem;">SISTEMA EPM</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<hr style="margin: 0.5rem 0; opacity:0.15;">', unsafe_allow_html=True)

    # --- 2. NAVEGACIÓN MANUAL (con o sin Admin Panel) ---
    inject_sidebar_navigation(show_admin_button=show_admin_button)
    
    # --- 3. BRANDING INSTITUCIONAL (Debajo de navegación) ---
    st.sidebar.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
    
    # Centrado usando columnas nativas
    c1, c2, c3 = st.sidebar.columns([1.4, 2, 1])
    logo_ria_path = os.path.join("assets", "logos", "logo_ria_desktop.png")
    with c2:
        if os.path.exists(logo_ria_path):
            st.image(logo_ria_path, width=80)
            
    st.sidebar.markdown(f"""
        <div style="text-align:center; opacity:0.5; font-size:0.65rem; color:white; text-transform:uppercase; margin-top: 5px; margin-bottom: 2.2rem;">
            Versión v3.1 – 2026<br>IPN - ESCOM
        </div>
    """, unsafe_allow_html=True)

    # --- 4. CIERRE (ESPACIO FINAL) ---
    st.sidebar.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)


def inject_sidebar_navigation(show_admin_button=False):
    """Inyecta navegación manual del sidebar (opcionalmente con Admin Panel)."""
    # Botón de Admin Panel (solo si show_admin_button=True y user es admin)
    if show_admin_button:
        user_role = st.session_state.get("role", "")
        if user_role == "admin":
            st.sidebar.markdown("#### Panel Administrativo")
            if st.sidebar.button("Acceder a Panel Admin", key="admin_access_btn", use_container_width=True, type="primary"):
                st.switch_page("pages/99_Admin_Panel.py")
            st.sidebar.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Navegación de módulos
    st.sidebar.markdown("#### Módulos del Sistema")
    
    pages = [
        ("Home", "Home.py"),
        ("Ingesta de Video", "pages/01_Ingesta_de_Video.py"),
        ("Keypoints", "pages/02_Keypoints.py"),
        ("Configuracion Zonas", "pages/03_Configuracion_Zonas.py"),
        ("Analisis Final", "pages/04_Analisis_Final.py"),
        ("Resultados y Estadisticas", "pages/05_Resultados_y_Estadisticas.py"),
        ("Comparacion", "pages/06_Comparacion.py"),
        ("Perfil", "pages/98_Perfil.py"),
    ]
    
    for label, page_path in pages:
        if st.sidebar.button(label, key=f"nav_{page_path}", use_container_width=True):
            st.switch_page(page_path)
    
    st.sidebar.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
