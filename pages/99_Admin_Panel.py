import streamlit as st
import os
import sys
import pandas as pd
from sqlalchemy import bindparam, text

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
from ui_theme import use_theme, render_topbar, inject_sidebar_profile

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
    if st.button("Cerrar Sesión", key="logout_btn", use_container_width=True):
        from session_utils import clear_session
        clear_session()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Sidebar con navegación
    inject_sidebar_profile(show_admin_button=True)

# ================= 2. CABECERA =================
render_topbar()
st.markdown("### Panel de Administración")
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


def delete_admin_experiments(engine, experiment_ids):
    experiment_ids = sorted(
        {int(exp_id) for exp_id in experiment_ids if str(exp_id).isdigit() and int(exp_id) > 0}
    )
    if not experiment_ids:
        return 0

    delete_query = text("DELETE FROM experiments WHERE id IN :experiment_ids").bindparams(
        bindparam("experiment_ids", expanding=True)
    )
    with engine.connect() as conn:
        result = conn.execute(delete_query, {"experiment_ids": experiment_ids})
        conn.commit()
    return int(result.rowcount or 0)

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
    st.markdown("##### Editar Privilegios")
    u_sel = st.selectbox("Seleccionar Usuario", df_users['username'])
    new_r = st.selectbox("Nuevo Rol", ["estudiante", "investigador", "admin"])
    if st.button("Actualizar Rol", use_container_width=True):
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET role = :r WHERE username = :u"), {"r": new_r, "u": u_sel})
            conn.commit()
            st.success(f"Rol de {u_sel} actualizado exitosamente.")
            st.rerun()

with cols[1]:
    st.markdown("##### Gestión de Estado")
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
st.markdown("#### Auditoría de Experimentos")
st.markdown("#### Auditoria de Experimentos")
admin_delete_notice = st.session_state.pop("admin_delete_notice", None)
if admin_delete_notice:
    st.success(admin_delete_notice)

with engine.connect() as conn:
    df_exp = safe_df(pd.read_sql(
        text(
            """
            SELECT
                e.id,
                e.rat_id,
                e.treatment,
                e.experiment_date,
                e.responsible,
                e.processed,
                COALESCE(ar.status, CASE WHEN e.processed THEN 'completed' ELSE 'pending' END) AS status
            FROM experiments e
            LEFT JOIN (
                SELECT DISTINCT ON (experiment_id)
                    experiment_id,
                    status,
                    timestamp,
                    id
                FROM analysis_results
                ORDER BY experiment_id, timestamp DESC, id DESC
            ) ar
                ON ar.experiment_id = e.id
            ORDER BY e.id DESC
            LIMIT 200
            """
        ),
        conn
    ))

if df_exp.empty:
    st.info("No hay experimentos registrados en la plataforma.")
else:
    selected_admin_ids = {
        int(exp_id)
        for exp_id in st.session_state.get("admin_selected_experiment_ids", [])
        if str(exp_id).isdigit()
    }
    visible_admin_ids = {int(exp_id) for exp_id in df_exp["id"].tolist()}
    selected_admin_ids = selected_admin_ids.intersection(visible_admin_ids)

    admin_selection_df = df_exp.copy()
    admin_selection_df.insert(0, "Seleccionar", admin_selection_df["id"].astype(int).isin(selected_admin_ids))
    edited_admin_selection = st.data_editor(
        admin_selection_df,
        use_container_width=True,
        hide_index=True,
        disabled=[column for column in admin_selection_df.columns if column != "Seleccionar"],
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn(
                "Sel.",
                help="Marca experimentos para borrarlos como administrador.",
                default=False,
                width="small",
            )
        },
        key="admin_experiment_selection_editor",
    )
    selected_admin_ids = edited_admin_selection.loc[
        edited_admin_selection["Seleccionar"],
        "id",
    ].astype(int).tolist()
    st.session_state["admin_selected_experiment_ids"] = selected_admin_ids

    delete_cols = st.columns([1.4, 1])
    with delete_cols[0]:
        admin_delete_confirm = st.checkbox(
            "Confirmo que deseo borrar permanentemente los experimentos seleccionados.",
            key="admin_delete_confirm",
        )
    with delete_cols[1]:
        if st.button(
            "BORRAR SELECCIONADOS",
            type="secondary",
            use_container_width=True,
            disabled=not selected_admin_ids or not admin_delete_confirm,
            key="btn_admin_delete_experiments",
        ):
            deleted_count = delete_admin_experiments(engine, selected_admin_ids)
            st.session_state["admin_selected_experiment_ids"] = []
            st.session_state["admin_delete_notice"] = f"Se borraron {deleted_count} experimento(s)."
            st.rerun()

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
