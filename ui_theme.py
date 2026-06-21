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
     6. análisis      (04_*)
     7. Resultados    (05_*)
     8. Perfil        (98_*)
     9. Admin         (99_*)
    """
    logged_in = st.session_state.get("logged_in", False)
    is_admin  = st.session_state.get("role", "") == "admin"

    # Selectores basados en href (no dependen del orden de las paginas).
    # Streamlit deriva el href del filename sin prefijo numerico ni .py:
    #   pages/00_Login.py        -> /Login
    #   pages/99_Admin_Panel.py  -> /Admin_Panel
    if not logged_in:
        # No autenticado: ocultar TODO el sidebar nav excepto Login.
        return """
    /* === MODO NO AUTENTICADO: solo Login visible === */
    [data-testid="stSidebarNavItems"] li:not(:has(a[href$="/Login"])) {
        display: none !important;
    }"""
    elif not is_admin:
        # Autenticado pero no admin: ocultar Login y Admin Panel.
        return """
    /* === MODO AUTENTICADO (usuario normal) === */
    [data-testid="stSidebarNavItems"] li:has(a[href$="/Login"]),
    [data-testid="stSidebarNavItems"] li:has(a[href$="/Admin_Panel"]) {
        display: none !important;
    }"""
    else:
        # Admin: ocultar solo Login.
        return """
    /* === MODO ADMIN === */
    [data-testid="stSidebarNavItems"] li:has(a[href$="/Login"]) {
        display: none !important;
    }"""

def use_theme():
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
    /* 6. análisis */
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

def render_topbar(title="Prototipo para análisis automatizado y visualización de comportamiento de especímenes en modelos de ansiedad"):
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
    
    role_raw = st.session_state.get("role", "investigador").lower()
    role_map = {
        "admin": "Administrador",
        "investigador": "Investigador",
        "estudiante": "Estudiante"
    }
    role = role_map.get(role_raw, role_raw.capitalize())
    
    import datetime
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    now = datetime.datetime.now()
    date_str = f"{now.day} de {meses[now.month-1]} de {now.year}"
    
    logo_ipn_path = os.path.join("assets", "logos", "logo-ipn-guinda.png")
    logo_escom_path = os.path.join("assets", "logos", "logo-escom.png")
    
    ipn_b64 = get_image_base64(logo_ipn_path)
    escom_b64 = get_image_base64(logo_escom_path)
    
    logos_html = ""
    # El logo del IPN debe ser visiblemente equivalente o muy levemente mayor debido a jerarquía
    if ipn_b64 and escom_b64:
        logos_html = (
            f'<img src="{ipn_b64}" style="height: 100px; margin-right: 12px; opacity: 0.95;">'
            f'<img src="{escom_b64}" style="height: 58px; margin-left: 12px; opacity: 0.95;" title="ESCOM">'
        )
    else:
        logos_html = f'<span style="background: {colors["primary"]}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">ESCOM</span> IPN'
    
    st.markdown(f"""
<div class="topbar" style="align-items: center; justify-content: space-between;">
    <div class="topbar-left" style="align-items: center; flex: 1;">
        {logos_html}
        <div style="width: 1px; height: 35px; background: {colors['border']}; margin: 0 20px;"></div>
        <div style="color: {colors['text_main']}; font-size: 1.25rem; font-weight: 700;">{title}</div>
        <div style="width: 1px; height: 50px; background: {colors['border']}; margin: 0 10px;"></div>
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
    
    # Aviso legal y Términos debajo del header
    col_legal1, col_legal2 = st.columns(2)
    
    with col_legal1:
        with st.expander("Aviso Legal", expanded=False):
            st.markdown("""
### AVISO LEGAL

#### 1. Datos identificativos

La presente plataforma constituye un prototipo tecnológico desarrollado en el marco de actividades académicas y de investigación realizadas en la Escuela Superior de Cómputo en conjunto con la Escuela Nacional de Medicina y Homeopatía del Instituto Politécnico Nacional.

Este prototipo es propiedad del Instituto Politécnico Nacional con domicilio en Av. Luis Enrique Erro s/n, Unidad Profesional Adolfo López Mateos, Zacatenco, Alcaldía Gustavo A. Madero, C.P. 07738, Ciudad de México.

Para cualquier consulta relacionada con el funcionamiento de la plataforma, los usuarios podrán contactar a los responsables del proyecto a través de los medios institucionales correspondientes.

- glazarov1500@alumno.ipn.mx
- emuzquizp1800@alumno.ipn.mx
- hportocarreror1700@alumno.ipn.mx

#### 2. Condiciones de uso

El acceso y utilización de esta plataforma implica la aceptación plena de las disposiciones contenidas en el presente Aviso Legal.

La plataforma tiene fines exclusivamente científicos, académicos y de investigación. Los resultados generados por los modelos de inteligencia artificial tienen carácter auxiliar y no sustituyen el criterio, análisis o validación de los investigadores responsables.

Los responsables del proyecto se reservan el derecho de modificar, actualizar o suspender parcial o totalmente el contenido y funcionamiento de la plataforma sin previo aviso.

#### 3. Propiedad intelectual

El código fuente, modelos de inteligencia artificial, bases de datos, documentación técnica, interfaces gráficas, diseños, logotipos y demás elementos que integran la plataforma se encuentran protegidos por la Ley Federal del Derecho de Autor y demás disposiciones aplicables en materia de propiedad intelectual.

Queda prohibida la reproducción, distribución, modificación, comercialización o utilización no autorizada de dichos contenidos sin el consentimiento expreso de los titulares de los derechos correspondientes.

Asimismo, la plataforma incorpora componentes de software de código abierto utilizados conforme a los términos establecidos en sus respectivas licencias.

#### 4. Responsabilidad

Los responsables del proyecto no garantizan la ausencia de errores en los resultados generados por el sistema ni asumen responsabilidad por las decisiones, interpretaciones o acciones realizadas por terceros con base en dichos resultados.

El uso de la información proporcionada por la plataforma es responsabilidad exclusiva del usuario.

#### 5. Protección de datos

La plataforma no recopila ni procesa datos personales sensibles de personas físicas durante su operación ordinaria.

En caso de que se recabe información de contacto o datos administrativos relacionados con investigadores, colaboradores o usuarios, estos serán tratados conforme a lo dispuesto por la Ley Federal de Protección de Datos Personales en Posesión de los Particulares y demás normativa aplicable.

#### 6. Uso de animales de laboratorio

Los datos procesados por la plataforma provienen de investigaciones realizadas conforme a la normativa aplicable al uso y cuidado de animales de laboratorio, incluyendo la Norma Oficial Mexicana NOM-062-ZOO-1999 y los lineamientos éticos e institucionales correspondientes.

La plataforma no interviene directamente en procedimientos experimentales sobre animales, limitándose al procesamiento y análisis de registros previamente obtenidos.

#### 7. Legislación aplicable

El presente Aviso Legal se rige por las leyes vigentes de los Estados Unidos Mexicanos. Cualquier controversia derivada de la interpretación o aplicación de este documento será resuelta conforme a la legislación mexicana aplicable.
            """)
    
    with col_legal2:
        with st.expander("Términos y Condiciones", expanded=False):
            st.markdown("""
### TÉRMINOS Y CONDICIONES DE USO

#### 1. Objeto
Los presentes Términos y Condiciones regulan el acceso y uso de la plataforma de análisis conductual asistido por inteligencia artificial desarrollada como proyecto académico en la Escuela Superior de Cómputo (ESCOM) del Instituto Politécnico Nacional (IPN).

El acceso y utilización de la plataforma implican la aceptación plena de las disposiciones aquí establecidas.

#### 2. Finalidad de la plataforma
La plataforma tiene como objetivo apoyar actividades de investigación científica, docencia y desarrollo tecnológico relacionadas con el análisis automatizado del comportamiento animal mediante técnicas de inteligencia artificial y visión por computadora.

La información generada por la plataforma tiene fines exclusivamente académicos, científicos y educativos.

#### 3. Usuarios
Podrán utilizar la plataforma investigadores, docentes, estudiantes y demás personas autorizadas por los responsables del proyecto.

Los usuarios se comprometen a utilizar la plataforma de manera lícita, ética y conforme a la legislación mexicana aplicable.

#### 4. Uso permitido
El usuario podrá:

- Acceder a las funcionalidades disponibles de la plataforma.
- Cargar y procesar datos experimentales relacionados con proyectos de investigación.
- Consultar resultados, métricas y análisis generados por el sistema.

El usuario deberá garantizar que cuenta con las autorizaciones necesarias para el uso de los datos que incorpore a la plataforma.

#### 5. Restricciones de uso
Queda prohibido:

- Utilizar la plataforma para fines ilícitos o contrarios a la normatividad aplicable.
- Intentar acceder sin autorización a sistemas, bases de datos o servicios asociados.
- Modificar, descompilar, realizar ingeniería inversa o interferir con el funcionamiento de la plataforma, salvo en los casos permitidos por la legislación aplicable.
- Utilizar los resultados generados como único criterio para la toma de decisiones que requieran validación científica o profesional adicional.

#### 6. Propiedad intelectual
El software, documentación, modelos de inteligencia artificial, diseños, bases de datos y demás elementos que integran la plataforma están protegidos por la Ley Federal del Derecho de Autor, la Ley Federal de Protección a la Propiedad Industrial y demás disposiciones aplicables.

Los derechos patrimoniales correspondientes pertenecen a sus autores y titulares respectivos.

Las herramientas de software libre empleadas conservan las licencias originales otorgadas por sus desarrolladores.

#### 7. Uso de datos
La plataforma está diseñada para procesar información experimental relacionada con estudios de comportamiento animal.

Los usuarios son responsables de asegurar que los datos incorporados al sistema cumplan con la legislación aplicable, así como con las normas institucionales y éticas correspondientes.

Cuando proceda, el tratamiento de información se realizará conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares y demás disposiciones aplicables.

#### 8. Investigación con animales
El uso de la plataforma en proyectos experimentales deberá observar la normativa vigente aplicable al bienestar animal, incluyendo la Norma Oficial Mexicana NOM-062-ZOO-1999 y las disposiciones institucionales correspondientes.

La responsabilidad sobre el cumplimiento de dichas normas recae en los investigadores y responsables de cada proyecto.

#### 9. Exclusión de garantías
La plataforma se proporciona "tal como está" para fines académicos y de investigación.

Los responsables del proyecto no garantizan la ausencia total de errores, interrupciones o imprecisiones en los resultados generados por los modelos de inteligencia artificial.

Los resultados obtenidos deberán ser interpretados y validados por personal competente.

#### 10. Limitación de responsabilidad
El Instituto Politécnico Nacional, la Escuela Superior de Cómputo y los desarrolladores del proyecto no serán responsables por daños directos o indirectos derivados del uso, interpretación o aplicación de los resultados proporcionados por la plataforma.

#### 11. Modificaciones
Los responsables del proyecto podrán actualizar los presentes Términos y Condiciones en cualquier momento para adecuarlos a cambios normativos, tecnológicos o institucionales.

Las modificaciones entrarán en vigor desde su publicación en el sitio web.

#### 12. Legislación aplicable y jurisdicción
Los presentes Términos y Condiciones se regirán por las leyes vigentes de los Estados Unidos Mexicanos.

Cualquier controversia relacionada con la interpretación o aplicación de estos términos será resuelta conforme a la legislación mexicana aplicable y ante las autoridades competentes de la Ciudad de México.
            """)

    # Acceso al manual de usuario dentro del sistema
    st.markdown(
    f"""
    <div style="
        text-align: center;
        margin-top: 1rem;
        padding: 0.75rem;
        background: {colors['bg_card']};
        border-radius: 8px;
        border: 1px solid {colors['border']};
        >
    </div>
    """,
    unsafe_allow_html=True
)

    if st.button(
        "¿Necesitas ayuda? ¡Consulta el manual de usuario!",
        key="manual_usuario_btn",
        use_container_width=True
    ):
        st.switch_page("pages/97_Manual_Usuario.py")


def inject_sidebar_profile(show_admin_button=False):
    """Inyecta el layout HTML para la cabecera y branding en el sidebar."""
    colors = use_theme()
    # --- 1. CABECERA (TÍTULO) ---
    st.sidebar.markdown('<div style="text-align:center; font-weight:800; color:white; letter-spacing:1px; padding-top:0.2rem;">PROTOTIPO</div>', unsafe_allow_html=True)
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
    """, unsafe_allow_html=True)

    # --- 4. CIERRE (ESPACIO FINAL) ---
    st.sidebar.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)


def inject_sidebar_navigation(show_admin_button=False):
    # Botón de Admin Panel (solo si show_admin_button=True y user es admin)
    if show_admin_button:
        user_role = st.session_state.get("role", "")
        if user_role == "admin":
            st.sidebar.markdown("#### Panel administrativo")
            if st.sidebar.button("Acceder al panel de administración", key="admin_access_btn", use_container_width=True, type="primary"):
                st.switch_page("pages/99_Admin_Panel.py")
            st.sidebar.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Navegación de módulos
    st.sidebar.markdown("#### Módulos del prototipo")
    
    pages = [
        ("Inicio", "Home.py"),
        ("Manual de usuario", "pages/97_Manual_Usuario.py"),
        ("Ingesta de vídeo", "pages/01_Ingesta_de_Video.py"),
        ("Keypoints", "pages/02_Keypoints.py"),
        ("Configuración de zonas", "pages/03_Configuracion_Zonas.py"),
        ("Análisis final", "pages/04_Analisis_Final.py"),
        ("Resultados y estadísticas", "pages/05_Resultados_y_Estadisticas.py"),
        ("Comparación", "pages/06_Comparacion.py"),
        ("Perfil", "pages/98_Perfil.py"),
    ]
    
    for label, page_path in pages:
        if st.sidebar.button(label, key=f"nav_{page_path}", use_container_width=True):
            st.switch_page(page_path)
    
    st.sidebar.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
