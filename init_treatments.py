"""
Script para inicializar la tabla de tratamientos en la base de datos
"""
import sys
import os

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from treatments import initialize_treatments_table, get_all_treatments

if __name__ == "__main__":
    print("[INFO] Inicializando tabla de tratamientos...")
    success = initialize_treatments_table()
    
    if success:
        print("[OK] Tabla de tratamientos creada exitosamente")
        
        treatments = get_all_treatments()
        print(f"\n[INFO] Tratamientos disponibles ({len(treatments)}):")
        for t in treatments:
            print(f"  - {t['name']}")
        
        print("\n[OK] Sistema de tratamientos listo para usar")
    else:
        print("[ERROR] No se pudo crear la tabla de tratamientos")
