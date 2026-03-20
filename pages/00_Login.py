import streamlit as st
import base64
import os
import sys

# Seteamos la ruta de src para importar utilerías
sys.path.append(os.path.join(os.getcwd(), "src"))
from session_utils import load_session, save_session

# Cargar sesión previa
if "init_done" not in st.session_state:
    load_session()
    st.session_state.init_done = True

# 1. CONFIGURACIÓN
st.set_page_config(page_title="TT 2026 - Login", page_icon="🐭", layout="wide")

# 2. FUNCIÓN DE IMAGEN
PRIVACY_NOTICE = """
**Aviso de Privacidad Simplificado – Sistema de Análisis EPM (TT 2026)**  

El equipo responsable del proyecto “TT 2026 – Sistema de Análisis EPM” de la Escuela Superior de Cómputo del Instituto Politécnico Nacional (ESCOM-IPN), es responsable del tratamiento de los datos personales que se recaben a través de esta plataforma.

**1. Datos personales que recabamos**  
Para el acceso y uso del sistema se recaban y tratan los siguientes datos personales:  
- Correo electrónico institucional (@ipn.mx).  
- Nombre de usuario asociado a la cuenta institucional.  
- Credenciales de acceso (que en su versión final deberán almacenarse de forma cifrada o mediante servicios de autenticación institucional).  

Adicionalmente, el sistema puede registrar información técnica relacionada con el uso de la plataforma, como fecha y hora de acceso, dirección IP y acciones realizadas dentro del sistema, con fines de seguridad y trazabilidad.

**2. Finalidades del tratamiento**  
Los datos personales serán utilizados para las siguientes finalidades:  
- Gestionar su autenticación e inicio de sesión en el sistema.  
- Administrar los permisos de acceso y los perfiles de usuario (p. ej. Investigador, Administrador).  
- Generar registros y bitácoras de uso con fines académicos, estadísticos y de mejora continua del sistema.  
- Dar cumplimiento a obligaciones derivadas de normas institucionales y disposiciones aplicables en materia de investigación y resguardo de información.  

No se utilizarán sus datos personales para finalidades distintas a las aquí señaladas sin obtener previamente su consentimiento.

**3. Transferencias de datos**  
Sus datos personales no serán vendidos, cedidos ni transferidos a terceros ajenos al proyecto, salvo en los casos en que lo exija una disposición legal aplicable o requerimientos formales de autoridades competentes o instancias del propio Instituto Politécnico Nacional.

**4. Medidas de seguridad**  
El proyecto implementa medidas de seguridad administrativas, técnicas y físicas razonables para proteger sus datos personales contra daño, pérdida, alteración, destrucción o uso, acceso o tratamiento no autorizado.

**5. Derechos ARCO y revocación del consentimiento**  
Usted puede ejercer sus derechos de Acceso, Rectificación, Cancelación u Oposición (ARCO), así como revocar el consentimiento otorgado para el tratamiento de sus datos personales, enviando una solicitud al correo electrónico de contacto del proyecto:  
**tt2026.epm@escom.ipn.mx**  

La solicitud deberá contener, al menos, nombre completo, correo institucional de contacto y la descripción clara del derecho que desea ejercer.

**6. Cambios al Aviso de Privacidad**  
Cualquier modificación al presente Aviso de Privacidad será publicada en esta misma plataforma, indicando la fecha de la última actualización.  

_Fecha de última actualización: diciembre de 2025._
"""

def get_img_as_base64(file_path: str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# LOGO
LOGO_PATH = "logo_ria.png"
img_base64 = get_img_as_base64(LOGO_PATH)
if img_base64:
    logo_html = f'<img src="data:image/png;base64,{img_base64}" class="tt-logo">'
else:
    logo_html = '<div style="text-align:center;">⚠️ Logo no encontrado</div>'

# 3. TEMA Y ESTILOS
from ui_theme import use_theme
use_theme()

# 4. CSS ESTILIZADO ESPECÍFICO DEL LOGIN
st.markdown(
    """
    <style>
    /* Estilizar el formulario principal como tarjeta IPN */
    [data-testid="stForm"] {
        background-color: var(--card-bg);
        padding: 3rem 3.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 15px var(--shadow);
        border: 1px solid var(--card-border);
        border-top: 4px solid var(--primary);
        max-width: 600px;
        margin: 2rem auto 1rem auto;
    }

    .tt-logo {
        width: 90px;
        height: auto;
    }

    h1.tt-title {
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.1rem !important;
        letter-spacing: -0.02em;
        color: var(--text-main);
        margin: 0 0 6px 0;
        padding: 0;
    }

    div.tt-subtitle {
        text-align: center;
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 32px;
        color: var(--primary);
    }

    @media (max-width: 768px) {
        [data-testid="stForm"] {
            padding: 2.3rem 1.6rem;
            max-width: 100%;
            margin: 2rem 1rem 1rem 1rem;
        }
        h1.tt-title {
            font-size: 1.7rem !important;
        }
        div.tt-subtitle {
            font-size: 0.95rem;
        }
        .tt-logo {
            width: 70px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# 5. AUTH UTILITY (Force Reload)
from src.auth import authenticate, register_user, verify_otp, resend_verification_code, request_password_reset, reset_password

# 6. LÓGICA DE SESIÓN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    st.success(f"Bienvenido, {st.session_state.user}")
    st.info(f"Rol: {st.session_state.role}")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        from src.session_utils import clear_session
        clear_session()
        st.rerun()
    st.stop()

# Logos institucionales
import os
import base64

def get_img_as_base64_login(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()

IPN_LOGO_PATH = os.path.join("assets", "logos", "logo_ipn.webp")
ESCOM_LOGO_PATH = os.path.join("assets", "logos", "logo_escom.webp")

ipn_img_base64 = get_img_as_base64_login(IPN_LOGO_PATH)
if ipn_img_base64: ipn_logo_html = f'<img src="data:image/webp;base64,{ipn_img_base64}" class="institucional-logo" style="width: 140px; height: auto;">'
else: ipn_logo_html = '<div style="width:140px; height:140px; border-radius:50%; background-color:var(--primary); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:18px; margin: 0 auto;">IPN</div>'

escom_img_base64 = get_img_as_base64_login(ESCOM_LOGO_PATH)
if escom_img_base64: escom_logo_html = f'<img src="data:image/webp;base64,{escom_img_base64}" class="institucional-logo" style="width: 80px; height: auto;">'
else: escom_logo_html = '<div style="width:80px; height:80px; border-radius:50%; background-color:var(--primary); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:12px; margin: 0 auto;">ESCOM</div>'

# 7. LAYOUT CENTRADO
c1, c2, c3 = st.columns([1, 2, 1])

with c2:
    st.markdown(
        f"""
        <style>
        .logos-container-login {{
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            width: 100%;
            margin-bottom: 2rem;
        }}
        .logo-left-lg, .logo-right-lg {{
            flex: 1;
            flex-basis: 33%;
            display: flex;
        }}
        .logo-left-lg {{
            justify-content: flex-start;
        }}
        .logo-right-lg {{
            justify-content: flex-end;
        }}
        .logo-center-lg {{
            flex: 1;
            flex-basis: 33%;
            display: flex;
            justify-content: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        f'''
        <div class="logos-container-login">
            <div class="logo-left-lg">{ipn_logo_html}</div>
            <div class="logo-center-lg">{logo_html}</div>
            <div class="logo-right-lg">{escom_logo_html}</div>
        </div>
        ''', unsafe_allow_html=True
    )
    st.markdown('<h1 class="tt-title">INSTITUTO POLITÉCNICO NACIONAL</h1>', unsafe_allow_html=True)
    st.markdown('<div class="tt-subtitle">Sistema EPM - Plataforma Institucional</div>', unsafe_allow_html=True)

    # MODIFICACIÓN: Si hay verificación pendiente, ocultamos los tabs para no confundir
    if st.session_state.get("show_verification"):
        st.info(f"📧 Hemos enviado un código de verificación a: **{st.session_state.get('pending_email')}**")
        st.warning("⚠️ Revisa tu carpeta de SPAM o 'Correo no deseado'.")
        
        st.markdown("### 🔐 Ingresa el Código")
        with st.form("verify_form"):
            otp_input = st.text_input("Código de 6 dígitos", max_chars=6, placeholder="Ej: 123456")
            verify_btn = st.form_submit_button("VERIFICAR CUENTA")
            
            if verify_btn:
                success, msg = verify_otp(st.session_state.get("pending_email"), otp_input)
                if success:
                    st.success("✅ ¡Cuenta verificada! Accediendo...")
                    st.session_state["show_verification"] = False
                    st.session_state["pending_email"] = None
                    st.balloons()
                    # Opcional: Auto-login si guardamos credentials
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
                    
        # Botón de reenvío fuera del form para no enviar el form principal
        col_resend, col_back = st.columns([1, 1])
        with col_resend:
            if st.button("🔄 Reenviar Código"):
                success_rs, msg_rs = resend_verification_code(st.session_state.get("pending_email"))
                if success_rs:
                    st.toast(msg_rs)
                else:
                    st.error(msg_rs)
                    
        with col_back:
            if st.button("⬅️ Volver"):
                st.session_state["show_verification"] = False
                st.session_state["pending_email"] = None
                st.rerun()

    elif st.session_state.get("show_recovery"):
        # PANTALLA DE RECUPERACIÓN DE CONTRASEÑA
        st.markdown("### 🔄 Recuperar Contraseña")
        
        if not st.session_state.get("recovery_step_2"):
            # PASO 1: Solicitar Correo
            st.info("Ingresa tu correo institucional para recibir un código de recuperación.")
            with st.form("recovery_req_form"):
                rec_email = st.text_input("Correo Registrado", placeholder="usuario@ipn.mx")
                req_btn = st.form_submit_button("ENVIAR CÓDIGO")
                
                if req_btn:
                    success, msg = request_password_reset(rec_email)
                    if success:
                        st.session_state["recovery_email"] = rec_email
                        st.session_state["recovery_step_2"] = True
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            
            if st.button("⬅️ Volver al Login"):
                st.session_state["show_recovery"] = False
                st.rerun()
                
        else:
            # PASO 2: Ingresar OTP y Nueva pass
            st.success(f"Código enviado a: {st.session_state.get('recovery_email')}")
            with st.form("recovery_reset_form"):
                otp_rec = st.text_input("Código de Verificación", max_chars=6)
                new_p1 = st.text_input("Nueva Contraseña", type="password")
                new_p2 = st.text_input("Confirmar Nueva Contraseña", type="password")
                reset_btn = st.form_submit_button("CAMBIAR CONTRASEÑA")
                
                if reset_btn:
                    if new_p1 != new_p2:
                        st.error("Las contraseñas no coinciden.")
                    elif len(new_p1) < 6:
                        st.error("Mínimo 6 caracteres.")
                    else:
                        success, msg = reset_password(st.session_state.get("recovery_email"), otp_rec, new_p1)
                        if success:
                            st.success(msg)
                            st.balloons()
                            # Resetear estados y volver a login
                            st.session_state["show_recovery"] = False
                            st.session_state["recovery_step_2"] = False
                            st.session_state["recovery_email"] = None
                            st.rerun()
                        else:
                            st.error(msg)
                            
            if st.button("⬅️ Cancelar"):
                st.session_state["show_recovery"] = False
                st.session_state["recovery_step_2"] = False
                st.rerun()

    else:
        # PANTALLA NORMAL (Login / Registro)
        tab_login, tab_register = st.tabs(["🔐 Iniciar Sesión", "📝 Registro IPN"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Usuario", placeholder="correo@ipn.mx")
                password = st.text_input("Contraseña", type="password", placeholder="••••••")
                submitted = st.form_submit_button("INGRESAR")
                
                if submitted:
                    # Intentar login
                    auth_result = authenticate(email, password)
                    
                    if auth_result and auth_result.get("status") == "ACTIVE":
                        st.session_state.logged_in = True
                        st.session_state.user = auth_result["email"]
                        st.session_state.role = auth_result["role"]
                        st.session_state.user_name = auth_result["name"]
                        save_session()
                        st.success(f"✅ Bienvenido {auth_result['name']}")
                        st.rerun()
                        
                    elif auth_result and auth_result.get("status") == "SUSPENDED":
                        st.error("⛔ Tu cuenta ha sido SUSPENDIDA por un administrador.")
                        st.warning("Contacta al administrador si crees que es un error.")

                    elif auth_result and auth_result.get("status") == "NOT_VERIFIED":
                        st.session_state["pending_email"] = email
                        st.warning("⚠️ Tu cuenta no está verificada. Revisa tu correo IPN.")
                        st.session_state["show_verification"] = True
                        st.rerun()
                        
                    else:
                        st.error("❌ Credenciales incorrectas o usuario no encontrado.")
            
            # Botón de Olvidé mi contraseña
            st.markdown("---")
            if st.button("¿Olvidaste tu contraseña?", type="secondary"):
                st.session_state["show_recovery"] = True
                st.rerun()

        if st.session_state.get("show_verification"):
           pass # Ya se mostró arriba


        with tab_register:
            st.info("Solo se permiten correos @ipn.mx o @alumno.ipn.mx para el registro.")
            with st.form("register_form"):
                new_name = st.text_input("Nombre Completo")
                new_email = st.text_input("Correo Institucional", placeholder="usuario@alumno.ipn.mx")
                new_pass = st.text_input("Contraseña", type="password", key="reg_pass")
                confirm_pass = st.text_input("Confirmar Contraseña", type="password", key="reg_confirm")
                new_role = st.selectbox("Rol", ["Investigador", "Estudiante"], key="reg_role")
                
                # Reintegrar checkbox solo para registro
                aceptar_aviso_reg = st.checkbox("Acepto el Aviso de Privacidad", key="reg_aviso")
                
                # Mostrar aviso en expander aquí mismo
                with st.expander("📄 Ver Aviso de Privacidad"):
                    st.markdown(PRIVACY_NOTICE)
                    
                reg_submitted = st.form_submit_button("CREAR CUENTA")

            if reg_submitted:
                if not aceptar_aviso_reg:
                    st.error("⚠️ Debes aceptar el Aviso de Privacidad para crear una cuenta.")
                elif not (new_email.endswith("@ipn.mx") or new_email.endswith("@alumno.ipn.mx")):
                    st.error("❌ El correo debe ser institucional (@ipn.mx o @alumno.ipn.mx).")
                elif new_pass != confirm_pass:
                    st.error("❌ Las contraseñas no coinciden.")
                elif len(new_pass) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                else:
                    success, msg = register_user(new_email, new_pass, new_role, new_name)
                    if success:
                        st.success(f"✅ {msg}")
                        # Auto-mostrar pantalla de verificación
                        st.session_state["pending_email"] = new_email
                        st.session_state["show_verification"] = True
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    # Pie de página
    st.markdown(
        '<div style="text-align:center; margin-top:15px; '
        'font-size:0.85rem; color:var(--text-sub); font-weight: 500;">'
        "Escuela Superior de Cómputo - Instituto Politécnico Nacional © 2026"
        "</div>",
        unsafe_allow_html=True,
    )
