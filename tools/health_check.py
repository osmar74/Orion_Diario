import os
import platform
import sys
from pathlib import Path

import pyodbc
import pytesseract


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO, TESSERACT_PATH
from app.controllers.helpers import construir_cadena_conexion, obtener_driver_sql_server


def imprimir_titulo(titulo):
    print()
    print("====================================================")
    print(titulo)
    print("====================================================")


def ok(mensaje):
    print(f"✅ {mensaje}")


def fallo(mensaje):
    print(f"❌ {mensaje}")


def advertencia(mensaje):
    print(f"⚠️ {mensaje}")


def validar_python():
    imprimir_titulo("1. PYTHON Y PROYECTO")

    print(f"Python: {sys.version}")
    print(f"Sistema: {platform.platform()}")
    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")

    if ROOT_DIR.exists():
        ok("Ruta raíz del proyecto existe.")
    else:
        fallo("Ruta raíz del proyecto no existe.")

    if Path(DATA_DIR).exists():
        ok("Carpeta data existe.")
    else:
        advertencia("Carpeta data no existe.")


def validar_env():
    imprimir_titulo("2. VARIABLES DE ENTORNO")

    env_path = ROOT_DIR / ".env"
    env_example_path = ROOT_DIR / ".env.example"

    if env_path.exists():
        ok(".env existe localmente.")
    else:
        advertencia(".env no existe. Se usarán valores por defecto.")

    if env_example_path.exists():
        ok(".env.example existe.")
    else:
        fallo(".env.example no existe.")

    print(f"SQL_LOCAL server: {SQL_LOCAL['server']}")
    print(f"SQL_LOCAL database: {SQL_LOCAL['database']}")
    print(f"SQL_LOCAL user: {SQL_LOCAL['username']}")
    print(f"SQL_LOCAL password configurado: {bool(SQL_LOCAL['password'])}")

    print(f"SQL_REMOTO server: {SQL_REMOTO['server']}")
    print(f"SQL_REMOTO alt_server: {SQL_REMOTO.get('alt_server')}")
    print(f"SQL_REMOTO database: {SQL_REMOTO['database']}")
    print(f"SQL_REMOTO user: {SQL_REMOTO['username']}")
    print(f"SQL_REMOTO password configurado: {bool(SQL_REMOTO['password'])}")


def validar_tesseract():
    imprimir_titulo("3. TESSERACT OCR")

    print(f"TESSERACT_PATH: {TESSERACT_PATH}")

    if not os.path.exists(TESSERACT_PATH):
        fallo("No existe tesseract.exe en la ruta configurada.")
        return False

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    version = pytesseract.get_tesseract_version()

    ok(f"Tesseract disponible. Versión: {version}")
    return True


def validar_odbc():
    imprimir_titulo("4. ODBC SQL SERVER")

    drivers = list(pyodbc.drivers())

    print("Drivers instalados con SQL Server:")
    encontrados = [driver for driver in drivers if "SQL Server" in driver]

    if not encontrados:
        fallo("No se encontró driver ODBC SQL Server.")
        return False

    for driver in encontrados:
        print(f" - {driver}")

    driver = obtener_driver_sql_server()
    ok(f"Driver seleccionado por el proyecto: {driver}")
    return True


def probar_conexion(nombre, cfg):
    print()
    print(f"Probando conexión: {nombre}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")

    try:
        conn_str = construir_cadena_conexion(cfg)

        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    @@SERVERNAME AS servidor,
                    DB_NAME() AS base_actual,
                    SUSER_SNAME() AS usuario
                """
            )
            row = cursor.fetchone()

            ok(f"{nombre} conectado.")
            print(f"Servidor SQL: {row.servidor}")
            print(f"Base actual: {row.base_actual}")
            print(f"Usuario: {row.usuario}")
            return True

    except Exception as exc:
        fallo(f"{nombre} falló.")
        print(exc)
        return False


def validar_sql():
    imprimir_titulo("5. CONEXIONES SQL SERVER")

    local_ok = probar_conexion("SQL_LOCAL", SQL_LOCAL)
    remoto_ok = probar_conexion("SQL_REMOTO", SQL_REMOTO)

    return local_ok and remoto_ok


def validar_flask():
    imprimir_titulo("6. FLASK APP")

    try:
        app = create_app()
        ok("Aplicación Flask creada correctamente.")
        print(f"Nombre app: {app.name}")
        print(f"Blueprints: {list(app.blueprints.keys())}")
        return True

    except Exception as exc:
        fallo("No se pudo crear la aplicación Flask.")
        print(exc)
        return False


def validar_conteos_prueba():
    imprimir_titulo("7. CONTEOS DE REGISTROS DE PRUEBA LOCAL")

    try:
        conn_str = construir_cadena_conexion(SQL_LOCAL)

        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()

            consultas = {
                "Causales prueba": """
                    SELECT COUNT(*)
                    FROM dbo.Causales
                    WHERE Comentario LIKE 'Prueba controlada causales%'
                """,
                "Lote prueba": """
                    SELECT COUNT(*)
                    FROM dbo.Lote
                    WHERE Nombre_Lote = 'LOTE_PRUEBA_01'
                      AND codigo_cliente IN ('CLI001', 'CLI002')
                """,
                "Discador prueba": """
                    SELECT COUNT(*)
                    FROM dbo.Discador
                    WHERE Lote = 'LOTE_PRUEBA_01'
                      AND NroCliente_Contrato IN ('CLI001', 'CLI002')
                """,
            }

            for nombre, sql in consultas.items():
                cursor.execute(sql)
                total = cursor.fetchone()[0]
                print(f"{nombre}: {total}")

        ok("Conteos de prueba consultados correctamente.")
        return True

    except Exception as exc:
        advertencia("No se pudieron consultar conteos de prueba.")
        print(exc)
        return False


def main():
    resultados = []

    validar_python()
    validar_env()
    resultados.append(validar_tesseract())
    resultados.append(validar_odbc())
    resultados.append(validar_sql())
    resultados.append(validar_flask())
    validar_conteos_prueba()

    imprimir_titulo("RESUMEN FINAL")

    if all(resultados):
        ok("HEALTH CHECK COMPLETADO CORRECTAMENTE")
        raise SystemExit(0)

    fallo("HEALTH CHECK CON OBSERVACIONES")
    raise SystemExit(1)


if __name__ == "__main__":
    main()