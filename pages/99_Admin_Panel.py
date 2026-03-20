import streamlit as st
import os
import sys
import pandas as pd
from sqlalchemy import text

# REGLA #1: set_page_config SIEMPRE primero
st.set_page_config(page_title="Panel Admin - TT 2026", layout="wide", page_icon="🛡️")

# Add project root to path
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from src.session_utils import load_session, save_session
from src.auth import check_admin_access
from src.db.connection import get_db_engine
from src.access_control import require_admin
from src.sidebar_control import apply_sidebar_visibility

# Cargar sesión para tener el rol actualizado
load_session()

# Aplicar control de sidebar
apply_sidebar_visibility()

# ================= SEGURIDAD: SOLO ADMINS =================
require_admin()  # Solo administradores

st.markdown("# 🛡️ Panel de Administración")
st.markdown("### Gestión de Usuarios y Auditoría")

engine = get_db_engine()

# ================= FUNCIONES CRUD =================
def get_all_users():
    with engine.connect() as conn:
        query = text("SELECT id, username, role, is_verified, created_at, verification_code, is_active FROM users ORDER BY id ASC")
        result = conn.execute(query).fetchall()
        return pd.DataFrame(result)

def delete_user_by_id(user_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        conn.commit()

def update_user_role(user_id, new_role):
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = :r WHERE id = :id"), {"r": new_role, "id": user_id})
        conn.commit()

# ================= ESTADÍSTICAS RÁPIDAS =================
df_users = get_all_users()

c1, c2, c3 = st.columns(3)
c1.metric("Total Usuarios", len(df_users))
c2.metric("Verificados", len(df_users[df_users['is_verified'] == True]))
c3.metric("Estudiantes", len(df_users[df_users['role'].str.lower() == 'estudiante']))

st.divider()

def toggle_user_status(user_id, current_status):
    new_status = not current_status
    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET is_active = :s WHERE id = :id"), {"s": new_status, "id": user_id})
        conn.commit()

# ================= TABLA DE USUARIOS =================
st.subheader("📋 Listado de Usuarios")

# Dataframe con status
df_users['Estado'] = df_users['is_active'].apply(lambda x: "✅ Activo" if x else "⛔ Suspendido")

# Mostramos tabla interactiva
st.dataframe(
    df_users,
    column_config={
        "id": "ID",
        "username": "Correo Electrónico",
        "role": "Rol Actual",
        "Estado": "Estado",
        "is_verified": st.column_config.CheckboxColumn("Verificado"),
        "created_at": st.column_config.DatetimeColumn("Fecha Registro")
    },
    use_container_width=True,
    hide_index=True
)

st.divider()

# ================= ACCIONES (CRUD) =================
c_edit, c_suspend = st.columns([1, 1])

with c_edit:
    st.markdown("### ✏️ Editar Rol")
    user_to_edit = st.selectbox("Seleccionar Usuario", df_users['username'], key="sel_edit")
    new_role_val = st.selectbox("Nuevo Rol", ["estudiante", "investigador", "admin"], key="sel_role_new")
    
    if st.button("Actualizar Rol"):
        uid = int(df_users[df_users['username'] == user_to_edit]['id'].values[0])
        update_user_role(uid, new_role_val)
        st.success(f"Rol de {user_to_edit} actualizado a {new_role_val}")
        st.rerun()

with c_suspend:
    st.markdown("### ⛔ Suspender / Activar")
    user_to_mod = st.selectbox("Seleccionar Usuario", df_users['username'], key="sel_suspend")
    
    current_active = bool(df_users[df_users['username'] == user_to_mod]['is_active'].values[0])
    btn_label = "⛔ SUSPENDER CUENTA" if current_active else "✅ REACTIVAR CUENTA"
    
    if st.button(btn_label, type="primary" if current_active else "secondary"):
        if user_to_mod == st.session_state.user:
            st.error("❌ No puedes suspender tu propia cuenta de Admin.")
        else:
            uid = int(df_users[df_users['username'] == user_to_mod]['id'].values[0])
            toggle_user_status(uid, current_active)
            st.success(f"Estado de {user_to_mod} actualizado.")
            st.rerun()
