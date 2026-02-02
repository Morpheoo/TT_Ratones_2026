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
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    sender_email = os.getenv("GMAIL_SENDER_EMAIL")
    # We try to get the password from Streamlit secrets or env var, fallback to empty string
    sender_password = st.secrets.get("GMAIL_APP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", ""))
    
    if not sender_email:
        return False, "Falta configurar el correo remitente (GMAIL_SENDER_EMAIL)."

    if not sender_password:
        return False, "Falta la contraseña de aplicación (GMAIL_APP_PASSWORD)."

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
            <p>Tu código de verificación para el sistema TT Ratones 2026 es:</p>
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
