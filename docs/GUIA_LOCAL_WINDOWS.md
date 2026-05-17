# Guía local Windows — Orion Diario

## 1. Ruta oficial del proyecto

```text
D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario

2. Requisitos instalados

El proyecto requiere:

Windows 11
Visual Studio Code
Command Prompt de VSCode
Python 3.12
Git
Tesseract OCR
SQL Server
ODBC Driver 17 o 18 for SQL Server
3. Entorno virtual

Para activar manualmente:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat

También se puede usar:

scripts\activar_entorno.bat
4. Variables de entorno

El proyecto usa:

.env

Este archivo no debe subirse a Git.

La plantilla versionada es:

.env.example

Si se instala el proyecto en otra PC:

copy .env.example .env
code .env

Luego completar usuario, contraseña, servidor SQL y ruta de Tesseract.

5. Ejecutar health check

Comando recomendado:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
scripts\health_check.bat

También se puede ejecutar directo:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\health_check.py

Resultado esperado:

✅ HEALTH CHECK COMPLETADO CORRECTAMENTE
6. Ejecutar Flask localmente

Comando recomendado:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
scripts\run_local.bat

También se puede ejecutar directo:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python run.py

Abrir en navegador:

http://127.0.0.1:5000

Para detener Flask:

CTRL + C
7. Validar OCR

Prueba directa:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\test_ocr_smoke.py

Resultado esperado:

✅ PRUEBA OCR EXITOSA
8. Validar SQL Server

Prueba de conexión:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\test_sql_connection.py

Prueba de esquema:

python tools\test_sql_schema.py

Resultado esperado:

SQL_LOCAL: OK
SQL_REMOTO: OK
9. Crear archivos Excel de prueba
cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\create_sample_load_files.py

Archivos generados:

data\orion_202605_12\Causales\Causales_Consolidado_Prueba.xlsx
data\orion_202605_12\Lotes\Lote_Consolidado_Prueba.xlsx
data\orion_202605_12\discador_Prueba_Consolidado.xlsx
10. Limpiar registros de prueba
cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\cleanup_sample_load_rows.py local

Validar conteos:

python tools\check_sample_load_counts.py local

Resultado limpio:

Causales prueba: 0
Lote prueba: 0
Discador prueba: 0
11. Insertar datos de prueba local

Primero levantar Flask:

scripts\run_local.bat

En otra terminal:

cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
curl.exe -X POST -F "tipo=causales" -F "conexion=local" http://127.0.0.1:5000/accion/insertar-datos
curl.exe -X POST -F "tipo=lote" -F "conexion=local" http://127.0.0.1:5000/accion/insertar-datos
curl.exe -X POST -F "tipo=discador" -F "conexion=local" http://127.0.0.1:5000/accion/insertar-datos

Validar:

python tools\check_sample_load_counts.py local

Resultado esperado:

Causales prueba: 2
Lote prueba: 2
Discador prueba: 2
12. Preparar datos para consolidado
cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\prepare_sample_consolidado_rows.py local

Resultado esperado:

✅ DATOS DE PRUEBA PREPARADOS PARA CONSOLIDADO
13. Probar consolidado local
cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario
venv\Scripts\activate.bat
python tools\test_consolidado_query.py local

Resultado esperado:

✅ CONSULTA CONSOLIDADO EJECUTADA

Archivo generado:

data\consolidado_test_20260512.xlsx
14. Probar exportación final desde Flask

Primero ejecutar:

scripts\run_local.bat

Luego consultar consolidado:

curl.exe -X POST -F "fecha=2026-05-12" -F "meses=202605" -F "conexion=local" http://127.0.0.1:5000/accion/consolidar-consulta -o data\consolidado_consulta_export.html

Buscar temporal:

dir data\temp_consolidado_*.pkl

Aplicar exportación, reemplazando AQUI_TU_TEMP_ID:

curl.exe -X POST -F "fecha=2026-05-12" -F "seleccionados=[]" -F "temp_id=AQUI_TU_TEMP_ID" http://127.0.0.1:5000/accion/consolidar-aplicar

Archivo esperado:

data\20260512_Gestion_orion.xlsx
15. Estado de Git

Revisar estado:

git status

Resultado esperado:

On branch dev
nothing to commit, working tree clean

Ver tags:

git tag
16. Punto estable actual

Punto estable recomendado:

local-working-v1

Este tag representa el estado donde funciona:

Flask
OCR
SQL local/remoto
Carga Excel
Consolidado
Exportación Excel
Scripts .bat
.env
Health check

---

## e. Comandos exactos para Command Prompt

Entra al proyecto:

```cmd
cd D:\Develop\ETL\Nicaragua_Proceso\Orion_Diario

Activa el entorno:

venv\Scripts\activate.bat

Crea la carpeta docs:

mkdir docs

Crea el archivo:

type nul > docs\GUIA_LOCAL_WINDOWS.md

Ábrelo:

code docs\GUIA_LOCAL_WINDOWS.md

Pega el contenido completo de la sección anterior y guarda.

Verifica Git:

git status

Agrega la documentación:

git add docs\GUIA_LOCAL_WINDOWS.md

Haz commit:

git commit -m "Add local Windows setup guide"

Verifica estado:

git status

Crea el tag estable:

git tag local-working-v1

Verifica tags:

git tag

Verifica el commit asociado al tag:

git show local-working-v1 --stat

Estado final:

git status