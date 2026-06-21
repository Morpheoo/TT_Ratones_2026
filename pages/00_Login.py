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

st.set_page_config(page_title="Inicio de sesión", page_icon="assets/logos/logo_ria.png", layout="centered")

load_session()
colors = use_theme()

run_page_splash(
    "page_login",
    [
        "Validando entorno institucional...",
        "Preparando autenticación segura...",
        "Cargando acceso a la plataforma...",
    ],
    subtitle="Preparando acceso seguro...",
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
        Prototipo para análisis automatizado y visualización de comportamiento de especímenes en modelos de ansiedad
    </div>
    <div style="font-size: 0.85rem; color: {colors['text_sub']}; text-transform: uppercase; font-weight: 600; letter-spacing: 1.5px;">
        Instituto Politécnico Nacional — Escuela Superior de Cómputo
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
        max-width: {'550px' if st.session_state.get('auth_mode') in ['register'] else '480px' if st.session_state.get('auth_mode') in ['reset_password'] else '450px'} !important;
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
    st.markdown('<div class="login-title">Inicia sesión</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa tus credenciales para continuar</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input(
            "Correo institucional", 
            placeholder="ejemplo@alumno.ipn.mx | ejemplo@ipn.mx",
            max_chars=254
        )
        password = st.text_input(
            "Contraseña", 
            type="password", 
            placeholder="••••••••",
            max_chars=128
        )
        submit = st.form_submit_button("Ingresar", type="primary", use_container_width=True)

    if submit:
        if not email or not password:
            st.warning("Completa todos los campos requeridos.")
        elif len(email) > 254 or len(password) > 128:
            st.error("Los datos ingresados exceden la longitud máxima permitida.")
        elif not "@" in email or email.count("@") != 1:
            st.error("El formato del correo electrónico es inválido.")
        elif any(char in email for char in ['<', '>', '"', "'", ';', '\\', '|', '&', '$', '`']):
            st.error("El correo contiene caracteres no permitidos.")
        else:
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("¿No tienes cuenta? Solicita acceso aquí", use_container_width=True):
            st.session_state.auth_mode = "register"
            st.rerun()
    with col2:
        if st.button("¿Olvidaste tu contraseña?", use_container_width=True):
            st.session_state.auth_mode = "forgot_password"
            st.rerun()

elif st.session_state.auth_mode == "register":
    st.markdown('<div class="login-title">Crear cuenta</div>', unsafe_allow_html=True)
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
            st.markdown(f"<div style='text-align: center; font-weight: 600; color: {colors['primary']}; margin-bottom: 1rem;'>Registro de estudiante</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nombre completo *")
                boleta = st.text_input(
                    "Número de boleta *",
                    max_chars=10,
                    help="Exactamente 10 dígitos numéricos"
                )
            with col2:
                carrera = st.text_input("Carrera")
                escuela = st.text_input("Escuela (ej. ESCOM)")
            
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
            new_email = st.text_input("Correo institucional (@alumno.ipn.mx) *")
            new_pass = st.text_input(
                "Contraseña segura *",
                type="password",
                help="Mínimo 8 caracteres, al menos 1 mayúscula y 1 número"
            )
            
            st.markdown("""
                <div style="background: rgba(0,0,0,0.03); padding: 1rem; border-radius: 8px; font-size: 0.75rem; color: #555; margin-bottom: 10px; border: 1px solid rgba(0,0,0,0.05); text-align: justify;">
                    <strong>Términos y condiciones:</strong> Al registrarte en este prototipo, te comprometes al uso estrictamente académico y ético de las herramientas de análisis IA. Los datos generados son propiedad del laboratorio y deben ser tratados con confidencialidad según los lineamientos del IPN. El mal uso de la plataforma resultará en la suspensión inmediata del acceso.
                </div>
            """, unsafe_allow_html=True)
            accepted = st.checkbox("He leído y acepto los lineamientos institucionales y términos de uso.")
            
            reg_submit = st.form_submit_button("Solicitar Acceso", type="primary", use_container_width=True)

        if reg_submit:
            if not accepted:
                st.error("Debes aceptar los términos institucionales.")
            elif not all([full_name, boleta, new_email, new_pass]):
                st.warning("Completa los campos obligatorios (*).")
            elif len(boleta) != 10 or not boleta.isdigit():
                st.error("El número de boleta debe tener exactamente 10 dígitos numéricos.")
            elif len(new_pass) < 8:
                st.error("La contraseña debe tener al menos 8 caracteres.")
            elif not any(c.isupper() for c in new_pass):
                st.error("La contraseña debe contener al menos 1 letra mayúscula.")
            elif not any(c.isdigit() for c in new_pass):
                st.error("La contraseña debe contener al menos 1 número.")
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
            st.markdown(f"<div style='text-align: center; font-weight: 600; color: {colors['primary']}; margin-bottom: 1rem;'>Registro de investigador / docente</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nombre completo *")
                num_empleado = st.text_input(
                    "Número de empleado *",
                    max_chars=10,
                    help="Entre 4 y 10 dígitos numéricos"
                )
            with col2:
                area = st.text_input("Área de investigación")
                centro = st.text_input("Centro / Unidad (ej. ESCOM)")
            
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.1;'>", unsafe_allow_html=True)
            new_email = st.text_input("Correo institucional (@ipn.mx) *")
            new_pass = st.text_input(
                "Contraseña segura *",
                type="password",
                help="Mínimo 8 caracteres, al menos 1 mayúscula y 1 número."
            )
            
            st.markdown("""
                <div style="background: rgba(0,0,0,0.03); padding: 1rem; border-radius: 8px; font-size: 0.75rem; color: #555; margin-bottom: 10px; border: 1px solid rgba(0,0,0,0.05); text-align: justify;">
                    <strong>Términos y condiciones:</strong> Al registrarte en este prototipo, te comprometes al uso estrictamente académico y ético de las herramientas de análisis IA. Los datos generados son propiedad del laboratorio y deben ser tratados con confidencialidad según los lineamientos del IPN. El mal uso de la plataforma resultará en la suspensión inmediata del acceso.
                </div>
            """, unsafe_allow_html=True)
            accepted = st.checkbox("He leído y acepto los lineamientos institucionales y términos de uso.")
            
            reg_submit = st.form_submit_button("Solicitar acceso", type="primary", use_container_width=True)

        if reg_submit:
            if not accepted:
                st.error("Debes aceptar los términos y condiciones.")
            elif not all([full_name, num_empleado, new_email, new_pass]):
                st.warning("Completa los campos obligatorios (*).")
            elif len(num_empleado) < 4 or len(num_empleado) > 10 or not num_empleado.isdigit():
                st.error("El número de empleado debe tener entre 4 y 10 dígitos numéricos.")
            elif len(new_pass) < 8:
                st.error("La contraseña debe tener al menos 8 caracteres.")
            elif not any(c.isupper() for c in new_pass):
                st.error("La contraseña debe contener al menos 1 letra mayúscula.")
            elif not any(c.isdigit() for c in new_pass):
                st.error("La contraseña debe contener al menos 1 número.")
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
    if st.button("Volver al inicio de sesión", use_container_width=True):
        st.session_state.auth_mode = "login"
        st.rerun()

elif st.session_state.auth_mode == "verify":
    st.markdown('<div class="login-title">Verificar cuenta</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa el código que enviamos a tu correo</div>', unsafe_allow_html=True)
    
    # Mostrar el email pendiente de verificación
    if "pending_verification_email" in st.session_state:
        email_to_verify = st.session_state.pending_verification_email
        st.info(f"Código enviado a: {email_to_verify}. Revisa tu bandeja de entrada y carpeta de spam.")
    else:
        st.error("No hay email pendiente de verificación.")
        st.session_state.auth_mode = "login"
        st.rerun()
    
    with st.form("verify_form"):
        otp_code = st.text_input("Código de verificación", placeholder="123456", max_chars=6)
        verify_submit = st.form_submit_button("Verificar cuenta", type="primary", use_container_width=True)
    
    if verify_submit:
        if not otp_code:
            st.warning("Ingresa el código de verificación.")
        elif len(otp_code) != 6:
            st.warning("El código debe ser de 6 dígitos.")
        elif not otp_code.isdigit():
            st.error("El código debe contener solo números.")
        else:
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Opción para reenviar código
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reenviar código", use_container_width=True):
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
        if st.button("Volver al inicio de sesión", use_container_width=True):
            if "pending_verification_email" in st.session_state:
                del st.session_state.pending_verification_email
            st.session_state.auth_mode = "login"
            st.rerun()

elif st.session_state.auth_mode == "forgot_password":
    st.markdown('<div class="login-title">Recuperar contraseña</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa tu correo para recibir un código de recuperación</div>', unsafe_allow_html=True)
    
    with st.form("forgot_password_form"):
        recovery_email = st.text_input(
            "Correo institucional",
            placeholder="ejemplo@alumno.ipn.mx",
            max_chars=254
        )
        send_code_submit = st.form_submit_button("Enviar código de recuperación", type="primary", use_container_width=True)
    
    if send_code_submit:
        if not recovery_email:
            st.warning("Ingresa tu correo electrónico.")
        elif not "@" in recovery_email or recovery_email.count("@") != 1:
            st.error("El formato del correo electrónico es inválido.")
        else:
            success, msg = request_password_reset(recovery_email)
            if success:
                st.success("Código de recuperación enviado a tu correo.")
                st.session_state.password_reset_email = recovery_email
                st.session_state.auth_mode = "reset_password"
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Volver al inicio de sesión", use_container_width=True):
        st.session_state.auth_mode = "login"
        st.rerun()

elif st.session_state.auth_mode == "reset_password":
    st.markdown('<div class="login-title">Nueva contraseña</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Ingresa el código y tu nueva contraseña</div>', unsafe_allow_html=True)
    
    # Mostrar el email al que se envió el código
    if "password_reset_email" in st.session_state:
        reset_email = st.session_state.password_reset_email
        st.info(f"Código enviado a: {reset_email}")
    else:
        st.error("No hay solicitud de recuperación activa.")
        st.session_state.auth_mode = "login"
        st.rerun()
    
    with st.form("reset_password_form"):
        otp_code = st.text_input("Código de verificación (6 dígitos)", placeholder="123456", max_chars=6)
        new_password = st.text_input(
            "Nueva contraseña",
            type="password",
            placeholder="••••••••",
            help="Mínimo 8 caracteres, al menos 1 mayúscula y 1 número",
            max_chars=128
        )
        confirm_password = st.text_input(
            "Confirmar nueva contraseña",
            type="password",
            placeholder="••••••••",
            max_chars=128
        )
        reset_submit = st.form_submit_button("Restablecer contraseña", type="primary", use_container_width=True)
    
    if reset_submit:
        if not otp_code or not new_password or not confirm_password:
            st.warning("Completa todos los campos.")
        elif len(otp_code) != 6 or not otp_code.isdigit():
            st.error("El código debe ser de 6 dígitos numéricos.")
        elif new_password != confirm_password:
            st.error("Las contraseñas no coinciden.")
        elif len(new_password) < 8:
            st.error("La contraseña debe tener al menos 8 caracteres.")
        elif not any(c.isupper() for c in new_password):
            st.error("La contraseña debe contener al menos 1 letra mayúscula.")
        elif not any(c.isdigit() for c in new_password):
            st.error("La contraseña debe contener al menos 1 número.")
        else:
            success, msg = reset_password(reset_email, otp_code, new_password)
            if success:
                st.success("¡Contraseña actualizada exitosamente!")
                st.balloons()
                time.sleep(2)
                # Limpiar estado
                if "password_reset_email" in st.session_state:
                    del st.session_state.password_reset_email
                st.session_state.auth_mode = "login"
                st.info("Ahora puedes iniciar sesión con tu nueva contraseña.")
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Opciones para reenviar código o volver
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reenviar código", use_container_width=True):
            success, msg = request_password_reset(reset_email)
            if success:
                st.success("Nuevo código enviado a tu correo.")
            else:
                st.error(msg)
    with col2:
        if st.button("Volver al inicio de sesión", use_container_width=True):
            if "password_reset_email" in st.session_state:
                del st.session_state.password_reset_email
            st.session_state.auth_mode = "login"
            st.rerun()

st.markdown("<br><br>", unsafe_allow_html=True)

# Aviso legal y Términos
col_legal1, col_legal2 = st.columns(2)

with col_legal1:
    with st.expander("Aviso Legal"):
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
    with st.expander("Términos y Condiciones"):
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

# Link al manual de usuario
st.markdown(f"""
    <div style="text-align:center; color: {text_sub_c}; font-size: 0.75rem;">
        Prototipo para análisis automatizado y visualización de comportamiento de especímenes en modelos de ansiedad &copy; 2026<br>
    </div>
""", unsafe_allow_html=True)
