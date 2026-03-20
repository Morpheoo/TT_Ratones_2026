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

# Cargar sesión para tener el rol actualizado
load_session()

# =============== TEMA INSTITUCIONAL =================
from ui_theme import use_theme
use_theme()

# ================= SEGURIDAD: SOLO ADMINS =================
role = st.session_state.get("role", "")
if not check_admin_access(role):
    st.warning("⛔ Acceso Denegado. Esta página es exclusiva para Administradores.")
    st.stop()

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

# ================= GESTIÓN DE EXPERIMENTOS =================
st.divider()
st.markdown("## 🧪 Gestión de Experimentos")

def get_all_experiments():
    with engine.connect() as conn:
        query = text("""
            SELECT e.id, e.rat_id, e.treatment, e.experiment_date,
                   e.responsible, e.processed, e.created_at,
                   u.username AS creado_por
            FROM experiments e
            LEFT JOIN users u ON e.created_by = u.id
            ORDER BY e.id DESC
        """)
        result = conn.execute(query).fetchall()
        return pd.DataFrame(result)

def delete_experiment_by_id(exp_id):
    """Borra experimento + ROIs + resultados (CASCADE)."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM experiments WHERE id = :id"), {"id": exp_id})
        conn.commit()

def delete_unprocessed_experiments():
    """Borra todos los experimentos no procesados."""
    with engine.connect() as conn:
        result = conn.execute(text("DELETE FROM experiments WHERE processed = FALSE"))
        conn.commit()
        return result.rowcount

df_exp = get_all_experiments()

if df_exp.empty:
    st.info("📭 No hay experimentos registrados en la base de datos.")
else:
    # Métricas rápidas
    e1, e2, e3 = st.columns(3)
    e1.metric("Total Experimentos", len(df_exp))
    e2.metric("Procesados", len(df_exp[df_exp['processed'] == True]))
    e3.metric("Sin Procesar", len(df_exp[df_exp['processed'] == False]))

    # Tabla de experimentos
    st.dataframe(
        df_exp,
        column_config={
            "id": "ID",
            "rat_id": "Sujeto",
            "treatment": "Tratamiento",
            "experiment_date": st.column_config.DateColumn("Fecha Exp."),
            "responsible": "Responsable",
            "processed": st.column_config.CheckboxColumn("Procesado"),
            "created_at": st.column_config.DatetimeColumn("Fecha Registro"),
            "creado_por": "Creado Por",
        },
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    col_del, col_bulk = st.columns([1, 1])

    # --- Borrado Individual ---
    with col_del:
        st.markdown("### 🗑️ Eliminar Experimento")
        exp_options = [f"ID {row['id']} — {row['rat_id']} ({row['treatment']})" for _, row in df_exp.iterrows()]
        selected_exp = st.selectbox("Seleccionar Experimento", exp_options, key="sel_exp_del")

        if selected_exp:
            exp_id_to_del = int(selected_exp.split(" ")[1])

            st.warning(
                f"⚠️ Esto eliminará el experimento **ID {exp_id_to_del}** junto con "
                f"todas sus ROIs y resultados de análisis asociados."
            )
            confirm = st.checkbox(f"Confirmo que quiero eliminar el experimento {exp_id_to_del}", key="confirm_del")

            if st.button("🗑️ Eliminar", disabled=not confirm, type="primary"):
                delete_experiment_by_id(exp_id_to_del)
                st.success(f"✅ Experimento {exp_id_to_del} eliminado correctamente.")
                st.rerun()

    # --- Borrado Masivo ---
    with col_bulk:
        st.markdown("### 🧹 Limpieza Masiva")
        n_unprocessed = len(df_exp[df_exp['processed'] == False])

        if n_unprocessed == 0:
            st.success("✅ No hay experimentos sin procesar.")
        else:
            st.error(f"Hay **{n_unprocessed}** experimento(s) sin procesar.")
            confirm_bulk = st.checkbox(
                f"Confirmo eliminar TODOS los {n_unprocessed} experimentos sin procesar",
                key="confirm_bulk"
            )
            if st.button("🧹 Eliminar Todos Sin Procesar", disabled=not confirm_bulk, type="primary"):
                deleted = delete_unprocessed_experiments()
                st.success(f"✅ {deleted} experimento(s) eliminados.")
                st.rerun()

