import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.email_utils import send_verification_email

class TestEmailMock(unittest.TestCase):

    @patch("src.email_utils.smtplib.SMTP")
    @patch("src.email_utils.st.secrets")
    def test_send_email_success(self, mock_secrets, mock_smtp):
        """
        Test that email sending logic calls the correct SMTP methods when password is valid.
        """
        # 1. Mock Secrets to return a fake password
        mock_secrets.get.return_value = "fake_password_123"

        # 2. Mock SMTP server instance
        mock_server_instance = MagicMock()
        mock_smtp.return_value = mock_server_instance

        # 3. Call Function
        to_email = "test@student.ipn.mx"
        code = "123456"
        success, msg = send_verification_email(to_email, code)

        # 4. Assertions
        self.assertTrue(success)
        self.assertIn("Correo enviado", msg)
        
        # Verify SMTP interactions
        mock_smtp.assert_called_with("smtp.gmail.com", 587)
        mock_server_instance.starttls.assert_called_once()
        mock_server_instance.login.assert_called_with("chavid04@gmail.com", "fake_password_123")
        mock_server_instance.sendmail.assert_called_once()
        mock_server_instance.quit.assert_called_once()

    @patch("src.email_utils.st.secrets")
    def test_send_email_no_password(self, mock_secrets):
        """
        Test properly handling missing password.
        """
        # Mock secrets to return None or empty
        mock_secrets.get.return_value = ""

        success, msg = send_verification_email("someone@ipn.mx", "000000")
        
        self.assertFalse(success)
        self.assertIn("Falta la contraseña", msg)

if __name__ == '__main__':
    unittest.main()
