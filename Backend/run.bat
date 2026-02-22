@echo off
REM -- Nos situamos en esta carpeta
cd /d "%~dp0"

REM -- Activamos el virtualenv
call venv\Scripts\activate

REM -- Instalamos dependencias (si es la primera vez o cambiaste requirements.txt)
pip install -r requirements.txt

REM -- Abrimos el navegador
start http://127.0.0.1:5000/

REM -- Arrancamos Flask
python app.py

REM -- Pausa al terminar para que veas mensajes
pause
