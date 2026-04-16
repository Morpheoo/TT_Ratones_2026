import streamlit as st
import os
import sys
import pandas as pd
from sqlalchemy import text

# ================= 0. SETUP & PERSISTENCE =================
st.set_page_config(page_title="Admin Panel | IPN", layout="wide", page_icon="assets/logos/logo_ria.png")

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from src.session_utils import load_session, save_session
from src.auth import check_admin_access
from src.db.connection import get_db_engine
from src.ui_components import run_page_splash
import importlib
import ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme, render_topbar

load_session()
colors = use_theme()

# ================= 1. VERIFICAR LOGIN ==================
if not st.session_state.get("logged_in"):
    st.switch_page("pages/00_Login.py")

role = st.session_state.get("role", "")
if not check_admin_access(role):
    st.error("ACCESO RESTRINGIDO. Se requiere privilegio de Administrador Institucional.")
    st.stop()

run_page_splash(
    "page_admin",
    [
        "Verificando privilegios administrativos...",
        "Sincronizando directorio de usuarios...",
        "Preparando consola institucional...",
    ],
    subtitle="TT 2026 - Cargando panel administrativo...",
)

# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Módulo 99: Panel de Administración")
st.markdown("""
    Gestión de identidades, privilegios y auditoría de experimentos del sistema institucional. 
    Este tablero es exclusivo para personal de administración central.
""")

st.divider()

engine = get_db_engine()

import datetime as _dt

def safe_df(df):
    """Convierte columnas con fechas a string para evitar errores de Arrow en Streamlit."""
    df = df.copy()
    for col in df.columns:
        if hasattr(df[col].dtype, 'name') and any(k in df[col].dtype.name for k in ('date', 'time')):
            df[col] = df[col].astype(str)
            continue
        if df[col].dtype == object:
            sample = df[col].dropna()
            if len(sample) > 0 and isinstance(sample.iloc[0], (_dt.date, _dt.datetime)):
                df[col] = df[col].astype(str)
    return df

# ================= 3. USER MANAGEMENT =================
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("#### Directorio de Usuarios")

# Data fetch
with engine.connect() as conn:
    df_users = safe_df(pd.read_sql(text("SELECT id, username, role, is_verified, is_active FROM users"), conn))

c1, c2, c3 = st.columns(3)
with c1: st.metric("Cuentas Totales", len(df_users))
with c2: st.metric("Sujetos Verificados", len(df_users[df_users['is_verified'] == True]))
with c3: st.metric("Investigadores", len(df_users[df_users['role'] == 'investigador']))

st.dataframe(df_users, use_container_width=True, hide_index=True)

# User Actions
st.markdown("---")
cols = st.columns(2)
with cols[0]:
    st.markdown("##### ✏️ Editar Privilegios")
    u_sel = st.selectbox("Seleccionar Usuario", df_users['username'])
    new_r = st.selectbox("Nuevo Rol", ["estudiante", "investigador", "admin"])
    if st.button("Actualizar Rol", use_container_width=True):
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET role = :r WHERE username = :u"), {"r": new_r, "u": u_sel})
            conn.commit()
            st.success(f"Rol de {u_sel} actualizado exitosamente.")
            st.rerun()

with cols[1]:
    st.markdown("##### ⛔ Gestión de Estado")
    u_mod = st.selectbox("Usuario a modificar", df_users['username'], key="u_mod")
    current_s = df_users[df_users['username'] == u_mod]['is_active'].values[0]
    btn_label = "SUSPENDER CUENTA" if current_s else "REACTIVAR CUENTA"
    if st.button(btn_label, type="primary" if current_s else "secondary", use_container_width=True):
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET is_active = :s WHERE username = :u"), {"s": not current_s, "u": u_mod})
            conn.commit()
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ================= 4. EXPERIMENT AUDIT =================
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("#### 🧪 Auditoría de Experimentos")
with engine.connect() as conn:
    df_exp = safe_df(pd.read_sql(
        text("SELECT id, rat_id, treatment, responsible, processed FROM experiments ORDER BY id DESC LIMIT 50"),
        conn
    ))

if df_exp.empty:
    st.info("No hay experimentos registrados en la plataforma.")
else:
    st.dataframe(df_exp, use_container_width=True, hide_index=True)
    if st.button("LIMPIAR REGISTROS HUERFANOS", type="secondary"):
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM experiments WHERE processed = FALSE"))
            conn.commit()
            st.success("Limpieza completada.")
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; color: {colors['text_sub']}; font-size: 0.8rem;">
        Administración Central de Plataforma &bull; IPN &bull; ESCOM &bull; 2026
    </div>
""", unsafe_allow_html=True)
