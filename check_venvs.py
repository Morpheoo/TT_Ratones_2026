"""
Script de verificación rápida de entornos virtuales
Ejecutar desde la raíz del proyecto: python check_venvs.py
"""
import subprocess
import os

def check_package(python_exe, package_name):
    """Verifica si un paquete está instalado"""
    try:
        result = subprocess.run(
            [python_exe, "-c", f"import {package_name}; print({package_name}.__version__)"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, "Error"

print("="*60)
print("VERIFICACIÓN DE ENTORNOS VIRTUALES")
print("="*60)

# venv_311
print("\n🔷 venv_311 (Python 3.11 - Aplicación Principal)")
print("-"*60)
venv_311_python = "venv_311\\Scripts\\python.exe"
if os.path.exists(venv_311_python):
    version = subprocess.check_output([venv_311_python, "--version"], text=True).strip()
    print(f"✓ {version}")
    
    packages = ["streamlit", "pandas", "numpy", "ultralytics", "torch"]
    for pkg in packages:
        ok, ver = check_package(venv_311_python, pkg)
        status = "✓" if ok else "❌"
        print(f"  {status} {pkg:15s} {ver if ok else 'NO instalado'}")
else:
    print("❌ venv_311 NO EXISTE")

# venv_310
print("\n🔶 venv_310 (Python 3.10 - DeepLabCut)")
print("-"*60)
venv_310_python = "venv_310\\Scripts\\python.exe"
if os.path.exists(venv_310_python):
    version = subprocess.check_output([venv_310_python, "--version"], text=True).strip()
    print(f"✓ {version}")
    
    packages = ["deeplabcut", "tensorflow", "numpy"]
    for pkg in packages:
        ok, ver = check_package(venv_310_python, pkg)
        status = "✓" if ok else "❌"
        print(f"  {status} {pkg:15s} {ver if ok else 'NO instalado'}")
else:
    print("❌ venv_310 NO EXISTE")

print("\n" + "="*60)
