import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.email_utils import send_verification_email


class TestEmailMock(unittest.TestCase):
    @patch("src.email_utils.smtplib.SMTP")
    @patch("src.email_utils.st.secrets")
    def test_send_email_success(self, mock_secrets, mock_smtp):
        """
        Test that email sending logic calls the correct SMTP methods when password is valid.
        """
        mock_secrets.get.return_value = "fake_password_123"
        mock_server_instance = MagicMock()
        mock_smtp.return_value = mock_server_instance

        with patch.dict(os.environ, {"GMAIL_SENDER_EMAIL": "sender@gmail.com"}, clear=False):
            success, msg = send_verification_email("test@ipn.mx", "123456")

        self.assertTrue(success)
        self.assertIn("Correo enviado", msg)
        mock_smtp.assert_called_with("smtp.gmail.com", 587)
        mock_server_instance.starttls.assert_called_once()
        mock_server_instance.login.assert_called_with("sender@gmail.com", "fake_password_123")
        mock_server_instance.sendmail.assert_called_once()
        mock_server_instance.quit.assert_called_once()

    @patch("src.email_utils.st.secrets")
    def test_send_email_no_password_uses_dev_otp(self, mock_secrets):
        """
        Test setup-friendly fallback when SMTP is not configured.
        """
        mock_secrets.get.return_value = ""

        with patch.dict(
            os.environ,
            {
                "GMAIL_SENDER_EMAIL": "your_email@gmail.com",
                "GMAIL_APP_PASSWORD": "your_app_password",
            },
            clear=False,
        ):
            success, msg = send_verification_email("someone@ipn.mx", "000000")

        self.assertTrue(success)
        self.assertIn("modo dev", msg.lower())


if __name__ == "__main__":
    unittest.main()
