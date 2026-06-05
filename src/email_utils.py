import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import streamlit as st

def send_verification_email(to_email, code):
    """
    Sends a verification code to the specified email address.
    Returns (True, Message) if successful, (False, Error) otherwise.
    """
    # Configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    from dotenv import load_dotenv
    load_dotenv(override=False)
    sender_email = os.environ.get("GMAIL_SENDER_EMAIL", "").strip()
    
    # We try to get the password from Streamlit secrets or env var
    try:
        sender_password = st.secrets.get("GMAIL_APP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", "")).strip()
    except:
        sender_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    
    # Fallback de desarrollo: si las credenciales SMTP no estan configuradas,
    # imprimir el OTP en consola para no bloquear el registro durante setup
    # inicial. En produccion deberian estar siempre presentes en .env.
    placeholders = {
        "",
        "your_email@gmail.com",
        "tu_email@gmail.com",
        "your_app_password",
        "tu_app_password",
    }
    if sender_email in placeholders or sender_password in placeholders:
        print("")
        print("=" * 60)
        print("[DEV-OTP] SMTP no configurado. Codigo de verificacion:")
        print(f"[DEV-OTP]   destinatario : {to_email}")
        print(f"[DEV-OTP]   codigo OTP   : {code}")
        print("[DEV-OTP] Ingresalo en la UI para completar el registro.")
        print("[DEV-OTP] Para enviar mails reales, configura")
        print("[DEV-OTP]   GMAIL_SENDER_EMAIL y GMAIL_APP_PASSWORD en .env")
        print("=" * 60)
        print("")
        return True, "OTP impreso en consola (modo dev sin SMTP)."

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Código de Verificación - TT Ratones 2026"

        body = f"""
        <html>
          <body>
            <h2>Verificación de Cuenta</h2>
            <p>Hola,</p>
            <p>Tu código de verificación para el prototipo TT Ratones 2026 es:</p>
            <h1 style="color: #2e7d32; font-size: 32px;">{code}</h1>
            <p>Ingresa este código en la aplicación para activar tu cuenta.</p>
            <p>Si no solicitaste este código, ignora este mensaje.</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        # Connect to server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        
        return True, "Correo enviado correctamente."
        
    except Exception as e:
        return False, f"Error al enviar correo: {e}"
