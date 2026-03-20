"""
test_security_logger.py — Tests Unitarios del Módulo de Logging de Seguridad
TT Ratones 2026 | ESCOM - IPN
"""

import sys
import os
import logging
import unittest
from unittest.mock import MagicMock, patch

# Asegurar que el entorno de test tenga los mocks necesarios
sys.modules['streamlit'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Agregar raíz del proyecto
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import src.security_logger as sl

class TestSecurityLogger(unittest.TestCase):

    def setUp(self):
        sl.security_logger.handlers = []
        self.log_records = []
        
        class CapturingHandler(logging.Handler):
            def emit(selfs, record):
                self.log_records.append(record)
        
        self.handler = CapturingHandler()
        sl.security_logger.addHandler(self.handler)

    def test_log_security_event_calls_db_internal(self):
        """Verifica que log_security_event llame a la persistencia interna."""
        with patch("src.security_logger._log_to_db") as mock_db:
            sl.log_security_event("LOGIN_SUCCESS", user="test@ipn.mx", message="Test")
            mock_db.assert_called_once()
            self.assertTrue(any("LOGIN_SUCCESS" in rec.msg for rec in self.log_records))

    @patch("src.db.connection.get_db_engine")
    def test_log_to_db_behavior(self, mock_get_engine):
        """Verifica que _log_to_db maneje correctamente la conexión a la BD."""
        # Caso 1: Motor no disponible
        mock_get_engine.return_value = None
        sl._log_to_db("EV", "u", "m")
        
        # Caso 2: Error en ejecución
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_engine.begin.side_effect = Exception("Conn Error")
        
        try:
            sl._log_to_db("EV", "u", "m")
        except Exception as e:
            self.fail(f"_log_to_db propagó una excepción: {e}")

    def test_log_levels_mapping(self):
        """Verifica que los niveles de severidad se asignen correctamente."""
        with patch("src.security_logger._log_to_db"):
            sl.log_security_event("CRITICAL_ERR", level="CRITICAL")
            self.assertEqual(self.log_records[-1].levelno, logging.CRITICAL)

if __name__ == '__main__':
    unittest.main()
