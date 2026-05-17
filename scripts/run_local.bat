@echo off
cd /d D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario

if not exist venv\Scripts\activate.bat (
    echo.
    echo ERROR: No se encontro el entorno virtual.
    echo Ejecuta primero:
    echo python -m venv venv
    echo.
    pause
    exit /b 1
)

if not exist .env (
    echo.
    echo ERROR: No existe el archivo .env.
    echo Crea .env copiando .env.example y completando tus datos.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo Iniciando Orion Diario en modo local...
echo URL: http://127.0.0.1:5000
echo Presiona CTRL + C para detener Flask.
echo.

python run.py

echo.
echo Servidor detenido.
echo.
pause