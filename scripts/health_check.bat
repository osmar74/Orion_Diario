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

call venv\Scripts\activate.bat

echo.
echo Ejecutando health check...
echo.

python tools\health_check.py

echo.
echo Health check finalizado.
echo.
pause