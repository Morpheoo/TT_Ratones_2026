import streamlit as st
import os
import sys
import time

# ================= 0. SETUP & PERSISTENCE =================
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from session_utils import load_session, save_session
from auth import authenticate, register_user, verify_otp, request_password_reset, reset_password
from ui_components import run_page_splash
import importlib
import ui_theme
importlib.reload(ui_theme)
from ui_theme import use_theme

st.set_page_config(page_title="Login | Sistema EPM", page_icon="assets/logos/logo_ria.png", layout="centered")

load_session()
colors = use_theme()

run_page_splash(
    "page_login",
    [
        "Validando entorno institucional...",
        "Preparando autenticación segura...",
        "Cargando acceso a la plataforma...",
    ],
    subtitle="TT 2026 - Preparando acceso seguro...",
)

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

# ================= 1. CABECERA LIMPIA LOGIN =================
from ui_theme import get_image_base64
logo_ria_path = os.path.join("assets", "logos", "logo_ria.png")
app_logo_b64 = get_image_base64(logo_ria_path)
img_tag = f'<img src="{app_logo_b64}" style="width: 150px; margin-bottom: 0.5rem; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));">' if app_logo_b64 else ''

st.markdown(f"""
<div style="text-align: center; margin-bottom: 2rem;">
    {img_tag}
    <div style="font-size: 2.2rem; margin-bottom: 0.2rem; letter-spacing: -0.5px; color: {colors['primary_dark']}; font-weight: 800;">
        SISTEMA EPM
    </div>
    <div style="font-size: 0.85rem; color: {colors['text_sub']}; text-transform: uppercase; font-weight: 600; letter-spacing: 1.5px;">
        Instituto Politécnico Nacional — ESCOM
    </div>
</div>
""", unsafe_allow_html=True)

# ================= 2. ESTILOS LOCALES PARA LOGIN =================
bg_card = colors.get('bg_card', '#FFFFFF')
border_c = colors.get('border', '#EAE3E6')
primary_c = colors.get('primary', '#6A1B3F')
text_sub_c = colors.get('text_sub', '#737373')
text_main_c = colors.get('text_main', '#1F1F1F')

st.markdown(f"""
    <style>
    /* Target the form container to be the login card */
    [data-testid="stForm"] {{
        background: {bg_card} !important;
        padding: 2.5rem 3rem !important;
        border-radius: 16px !important;
        border: 1px solid {border_c} !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.03) !important;
        margin: auto !important;
        max-width: {'550px' if st.session_state.get('auth_mode') == 'register' else '450px'} !important;
    }}
    
    /* REDISEÑO TOTAL DEL BOTÓN (White theme - Redo from scratch) */
    /* Target via tag, kind, and multiple test-ids to ensure catch-all */
    div.stButton > button[kind="primary"],
    [data-testid="stForm"] button[kind="primary"],
    [data-testid="stForm"] button[data-testid*="primary"],
    [data-testid="stFormSubmitButton"] button {{
        background-color: #FFFFFF !important;
        color: #6A1B3F !important;
        border: 2px solid #6A1B3F !important;
        border-radius: 12px !important;
        padding: 0.8rem 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        transition: all 0.25s ease-out !important;
        box-shadow: 0 4px 12px rgba(106, 27, 63, 0.08) !important;
        min-height: 52px !important;
        cursor: pointer !important;
        width: 100% !important;
    }}
    
    /* Target text inside button broadly */
    [data-testid="stForm"] button[kind="primary"] *,
    [data-testid="stForm"] button[data-testid*="primary"] *,
    [data-testid="stFormSubmitButton"] button * {{
        color: #6A1B3F !important;
        font-weight: 800 !important;
        background: transparent !important;
        border: none !important;
    }}

    /* Hover state robust redo */
    div.stButton > button[kind="primary"]:hover,
    [data-testid="stForm"] button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button:hover {{
        background-color: #6A1B3F !important;
        color: #FFFFFF !important;
        box-shadow: 0 8px 25px rgba(106, 27, 63, 0.25) !important;
        transform: translateY(-2px) !important;
        border-color: #6A1B3F !important;
    }}
    
    [data-testid="stForm"] button[kind="primary"]:hover *,
    [data-testid="stFormSubmitButton"] button:hover * {{
        color: #FFFFFF !important;
    }}

    .login-title {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.7rem;
        color: {text_main_c};
        margin-bottom: 0.2rem;
        text-align: center;
    }}
    .login-subtitle {{
        font-size: 0.95rem;
        color: {text_sub_c};
        margin-bottom: 2rem;
        text-align: center;
    }}
    </style>
""", unsafe_allow_html=True)

# ================= 3. LÓGICA DE NAVEGACIÓN =================
if st.session_state.auth_mode == "login":
    st.markdown('<div class="login-title">Inicia Sesión</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa tus credenciales para continuar</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Correo Electrónico Institucional", placeholder="ejemplo@alumno.ipn.mx")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        submit = st.form_submit_button("Entrar de forma segura", type="primary", use_container_width=True)

    if submit:
        if email and password:
            user_data = authenticate(email, password)
            if user_data:
                # Verificar si la cuenta está verificada
                if user_data.get("status") == "NOT_VERIFIED":
                    st.warning("Tu cuenta no está verificada. Revisa tu correo para el código de verificación.")
                    st.session_state.auth_mode = "verify"
                    st.session_state.pending_verification_email = user_data["email"]
                    time.sleep(1)
                    st.rerun()
                elif user_data.get("status") == "SUSPENDED":
                    st.error("Tu cuenta ha sido suspendida. Contacta al administrador.")
                elif user_data.get("status") == "ACTIVE":
                    st.session_state.logged_in = True
                    st.session_state.user = user_data["email"]
                    st.session_state.user_name = user_data["name"]
                    st.session_state.role = user_data["role"]
                    save_session()
                    st.success("Autenticación exitosa.")
                    time.sleep(1)
                    st.switch_page("Home.py")
                else:
                    st.error("Credenciales incorrectas o cuenta inactiva.")
            else:
                st.error("Credenciales incorrectas o cuenta inactiva.")
        else:
            st.warning("Completa todos los campos requeridos.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("¿No tienes cuenta? Solicita acceso aquí", use_container_width=True):
        st.session_state.auth_mode = "register"
        st.rerun()

elif st.session_state.auth_mode == "register":
    st.markdown('<div class="login-title">Crear Cuenta</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Acceso exclusivo para comunidad IPN</div>', unsafe_allow_html=True)
    
    # Inicializar tipo de registro si no existe
    if "register_type" not in st.session_state:
        st.session_state.register_type = "estudiante"
    
    # Selector de tipo de usuario
    st.markdown("<div style='margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(
            "Estudiante", 
            type="primary" if st.session_state.register_type == "estudiante" else "secondary",
            use_container_width=True
        ):
            st.session_state.register_type = "estudiante"
            st.rerun()
    with col_btn2:
        if st.button(
            "Investigador / Docente", 
            type="primary" if st.session_state.register_type == "investigador" else "secondary",
            use_container_width=True
        ):
            st.session_state.register_type = "investigador"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Formulario según el tipo seleccionado
    if st.session_state.register_type == "estudiante":
        with st.form("reg_form_estudiante"):
            st.markdown(f"<div style='text-align: center; font-weight: 600; color: {colors['primary']}; margin-bottom: 1rem;'>REGISTRO DE ESTUDIANTE</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nombre Completo *")
                boleta = st.text_input("Número de Boleta *")
            with col2:
                carrera = st.text_input("Carrera")
                escuela = st.text_input("Escuela (ej. ESCOM)")
            
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
            new_email = st.text_input("Correo Institucional (@alumno.ipn.mx) *")
            new_pass = st.text_input("Contraseña segura *", type="password")
            
            st.markdown("""
                <div style="background: rgba(0,0,0,0.03); padding: 1rem; border-radius: 8px; font-size: 0.75rem; color: #555; margin-bottom: 10px; border: 1px solid rgba(0,0,0,0.05); text-align: justify;">
                    <strong>Términos y Condiciones:</strong> Al registrarte en el Sistema EPM, te comprometes al uso estrictamente académico y ético de las herramientas de análisis IA. Los datos generados son propiedad del laboratorio y deben ser tratados con confidencialidad según los lineamientos del IPN. El mal uso de la plataforma resultará en la suspensión inmediata del acceso.
                </div>
            """, unsafe_allow_html=True)
            accepted = st.checkbox("He leído y acepto los lineamientos institucionales y términos de uso.")
            
            reg_submit = st.form_submit_button("Solicitar Acceso", type="primary", use_container_width=True)

        if reg_submit:
            if not accepted:
                st.error("Debes aceptar los términos institucionales.")
            elif not all([full_name, boleta, new_email, new_pass]):
                st.warning("Completa los campos obligatorios (*).")
            else:
                success, msg = register_user(
                    email=new_email, 
                    password=new_pass, 
                    role="estudiante", 
                    full_name=full_name,
                    boleta=boleta,
                    carrera=carrera,
                    escuela=escuela,
                    accepted_terms=accepted
                )
                if success:
                    st.success("Registro enviado. Revisa tu correo para el código de verificación.")
                    st.session_state.auth_mode = "verify"
                    st.session_state.pending_verification_email = new_email
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
    
    else:  # investigador
        with st.form("reg_form_investigador"):
            st.markdown(f"<div style='text-align: center; font-weight: 600; color: {colors['primary']}; margin-bottom: 1rem;'>REGISTRO DE INVESTIGADOR / DOCENTE</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nombre Completo *")
                num_empleado = st.text_input("Número de Empleado *")
            with col2:
                area = st.text_input("Área de Investigación")
                centro = st.text_input("Centro / Unidad (ej. ESCOM)")
            
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
            new_email = st.text_input("Correo Institucional (@ipn.mx) *")
            new_pass = st.text_input("Contraseña segura *", type="password")
            
            st.markdown("""
                <div style="background: rgba(0,0,0,0.03); padding: 1rem; border-radius: 8px; font-size: 0.75rem; color: #555; margin-bottom: 10px; border: 1px solid rgba(0,0,0,0.05); text-align: justify;">
                    <strong>Términos y Condiciones:</strong> Al registrarte en el Sistema EPM, te comprometes al uso estrictamente académico y ético de las herramientas de análisis IA. Los datos generados son propiedad del laboratorio y deben ser tratados con confidencialidad según los lineamientos del IPN. El mal uso de la plataforma resultará en la suspensión inmediata del acceso.
                </div>
            """, unsafe_allow_html=True)
            accepted = st.checkbox("He leído y acepto los lineamientos institucionales y términos de uso.")
            
            reg_submit = st.form_submit_button("Solicitar Acceso", type="primary", use_container_width=True)

        if reg_submit:
            if not accepted:
                st.error("Debes aceptar los términos institucionales.")
            elif not all([full_name, num_empleado, new_email, new_pass]):
                st.warning("Completa los campos obligatorios (*).")
            else:
                success, msg = register_user(
                    email=new_email, 
                    password=new_pass, 
                    role="investigador", 
                    full_name=full_name,
                    num_empleado=num_empleado,
                    area=area,
                    centro=centro,
                    accepted_terms=accepted
                )
                if success:
                    st.success("Registro enviado. Revisa tu correo para el código de verificación.")
                    st.session_state.auth_mode = "verify"
                    st.session_state.pending_verification_email = new_email
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
            
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Volver al Inicio de Sesión", use_container_width=True):
        st.session_state.auth_mode = "login"
        st.rerun()

elif st.session_state.auth_mode == "verify":
    st.markdown('<div class="login-title">Verificar Cuenta</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa el código que enviamos a tu correo</div>', unsafe_allow_html=True)
    
    # Mostrar el email pendiente de verificación
    if "pending_verification_email" in st.session_state:
        email_to_verify = st.session_state.pending_verification_email
        st.info(f"Código enviado a: {email_to_verify}")
    else:
        st.error("No hay email pendiente de verificación.")
        st.session_state.auth_mode = "login"
        st.rerun()
    
    with st.form("verify_form"):
        otp_code = st.text_input("Código de Verificación (6 dígitos)", placeholder="123456", max_chars=6)
        verify_submit = st.form_submit_button("Verificar Cuenta", type="primary", use_container_width=True)
    
    if verify_submit:
        if otp_code and len(otp_code) == 6:
            success, msg = verify_otp(email_to_verify, otp_code)
            if success:
                st.success(msg)
                st.balloons()
                time.sleep(2)
                # Limpiar estado y volver al login
                if "pending_verification_email" in st.session_state:
                    del st.session_state.pending_verification_email
                st.session_state.auth_mode = "login"
                st.info("Ahora puedes iniciar sesión con tus credenciales.")
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
        else:
            st.warning("Ingresa un código de 6 dígitos.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Opción para reenviar código
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reenviar Código", use_container_width=True):
            # Importar función para reenviar código
            from auth import request_password_reset
            # Generar nuevo código y enviarlo
            import random
            from sqlalchemy import text
            from db.connection import get_db_engine
            from email_utils import send_verification_email
            
            new_otp = str(random.randint(100000, 999999))
            engine = get_db_engine()
            
            try:
                with engine.connect() as conn:
                    with conn.begin():
                        update = text("""
                            UPDATE users 
                            SET verification_code = :code, 
                                verification_code_created_at = CURRENT_TIMESTAMP 
                            WHERE username = :email
                        """)
                        conn.execute(update, {"code": new_otp, "email": email_to_verify})
                        
                        # Enviar nuevo correo
                        sent, msg = send_verification_email(email_to_verify, new_otp)
                        if sent:
                            st.success("Nuevo código enviado a tu correo.")
                        else:
                            st.error(f"Error al enviar correo: {msg}")
            except Exception as e:
                st.error(f"Error al generar nuevo código: {e}")
    
    with col2:
        if st.button("Volver al Login", use_container_width=True):
            if "pending_verification_email" in st.session_state:
                del st.session_state.pending_verification_email
            st.session_state.auth_mode = "login"
            st.rerun()

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align:center; color: {text_sub_c}; font-size: 0.75rem;">
        Sistema Técnico para Análisis Automatizado de Comportamiento &copy; 2026<br>
        Laboratorio de Proyectos Profesionales — IPN ESCOM
    </div>
""", unsafe_allow_html=True)
