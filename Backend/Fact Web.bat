@echo off
REM -- Sitúate en la carpeta donde está este .bat
cd /d "%~dp0"

REM -- Activa el virtualenv
call venv\Scripts\activate

REM -- Arranca la app con pythonw del propio venv (sin consola)
start "" "%~dp0venv\Scripts\pythonw.exe" app.py

REM -- Dale un par de segundos para que Flask levante el servidor
timeout /t 2 >nul

REM -- Abre el navegador en la URL correcta
start "" http://127.0.0.1:5000/

exit
