@echo off
cd /d D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario

if not exist venv\Scripts\activate.bat (
    echo.
    echo ERROR: No se encontro el entorno virtual.
    echo Ruta esperada: venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo Entorno virtual activado.
echo Proyecto: D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
echo.
cmd /k