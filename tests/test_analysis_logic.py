import sys
import os
import unittest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis_logic import checar_zona, detectar_grooming, detectar_thigmotaxis

class TestAnalysisLogic(unittest.TestCase):

    def setUp(self):
        """
        Setup standard EPM configuration before each test.
        """
        self.zonas = [
            {"Nombre Zona": "Centro", "left": 200, "top": 200, "width": 100, "height": 100},
            {"Nombre Zona": "Brazo Abierto Izq", "left": 100, "top": 200, "width": 100, "height": 100},
            {"Nombre Zona": "Brazo Cerrado Sup", "left": 200, "top": 100, "width": 100, "height": 100},
        ]

    # --- TESTS: checar_zona ---
    
    def test_checar_zona_dentro(self):
        self.assertEqual(checar_zona((250, 250), self.zonas), "Centro")
        self.assertEqual(checar_zona((150, 250), self.zonas), "Brazo Abierto Izq")
        self.assertEqual(checar_zona((250, 150), self.zonas), "Brazo Cerrado Sup")

    def test_checar_zona_borde(self):
        # Test EXACT edge (should be inclusive)
        # 200 is left edge of Center, and right edge of Open Arm.
        # Function returns the first match in list. Center is first.
        self.assertIn(checar_zona((200, 200), self.zonas), ["Centro", "Brazo Abierto Izq"])
        # Pure left edge of Open Arm
        self.assertEqual(checar_zona((100, 250), self.zonas), "Brazo Abierto Izq")

    def test_checar_zona_fuera(self):
        self.assertEqual(checar_zona((99, 250), self.zonas), "Fuera del Laberinto")
        self.assertEqual(checar_zona((500, 500), self.zonas), "Fuera del Laberinto")

    # --- TESTS: detectar_grooming ---

    def test_grooming_detectado(self):
        self.assertTrue(detectar_grooming((100,100), (100,100), velocity_px_s=0.0))
        self.assertTrue(detectar_grooming((100,100), (100,110), velocity_px_s=10.0))

    def test_no_grooming_velocidad_alta(self):
        self.assertFalse(detectar_grooming((100,100), (100,100), velocity_px_s=50.0))

    def test_no_grooming_estirado(self):
        self.assertFalse(detectar_grooming((100,100), (100,200), velocity_px_s=0.0))

    # --- TESTS: detectar_thigmotaxis ---

    def test_thigmotaxis_positivo(self):
        # In Closed Arm, near Left Wall (x=200, left=200). 
        self.assertTrue(detectar_thigmotaxis((205, 150), "Brazo Cerrado Sup", self.zonas))

    def test_thigmotaxis_negativo_centro_brazo(self):
        # In Closed Arm, but in the middle
        self.assertFalse(detectar_thigmotaxis((250, 150), "Brazo Cerrado Sup", self.zonas))

    def test_thigmotaxis_negativo_zona_abierta(self):
        self.assertFalse(detectar_thigmotaxis((105, 250), "Brazo Abierto Izq", self.zonas))

if __name__ == '__main__':
    unittest.main()
