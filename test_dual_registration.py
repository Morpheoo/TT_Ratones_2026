"""Script de prueba para verificar que el registro guarda todos los campos correctamente"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.auth import register_user
from src.db.connection import get_db_engine
from sqlalchemy import text
import time

def cleanup_test_user(email):
    """Elimina usuario de prueba"""
    engine = get_db_engine()
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text("DELETE FROM users WHERE username = :email"), {"email": email})
        trans.commit()
    except:
        trans.rollback()
    finally:
        conn.close()

def verify_user_data(email):
    """Verifica los datos guardados en BD"""
    engine = get_db_engine()
    conn = engine.connect()
    result = conn.execute(text("""
        SELECT username, role, full_name, boleta, carrera, escuela, 
               num_empleado, area, centro, accepted_terms
        FROM users WHERE username = :email
    """), {"email": email}).fetchone()
    conn.close()
    return result

def test_student_registration():
    """Prueba registro de estudiante"""
    print("\n=== PRUEBA 1: Registro de Estudiante ===")
    
    test_email = "prueba.estudiante.test999@alumno.ipn.mx"
    
    # Limpiar si existe
    cleanup_test_user(test_email)
    time.sleep(0.5)
    
    # Intentar registro
    success, msg = register_user(
        email=test_email,
        password="TestPass123!",
        role="estudiante",
        full_name="Juan Pérez López",
        boleta="2020630999",
        carrera="Ingeniería en Sistemas Computacionales",
        escuela="ESCOM",
        accepted_terms=True
    )
    
    if success:
        print(f"[OK] Registro exitoso: {msg}")
        time.sleep(0.5)
        
        # Verificar datos guardados
        result = verify_user_data(test_email)
        
        if result:
            print(f"\n[OK] Datos guardados en BD:")
            print(f"  - Email: {result[0]}")
            print(f"  - Rol: {result[1]}")
            print(f"  - Nombre: {result[2]}")
            print(f"  - Boleta: {result[3]}")
            print(f"  - Carrera: {result[4]}")
            print(f"  - Escuela: {result[5]}")
            print(f"  - Num Empleado: {result[6]} (debe ser None)")
            print(f"  - Área: {result[7]} (debe ser None)")
            print(f"  - Centro: {result[8]} (debe ser None)")
            print(f"  - Términos: {result[9]}")
            
            # Limpiar
            cleanup_test_user(test_email)
            print("\n[OK] Registro de prueba eliminado")
        else:
            print("[ERROR] No se encontraron datos en BD")
    else:
        print(f"[ERROR] Registro falló: {msg}")

def test_researcher_registration():
    """Prueba registro de investigador"""
    print("\n\n=== PRUEBA 2: Registro de Investigador/Docente ===")
    
    test_email = "prueba.investigador.test999@ipn.mx"
    
    # Limpiar si existe
    cleanup_test_user(test_email)
    time.sleep(0.5)
    
    # Intentar registro
    success, msg = register_user(
        email=test_email,
        password="TestPass123!",
        role="investigador",
        full_name="Dra. María González Ramírez",
        num_empleado="EMP20230456",
        area="Inteligencia Artificial y análisis de Comportamiento",
        centro="ESCOM",
        accepted_terms=True
    )
    
    if success:
        print(f"[OK] Registro exitoso: {msg}")
        time.sleep(0.5)
        
        # Verificar datos guardados
        result = verify_user_data(test_email)
        
        if result:
            print(f"\n[OK] Datos guardados en BD:")
            print(f"  - Email: {result[0]}")
            print(f"  - Rol: {result[1]}")
            print(f"  - Nombre: {result[2]}")
            print(f"  - Boleta: {result[3]} (debe ser None)")
            print(f"  - Carrera: {result[4]} (debe ser None)")
            print(f"  - Escuela: {result[5]} (debe ser None)")
            print(f"  - Num Empleado: {result[6]}")
            print(f"  - Área: {result[7]}")
            print(f"  - Centro: {result[8]}")
            print(f"  - Términos: {result[9]}")
            
            # Limpiar
            cleanup_test_user(test_email)
            print("\n[OK] Registro de prueba eliminado")
        else:
            print("[ERROR] No se encontraron datos en BD")
    else:
        print(f"[ERROR] Registro falló: {msg}")

if __name__ == "__main__":
    print("="*70)
    print("PRUEBA DE REGISTRO DUAL: ESTUDIANTE E INVESTIGADOR")
    print("="*70)
    
    try:
        test_student_registration()
        test_researcher_registration()
        
        print("\n" + "="*70)
        print("PRUEBAS COMPLETADAS")
        print("="*70)
    except Exception as e:
        print(f"\n[ERROR] Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
