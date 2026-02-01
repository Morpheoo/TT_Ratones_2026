@echo off
cd /d "%~dp0"
call venv_311\Scripts\activate.bat
streamlit run Home.py
pause
