@echo off
cd /d "%~dp0"

echo [START] Levantando Base de Datos (Docker) en 2do plano...
docker-compose up -d >nul 2>&1

call venv_311\Scripts\activate.bat
streamlit run Home.py
pause
