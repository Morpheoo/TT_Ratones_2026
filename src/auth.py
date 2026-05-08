import random
import bcrypt
from sqlalchemy import text
from db.connection import get_db_engine
from email_utils import send_verification_email
from security_logger import log_security_event

# ============================================================
# Emails que reciben rol admin automaticamente al registrarse.
# Se comparan en lowercase. Estos usuarios saltean el OTP y
# quedan is_verified=TRUE directamente.
# ============================================================
ADMIN_EMAILS = {
    "careyes@ipn.mx",                       # Dr. Cesar Augusto Sandino Reyes Lopez
    "hportocarreror1700@alumno.ipn.mx",     # Habid Portocarrero Rodriguez
}


def is_admin_email(email: str) -> bool:
    """True si el email esta en la lista de admins predefinidos."""
    return (email or "").strip().lower() in ADMIN_EMAILS

def hash_password(password: str) -> str:
    """Bcrypt hashing."""
    # Hash password with a randomly generated salt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
         return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
         return False

def authenticate(email, password):
    """Authenticate a user against the PostgreSQL database."""
    engine = get_db_engine()
    if not engine:
        log_security_event(
            "DB_ERROR", user=email,
            message="Motor de BD no disponible durante autenticación",
            level="ERROR", success=False
        )
        return None

    try:
        with engine.connect() as conn:
            # Buscar usuario por email (username en el schema es el email)
            # El schema usa 'username' pero el login pide email. Asumimos username = email.
            query = text("SELECT id, username, password_hash, role, full_name FROM users WHERE username = :email")
            result = conn.execute(query, {"email": email}).fetchone()
            
            if result:
                # result: (id, username, password_hash, role, full_name)
                stored_hash = result[2]
                role = result[3]
                # Usar full_name si existe, si no, el username (que es el email)
                name = result[4] if result[4] else result[1] 
                
                if check_password(password, stored_hash):
                    # Verificar si la cuenta está activa (SUSPENSIÓN)
                    check_active = text("SELECT is_active, is_verified FROM users WHERE id = :uid")
                    res_status = conn.execute(check_active, {"uid": result[0]}).fetchone()
                    
                    is_active = res_status[0]
                    is_ver = res_status[1]

                    if is_active is False:
                        log_security_event(
                            "LOGIN_SUSPENDED", user=email,
                            message="Intento de acceso con cuenta suspendida",
                            level="WARNING", success=False
                        )
                        return {"status": "SUSPENDED", "email": email}

                    if is_ver is None: # Si por alguna razón es NULL, asumimos False o legacy
                        is_ver = False
                        
                    if not is_ver:
                        log_security_event(
                            "LOGIN_NOT_VERIFIED", user=email,
                            message="Intento de acceso con cuenta no verificada",
                            level="INFO", success=False
                        )
                        return {"status": "NOT_VERIFIED", "email": email}
                    
                    log_security_event(
                        "LOGIN_SUCCESS", user=email,
                        message=f"Login exitoso. Rol: {role}",
                        level="INFO", success=True
                    )
                    return {
                        "name": name,
                        "role": role,
                        "email": email,
                        "status": "ACTIVE"
                    }
                else:
                    log_security_event(
                        "LOGIN_FAILED", user=email,
                        message="Contraseña incorrecta",
                        level="WARNING", success=False
                    )
            else:
                log_security_event(
                    "LOGIN_FAILED", user=email,
                    message="Usuario no encontrado en BD",
                    level="WARNING", success=False
                )

    except Exception as e:
        log_security_event(
            "DB_ERROR", user=email,
            message=f"Error en autenticación BD: {e}",
            level="ERROR", success=False
        )
    
    return None

def validate_ipn_domain(email: str) -> bool:
    """Valida si el correo pertenece al dominio IPN."""
    allowed_domains = ["@ipn.mx", "@alumno.ipn.mx"]
    return any(email.endswith(dom) for dom in allowed_domains)

def check_admin_access(role: str) -> bool:
    """Verifica si el rol tiene acceso al panel de administración."""
    return role == "admin"

def register_user(email, password, role="investigador", full_name=None, boleta=None, carrera=None, escuela=None, accepted_terms=False):
    """Register a new user in the PostgreSQL database with full profile data and pending verification."""
    
    # 0. Validar Términos
    if not accepted_terms:
        return False, "⚠️ Debes aceptar los Términos y Condiciones para registrarte."

    # 1. Validar Dominio IPN
    if not validate_ipn_domain(email):
        log_security_event(
            "REGISTER_FAILED", user=email,
            message="Intento de registro con dominio no IPN",
            level="WARNING", success=False
        )
        return False, "❌ Registro restringido. Debes usar un correo institucional (@ipn.mx o @alumno.ipn.mx)."
        
    engine = get_db_engine()
    if not engine:
        return False, "No hay conexión a la base de datos."

    log_security_event(
        "REGISTER_ATTEMPT", user=email,
        message=f"Intento de registro. Rol solicitado: {role}. Boleta: {boleta}",
        level="INFO", success=True
    )

    try:
        with engine.connect() as conn:
            # 2. Verificar si existe
            check = text("SELECT id FROM users WHERE username = :email")
            if conn.execute(check, {"email": email}).fetchone():
                log_security_event(
                    "REGISTER_FAILED", user=email,
                    message="Usuario ya existe en BD",
                    level="WARNING", success=False
                )
                return False, "⚠️ El usuario ya existe. Si eres tú, intenta Iniciar Sesión para verificar tu cuenta."
            
            # 3. Auto-promocion a admin si el email esta en la lista.
            #    Estos usuarios saltean OTP y quedan verificados directamente.
            auto_admin = is_admin_email(email)
            if auto_admin:
                effective_role = "admin"
                is_verified = True
                otp_code = None
            else:
                effective_role = role
                is_verified = False
                otp_code = str(random.randint(100000, 999999))

            # Start transaction explicitly
            with conn.begin():
                # 4. Insertar con campos extendidos
                insert = text("""
                    INSERT INTO users (
                        username, password_hash, role,
                        is_verified, verification_code, verification_code_created_at,
                        full_name, boleta, carrera, escuela, accepted_terms
                    )
                    VALUES (
                        :email, :pwd, :role,
                        :verified, :otp,
                        CASE WHEN :otp IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END,
                        :fname, :boleta, :carrera, :escuela, :accepted
                    )
                """)

                conn.execute(insert, {
                    "email": email,
                    "pwd": hash_password(password),
                    "role": effective_role,
                    "verified": is_verified,
                    "otp": otp_code,
                    "fname": full_name or email,
                    "boleta": boleta,
                    "carrera": carrera,
                    "escuela": escuela,
                    "accepted": accepted_terms
                })

                # 5. Enviar correo OTP (saltado para admins predefinidos)
                if not auto_admin:
                    sent, msg = send_verification_email(email, otp_code)
                    if not sent:
                        log_security_event(
                            "REGISTER_FAILED", user=email,
                            message=f"Fallo en envío de correo OTP: {msg} — transacción revertida",
                            level="ERROR", success=False
                        )
                        raise Exception(f"Fallo envío de correo: {msg}")

            if auto_admin:
                log_security_event(
                    "REGISTER_SUCCESS", user=email,
                    message="Admin predefinido registrado y verificado automáticamente",
                    level="INFO", success=True
                )
                return True, "✅ Cuenta de administrador creada y verificada. Ya podés iniciar sesión."

            log_security_event(
                "REGISTER_SUCCESS", user=email,
                message=f"Usuario registrado. OTP enviado. Rol: {effective_role}",
                level="INFO", success=True
            )
            return True, "✅ Código de verificación enviado a tu correo IPN."
            
    except Exception as e:
        # If email failed (raised Exception), the DB insert is rolled back.
        return False, f"Error en registro: {e}"

def verify_otp(email, code):
    """Verifica el código OTP y activa la cuenta. Incluye validación de expiración (5 mins)."""
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            # Buscar usuario, código y timestamp
            query = text("SELECT id, verification_code, verification_code_created_at FROM users WHERE username = :email")
            res = conn.execute(query, {"email": email}).fetchone()
            
            if not res:
                return False, "Usuario no encontrado."
                
            db_code = res[1]
            created_at = res[2]
            
            # Validación de expiración (5 minutos)
            if created_at:
                check_time = text("""
                    SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - verification_code_created_at))/60 
                    FROM users WHERE username = :e
                """)
                minutes_passed = conn.execute(check_time, {"e": email}).scalar() or 0
                
                if minutes_passed > 5:
                    log_security_event(
                        "OTP_EXPIRED", user=email,
                        message=f"OTP expirado ({minutes_passed:.1f} minutos desde emisión)",
                        level="WARNING", success=False
                    )
                    return False, "⏳ El código ha expirado (más de 5 mins). Solicita uno nuevo."

            if str(db_code).strip() == str(code).strip():
                # Activar
                update = text("UPDATE users SET is_verified = TRUE, verification_code = NULL WHERE username = :email")
                conn.execute(update, {"email": email})
                conn.commit()
                log_security_event(
                    "OTP_SUCCESS", user=email,
                    message="Cuenta verificada exitosamente mediante OTP",
                    level="INFO", success=True
                )
                return True, "¡Cuenta verificada exitosamente!"
            else:
                log_security_event(
                    "OTP_FAILED", user=email,
                    message="Código OTP incorrecto ingresado",
                    level="WARNING", success=False
                )
                return False, "Código incorrecto."
    except Exception as e:
        return False, f"Error: {e}"

def resend_verification_code(email):
    """Genera un nuevo código y actualiza el timestamp."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # Verificar si existe el usuario primero
            check = text("SELECT id FROM users WHERE username = :email")
            if not conn.execute(check, {"email": email}).fetchone():
                return False, "Usuario no encontrado."

            new_otp = str(random.randint(100000, 999999))
            
            update = text("""
                UPDATE users 
                SET verification_code = :otp, verification_code_created_at = CURRENT_TIMESTAMP 
                WHERE username = :email
            """)
            conn.execute(update, {"otp": new_otp, "email": email})
            conn.commit()
            
            sent, msg = send_verification_email(email, new_otp)
            if sent:
                log_security_event(
                    "OTP_RESENT", user=email,
                    message="Nuevo OTP generado y enviado",
                    level="INFO", success=True
                )
                return True, "✅ Nuevo código enviado."
            else:
                return False, f"Error enviando correo: {msg} (Código debug: {new_otp})"
    except Exception as e:
        return False, f"Error BD: {e}"

def request_password_reset(email):
    """Inicia el proceso de recuperación de contraseña."""
    log_security_event(
        "PASSWORD_RESET_REQUEST", user=email,
        message="Solicitud de restablecimiento de contraseña iniciada",
        level="INFO", success=True
    )
    return resend_verification_code(email) # Reutilizamos la lógica de generar OTP

def reset_password(email, otp, new_password):
    """Verifica OTP y actualiza la contraseña."""
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            # 1. Verificar OTP
            query = text("SELECT verification_code, verification_code_created_at FROM users WHERE username = :email")
            res = conn.execute(query, {"email": email}).fetchone()
            
            if not res:
                return False, "Usuario no encontrado."
            
            db_code = res[0]
            created_at = res[1]
            
            # Checar expiración (reutilizando lógica, idealmente refactorizar en función helper)
            if created_at:
                check_time = text("""
                    SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - verification_code_created_at))/60 
                    FROM users WHERE username = :e
                """)
                minutes_passed = conn.execute(check_time, {"e": email}).scalar() or 0
                if minutes_passed > 5:
                    log_security_event(
                        "OTP_EXPIRED", user=email,
                        message=f"OTP de recuperación expirado ({minutes_passed:.1f} mins)",
                        level="WARNING", success=False
                    )
                    return False, "⏳ El código ha expirado."

            if str(db_code).strip() != str(otp).strip():
                log_security_event(
                    "OTP_FAILED", user=email,
                    message="OTP de recuperación incorrecto",
                    level="WARNING", success=False
                )
                return False, "Código incorrecto."

            # 2. Actualizar Password
            update = text("""
                UPDATE users 
                SET password_hash = :pwd, verification_code = NULL, is_verified = TRUE 
                WHERE username = :email
            """)
            conn.execute(update, {"pwd": hash_password(new_password), "email": email})
            conn.commit()
            
            log_security_event(
                "PASSWORD_RESET_SUCCESS", user=email,
                message="Contraseña actualizada exitosamente",
                level="INFO", success=True
            )
            return True, "✅ Contraseña actualizada exitosamente."
            
    except Exception as e:
        log_security_event(
            "DB_ERROR", user=email,
            message=f"Error al restablecer contraseña: {e}",
            level="ERROR", success=False
        )
        return False, f"Error BD: {e}"

def update_user_profile(email: str, full_name: str):
    """Actualiza el nombre completo (preferred name) del usuario en la base de datos."""
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            update = text("UPDATE users SET full_name = :fname WHERE username = :email")
            conn.execute(update, {"fname": full_name, "email": email})
            conn.commit()
            return True, "✅ Perfil actualizado exitosamente."
    except Exception as e:
        return False, f"Error al actualizar perfil en BD: {e}"

