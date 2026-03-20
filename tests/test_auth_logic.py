import sys
import os
import unittest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth import hash_password, check_password, validate_ipn_domain, check_admin_access

class TestAuthLogic(unittest.TestCase):

    def test_hash_password(self):
        """Test that hashing is secure and verifiable."""
        p1 = "secret123"
        h1 = hash_password(p1)
        self.assertNotEqual(p1, h1)
        self.assertTrue(check_password(p1, h1))
        self.assertFalse(check_password("wrong", h1))
        self.assertTrue(len(h1) > 10)

    def test_validate_domain(self):
        """Test IPN domain validation."""
        self.assertTrue(validate_ipn_domain("student@ipn.mx"))
        self.assertTrue(validate_ipn_domain("prof@alumno.ipn.mx"))
        self.assertFalse(validate_ipn_domain("hacker@gmail.com"))
        self.assertFalse(validate_ipn_domain("admin@yahoo.com"))

    def test_check_admin_access(self):
        """Test Role Guards."""
        self.assertTrue(check_admin_access("admin"))
        self.assertFalse(check_admin_access("investigador"))
        self.assertFalse(check_admin_access("estudiante"))
        self.assertFalse(check_admin_access(None))

if __name__ == '__main__':
    unittest.main()
