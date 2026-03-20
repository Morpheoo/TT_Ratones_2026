"""
Control de acceso basado en roles para las páginas del sistema
"""
import streamlit as st

def require_login(redirect_message="🔒 Debes iniciar sesión para acceder a esta página."):
    """
    Verifica que el usuario esté autenticado.
    Si no lo está, muestra un mensaje y detiene la ejecución de la página.
    """
    if not st.session_state.get("logged_in", False):
        st.error(redirect_message)
        st.info("Por favor, ve a la página de **Login** en el menú lateral.")
        st.stop()

def require_role(allowed_roles, redirect_message=None):
    """
    Verifica que el usuario tenga uno de los roles permitidos.
    
    Args:
        allowed_roles: Lista de roles permitidos (ej: ["admin", "investigador"])
        redirect_message: Mensaje personalizado si el acceso es denegado
    """
    # Primero verificar que esté logged in
    require_login()
    
    user_role = st.session_state.get("role", None)
    
    if user_role not in allowed_roles:
        if redirect_message is None:
            redirect_message = f"⛔ Acceso denegado. Esta página requiere uno de los siguientes roles: {', '.join(allowed_roles)}"
        st.error(redirect_message)
        st.warning(f"Tu rol actual es: **{user_role}**")
        st.info("Contacta al administrador si crees que deberías tener acceso.")
        st.stop()

def require_admin():
    """Verifica que el usuario sea administrador"""
    require_role(
        ["admin"],
        redirect_message="⛔ Acceso denegado. Solo los administradores pueden acceder a esta página."
    )

def require_researcher():
    """Verifica que el usuario sea investigador o estudiante (NO admin)"""
    require_role(
        ["investigador", "estudiante"],
        redirect_message="⛔ Acceso denegado. Los administradores no pueden acceder a los módulos experimentales."
    )
