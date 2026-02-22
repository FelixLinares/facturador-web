@echo off
REM -- Sitúate en la carpeta donde está el .bat
cd /d "%~dp0"

REM -- Activa el entorno virtual (suprime la salida)
call venv\Scripts\activate >nul 2>&1

REM -- Lanza tu app con pythonw (sin ventana de consola)
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0app.py"

REM -- Abre automáticamente el navegador tras un par de segundos
ping 127.0.0.1 -n 2 >nul
start "" http://127.0.0.1:5000/

exit
