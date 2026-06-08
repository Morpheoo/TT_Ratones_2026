import streamlit as st
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "src"))
from session_utils import load_session, save_session
from ui_components import run_page_splash

st.set_page_config(
    page_title="Perfil",
    page_icon="assets/logos/logo_ria.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "init_done" not in st.session_state:
    load_session()
    st.session_state.init_done = True

import importlib, ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar, inject_sidebar_profile

colors = use_theme()

if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

run_page_splash(
    "page_profile",
    [
        "Recuperando perfil del investigador...",
        "Cargando preferencias personales...",
        "Preparando panel de seguridad...",
    ],
    subtitle="Cargando perfil...",
)

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

render_topbar("Configuración del perfil")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_display_name(raw: str) -> str:
    import re
    if "@" in raw:
        name_part = raw.split("@")[0]
        name_part = re.sub(r'\d+', '', name_part)
        # Mapeo de nombres conocidos
        known = {"hportocarrero": "Habid Portocarrero"}
        return known.get(name_part.lower(), name_part.replace("_", " ").title())
    return raw.title()

user_raw   = st.session_state.get("user", "usuario@ejemplo.com")  # El correo real (columna username en DB)
role       = st.session_state.get("role", "investigador").capitalize()
# Identidad: se quiere llamar (display) vs correo real
display    = st.session_state.get("preferred_name") or st.session_state.get("user_name") or get_display_name(user_raw)
initials   = "".join(w[0].upper() for w in display.split()[:2])

# ─── Layout ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 2rem;">
    <h1 style="font-size:1.9rem; margin:0; color:{colors['text_main']}; letter-spacing:-0.02em;">Perfil del investigador</h1>
    <p style="color:{colors['text_sub']}; font-size:0.9rem; margin-top:0.4rem;">
        Gestiona tus datos, preferencias y seguridad de acceso.
    </p>
</div>
""", unsafe_allow_html=True)

col_card, col_form = st.columns([1, 2.5], gap="large")

# ─── Tarjeta Avatar ───────────────────────────────────────────────────────────
with col_card:
    st.markdown(f"""
<div style="background:{colors['bg_card']}; border:1px solid {colors['border']}; border-radius:12px;
            padding:2rem 1.5rem; text-align:center; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
    <div style="width:80px; height:80px; border-radius:50%; background:{colors['primary']};
                color:white; font-size:2rem; font-weight:700; display:flex; align-items:center;
                justify-content:center; margin:0 auto 1rem auto; letter-spacing:1px;">
        {initials}
    </div>
    <div style="font-size:1.1rem; font-weight:700; color:{colors['text_main']};">{display}</div>
    <div style="font-size:0.78rem; color:{colors['text_sub']}; margin-top:4px;">{user_raw}</div>
    <div style="margin-top:0.8rem;">
        <span style="background:{colors['accent_bg']}; color:{colors['primary']}; font-size:0.7rem;
                     font-weight:600; padding:3px 10px; border-radius:20px; text-transform:uppercase;
                     letter-spacing:0.5px;">{role}</span>
    </div>
    <div style="margin-top:1.5rem; border-top:1px solid {colors['border']}; padding-top:1rem;
                font-size:0.75rem; color:{colors['text_sub']}; line-height:1.8;">
        <div>Prototipo EPM v3.1 – 2026</div>
        <div>IPN / ESCOM</div>
        <div>TT 2026-A155</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Formulario ───────────────────────────────────────────────────────────────
with col_form:
    tab_info, tab_pwd = st.tabs(["Información general", "Cambiar contraseña"])

    # TAB 1: Info
    with tab_info:
        st.markdown(f"""
<div style="background:{colors['bg_card']}; border:1px solid {colors['border']}; border-radius:12px;
            padding:1.8rem; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom:1rem;">
    <h3 style="margin:0 0 1.2rem 0; font-size:1rem; font-weight:700; color:{colors['text_main']};">
        Datos del investigador
    </h3>
""", unsafe_allow_html=True)

        preferred_name = st.text_input(
            "Nombre de usuario",
            value=display,
            placeholder="Ej. Morpheoo",
            help="Este es tu nombre público en el prototipo. Puedes cambiarlo."
        )
        st.text_input("Correo institucional", value=user_raw, disabled=True,
                      help="El correo no puede modificarse desde aquí.")
        st.text_input("Rol en el prototipo", value=role, disabled=True,
                      help="El rol es asignado por el administrador.")

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Guardar preferencias", type="primary", key="btn_save_info"):
            if preferred_name:
                import auth
                import importlib
                importlib.reload(auth)
                success, msg = auth.update_user_profile(user_raw, preferred_name.strip())
                if success:
                    st.session_state["user_name"] = preferred_name.strip()
                    st.session_state["preferred_name"] = preferred_name.strip()
                    save_session()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("El nombre no puede estar vacío.")

    # TAB 2: Password
    with tab_pwd:
        st.markdown(f"""
<div style="background:{colors['bg_card']}; border:1px solid {colors['border']}; border-radius:12px;
            padding:1.8rem; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom:1rem;">
    <h3 style="margin:0 0 1.2rem 0; font-size:1rem; font-weight:700; color:{colors['text_main']};">
        Cambiar contraseña
    </h3>
""", unsafe_allow_html=True)

        pwd_actual    = st.text_input("Contraseña actual", type="password", key="pwd_actual")
        pwd_nueva     = st.text_input("Nueva contraseña", type="password", key="pwd_nueva",
                                      help="Mínimo 8 caracteres.")
        pwd_confirmar = st.text_input("Confirmar nueva contraseña", type="password", key="pwd_confirm")

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Actualizar contraseña", type="primary", key="btn_change_pwd"):
            if not pwd_actual or not pwd_nueva or not pwd_confirmar:
                st.error("Completa todos los campos.")
            elif pwd_nueva != pwd_confirmar:
                st.error("Las contraseñas nuevas no coinciden.")
            elif len(pwd_nueva) < 8:
                st.warning("La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    from auth import check_password, hash_password
                    from db.connection import get_db_engine
                    from sqlalchemy import text as sqltxt

                    engine = get_db_engine()
                    with engine.connect() as conn:
                        row = conn.execute(
                            sqltxt("SELECT password_hash FROM users WHERE username = :u"),
                            {"u": user_raw}
                        ).fetchone()

                        if not row or not check_password(pwd_actual, row[0]):
                            st.error("La contraseña actual no es correcta.")
                        else:
                            new_hash = hash_password(pwd_nueva)
                            conn.execute(
                                sqltxt("UPDATE users SET password_hash = :h WHERE username = :u"),
                                {"h": new_hash, "u": user_raw}
                            )
                            conn.commit()
                            st.success("Contraseña actualizada correctamente.")
                except Exception as e:
                    st.error(f"Error al actualizar la contraseña: {e}")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align: center; color: {colors['text_sub']}; font-size: 0.8rem;">
        Prototipo para análisis automatizado y visualización de comportamiento de especímenes en modelos de ansiedad &copy; 2026<br>
    </div>
    """,
    unsafe_allow_html=True,
)
