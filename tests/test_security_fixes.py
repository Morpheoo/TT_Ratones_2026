import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock streamlit
sys.modules['streamlit'] = MagicMock()
sys.modules['streamlit'].secrets = {} # Ensure secrets dict exists if accessed

# Import auth after mocking
# We need to make sure auth can import db.connection
# db.connection imports os, sqlalchemy... should be fine.
from auth import register_user, hash_password, check_password

class TestSecurityFixes(unittest.TestCase):
    def test_bcrypt_hashing(self):
        password = "secure_password"
        hashed = hash_password(password)
        self.assertNotEqual(hashed, password)
        self.assertTrue(check_password(password, hashed))
        self.assertFalse(check_password("wrong_password", hashed))

    @patch("auth.get_db_engine")
    @patch("auth.send_verification_email")
    def test_register_rollback_on_email_failure(self, mock_send_email, mock_get_engine):
        # Setup mocks
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock transaction context
        mock_trans = MagicMock()
        mock_conn.begin.return_value.__enter__.return_value = mock_trans
        
        # Mock checks (select returns None -> user not found)
        mock_conn.execute.return_value.fetchone.return_value = None 
        
        # Simulate email failure
        mock_send_email.return_value = (False, "SMTP Timeout")
        
        # Call register
        email = "test@ipn.mx"
        success, msg = register_user(email, "password", "user", "Test User")
        
        # Assert
        self.assertFalse(success)
        self.assertIn("Error en registro", msg)
        self.assertIn("SMTP Timeout", msg)
        
        # Verify insert was called
        self.assertGreaterEqual(mock_conn.execute.call_count, 2)
        
        # Verify email was attempted
        mock_send_email.assert_called_once()
        
        # Verify transaction exit (rollback)
        mock_conn.begin.return_value.__exit__.assert_called()

if __name__ == '__main__':
    unittest.main()
