import os
import sys
import streamlit as st

# ================= SETUP =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session
from ui_theme import (
    use_theme,
    render_topbar,
    inject_sidebar_profile,
)

st.set_page_config(
    page_title="Manual de usuario",
    page_icon="assets/logos/logo_ria.png",
    layout="wide"
)

load_session()
colors = use_theme()

# ================= LOGIN =================
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

# ================= CONTENIDO =================

render_topbar("Prototipo técnico para análisis automatizado de comportamiento")


st.markdown("### Manual de usuario")

pdf_path = os.path.join("assets", "manual_usuario.pdf")

if not os.path.exists(pdf_path):
    st.error("No se encontró el archivo PDF.")
    st.stop()

with open(pdf_path, "rb") as pdf_file:
    pdf_bytes = pdf_file.read()

st.pdf(pdf_bytes)

st.download_button(
    label="Descargar manual",
    data=pdf_bytes,
    file_name="manual_usuario.pdf",
    mime="application/pdf"
)