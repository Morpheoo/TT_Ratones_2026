# ui_theme.py
import streamlit as st

def _get_theme_name() -> str:
    # Retiramos el selector de tema y forzamos el oscuro
    st.session_state["theme_name"] = "Oscuro"
    return "Oscuro"


def use_theme():
    """
    Aplica el CSS global (ahora fijo en Tema Oscuro Institucional)
    y devuelve el diccionario de colores por si lo quieres usar.
    """
    theme_name = _get_theme_name()

    # -- PALETA OFICIAL IPN OBLIGATORIA --
    # Guinda principal: #6A1B2E
    # Guinda profundo: #4A1020
    # Guinda medio: #7A2238
    # Guinda acento: #8F314A
    # Guinda suave: #F4E9ED
    # Blancos: #FFFFFF, #FAF8F9
    # Grises: #E5E7EB, #9CA3AF, #374151
    # Carbón: #1F2937, #111827

    # Tema Oscuro Bloqueado
    colors = {
        "page_bg": "#201318",           # Guinda muy oscuro/carbón base
        "sidebar_bg": "#14090c",        # Sidebar casi negro-guinda
        "sidebar_text": "#E5E7EB",      # Gris claro legible
        "banner_bg": "#4A1020",         # Guinda Profundo
        "banner_text": "#FAF8F9",       # Blanco Suave
        "card_bg": "#311A22",           # Superficie Guinda-Carbón
        "card_border": "#4A1020",       # Borde sutil guinda
        "primary": "#8F314A",           # Guinda acento (más vibrante para contraste oscuro)
        "primary_hover": "#6A1B2E",     # Guinda principal
        "input_bg": "#1F2937",
        "input_border": "#4A1020",
        "text_main": "#FAF8F9",
        "text_sub": "#9CA3AF",
        "accent": "#C9A227",
        "shadow": "rgba(0,0,0,0.6)",
        "sidebar_hover": "rgba(122, 34, 56, 0.4)", # Guinda translúcido
        "sidebar_active": "#7A2238"      # Fondo select item
    }


    css = f"""
    <style>
    /* Variables Globales IPN */
    :root {{
      --page-bg: {colors['page_bg']};
      --banner-bg: {colors['banner_bg']};
      --banner-text: {colors['banner_text']};
      --card-bg: {colors['card_bg']};
      --card-border: {colors['card_border']};
      --primary: {colors['primary']};
      --primary-hover: {colors['primary_hover']};
      --input-bg: {colors['input_bg']};
      --input-border: {colors['input_border']};
      --text-main: {colors['text_main']};
      --text-sub: {colors['text_sub']};
      --accent: {colors['accent']};
      --shadow: {colors['shadow']};
      --sidebar-bg: {colors['sidebar_bg']};
      --sidebar-text: {colors['sidebar_text']};
      --sidebar-hover: {colors['sidebar_hover']};
      --sidebar-active: {colors['sidebar_active']};
    }}

    /* Fondo Principal de Streamlit */
    .stApp {{
      background-color: var(--page-bg) !important;
    }}

    .main {{
      background-color: var(--page-bg) !important;
    }}

    /* --- SIDEBAR REFORZADO IPN (APLICA EN AMBOS TEMAS) --- */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid rgba(143, 49, 74, 0.4) !important;
    }}

    /* Textos genéricos en sidebar siempre claros */
    section[data-testid="stSidebar"] * {{
        color: var(--sidebar-text) !important;
    }}

    /* Navegación - Iconos y Labels */
    [data-testid="stSidebarNav"] span {{
        color: var(--sidebar-text) !important;
    }}

    /* Elemento activo en navegación lateral */
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background-color: var(--sidebar-active) !important;
        border-radius: 6px !important;
        margin-bottom: 2px !important;
    }}
    
    [data-testid="stSidebarNav"] a[aria-current="page"] span {{
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }}

    /* Hover en navegación */
    [data-testid="stSidebarNav"] a:hover {{
        background-color: var(--sidebar-hover) !important;
        border-radius: 6px !important;
    }}

    /* Checkbox / Toggle en sidebar */
    section[data-testid="stSidebar"] .stCheckbox p,
    section[data-testid="stSidebar"] .stRadio p,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {{
         color: var(--sidebar-text) !important;
         font-weight: 600;
         opacity: 1 !important;
    }}

    /* Círculo indicador del Radio Button activo en el selector del sidebar */
    section[data-testid="stSidebar"] div[role="radiogroup"] div[data-testid="stMarkdownContainer"] p {{
         color: var(--sidebar-text) !important;
    }}
    
    /* Indicador del radio cuando está prendido se pinta de Guinda vibrante */
    section[data-testid="stSidebar"] [data-baseweb="radio"] div:first-child {{
        background-color: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.4) !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"] div:first-child {{
        background-color: var(--sidebar-text) !important;
        border-color: var(--sidebar-text) !important;
    }}

    /* Botón Especial de Cerrar Sesión en Sidebar */
    section[data-testid="stSidebar"] .stButton > button {{
        background-color: #6A1B2E !important; /* Rojo IPN fuerte siempre para acción salir */
        color: #FFFFFF !important;
        border: 1px solid #8F314A !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background-color: #7A2238 !important;
        border: 1px solid #FFFFFF !important;
        transform: scale(1.02);
    }}
    
    /* Contenedor principal */
    .block-container {{
      padding-top: 4rem; /* Restaurado a 4rem nativo para evitar solapamiento con header top */
      padding-bottom: 2.5rem;
    }}

    /* Tipografía Global (Inter / Sans Serif limpios) */
    html, body {{
      font-family: 'Inter', 'Segoe UI', sans-serif;
    }}

    /* Asegurarnos que texto principal (fuera del sidebar) obedezca */
    .main p, .main span, .main div {{
      color: var(--text-main);
    }}

    /* Banda superior del título institucional */
    .ipn-banner {{
      background-color: var(--banner-bg);
      color: var(--banner-text);
      padding: 1.5rem 1rem;
      text-align: center;
      font-weight: 700;
      letter-spacing: 0.05em;
      font-size: 1.1rem;
      margin-bottom: 2rem;
      border-radius: 0.5rem;
      box-shadow: 0 4px 6px var(--shadow);
      border-bottom: 3px solid var(--accent);
    }}
    
    .ipn-banner-subtitle {{
      display: block;
      font-size: 0.85rem;
      font-weight: 400;
      margin-top: 0.5rem;
      color: var(--banner-text);
      opacity: 0.85;
    }}

    /* Tarjeta institucional (login, formularios, modulos) */
    .ipn-card {{
      background-color: var(--card-bg);
      border-radius: 0.5rem;
      padding: 2rem;
      border: 1px solid var(--card-border);
      border-top: 4px solid var(--primary); /* Acento institucional extra */
      box-shadow: 0 4px 15px var(--shadow);
      margin-bottom: 1.5rem;
    }}

    .ipn-card-title {{
      text-align: center;
      font-weight: 700;
      color: var(--primary); /* Prioridad visual al guinda */
      margin-bottom: 1.5rem;
      font-size: 1.5rem;
    }}

    /* Botones principales Streamlit en área principal */
    .main .stButton > button {{
      background-color: var(--primary) !important;
      color: #FFFFFF !important;
      border-radius: 0.35rem !important;
      border: 1px solid var(--primary) !important;
      padding: 0.5rem 1.5rem !important;
      font-weight: 600 !important;
      transition: all 0.2s ease;
    }}
    .main .stButton > button:hover {{
      background-color: var(--primary-hover) !important;
      border-color: var(--primary-hover) !important;
      transform: translateY(-1px);
    }}

    /* Inputs de texto Streamlit */
    .stTextInput > div > div > input {{
      background-color: var(--input-bg) !important;
      color: var(--text-main) !important;
      border-radius: 0.35rem !important;
      border: 1px solid var(--input-border) !important;
    }}
    
    .stTextInput > div > div > input:focus {{
      border-color: var(--primary) !important;
      box-shadow: 0 0 0 1px var(--primary) !important;
    }}
    
    .stNumberInput > div > div > input {{
      background-color: var(--input-bg) !important;
      color: var(--text-main) !important;
      border-radius: 0.35rem !important;
      border: 1px solid var(--input-border) !important;
    }}

    /* Etiquetas de input */
    .main .st-af, .main .st-ag {{
      color: var(--text-main) !important;
      font-weight: 500;
      opacity: 0.9;
    }}

    /* DataFrames y Tablas */
    [data-testid="stDataFrame"] {{
      border: 1px solid var(--primary); /* Guinda border */
      border-radius: 0.5rem;
      overflow: hidden;
    }}
    
    /* Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 0.35rem 0.35rem 0 0;
        padding: 10px 20px;
        color: var(--text-main);
        transition: all 0.1s;
    }}

    /* Tab Activo = Mas presencia IPN */
    .stTabs [aria-selected="true"] {{
        background-color: var(--primary-hover) !important;
        color: #FFFFFF !important;
        border-color: var(--primary-hover) !important;
        border-bottom: 3px solid var(--accent) !important;
    }}

    /* Métricas Generales fuera de Sidebar (Acentos guinda) */
    .main div[data-testid="stMetricValue"], .main div[data-testid="stMetricLabel"] {{
        color: var(--text-main) !important;
    }}

    /* Badges o Toast Streamlit - Fuerza Guinda */
    [data-testid="stToast"] {{
         border-left: 4px solid var(--primary) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return colors


def render_header():
    """
    Muestra la banda superior con el título e identidad IPN.
    """
    st.markdown(
        """
        <div class="ipn-banner">
            <div>PROTOTIPO TÉCNICO DE ANÁLISIS AUTOMATIZADO DE COMPORTAMIENTO</div>
            <span class="ipn-banner-subtitle">INSTITUTO POLITÉCNICO NACIONAL | ESCOM</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

