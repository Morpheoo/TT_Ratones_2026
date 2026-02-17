@echo off
cd /d "%~dp0"
call venv_310\Scripts\activate.bat
echo Starting SimBA GUI...
simba
pause
