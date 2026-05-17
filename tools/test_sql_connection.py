import sys
from pathlib import Path

import pyodbc


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import SQL_LOCAL, SQL_REMOTO


def obtener_driver_sql_server():
    drivers = list(pyodbc.drivers())

    preferidos = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]

    for driver in preferidos:
        if driver in drivers:
            return driver

    raise RuntimeError(
        "No se encontró un driver ODBC para SQL Server. "
        "Instala ODBC Driver 17 o 18 for SQL Server."
    )


def construir_servidor(config, usar_alternativo=False):
    if usar_alternativo:
        server = config.get("alt_server") or config["server"]
        port = config.get("alt_port", "")
    else:
        server = config["server"]
        port = config.get("port", "")

    if port:
        return f"{server},{port}"

    return server


def construir_connection_string(config, driver, usar_alternativo=False):
    server = construir_servidor(config, usar_alternativo=usar_alternativo)

    partes = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={config['database']}",
        "TrustServerCertificate=yes",
    ]

    if driver == "ODBC Driver 18 for SQL Server":
        partes.append("Encrypt=no")

    if config.get("auth") == "windows":
        partes.append("Trusted_Connection=yes")
    else:
        partes.append(f"UID={config['username']}")
        partes.append(f"PWD={config['password']}")

    return ";".join(partes) + ";"


def probar_conexion(nombre, config, driver, usar_alternativo=False):
    server = construir_servidor(config, usar_alternativo=usar_alternativo)

    print("====================================================")
    print(f"Probando conexión: {nombre}")
    print(f"Servidor: {server}")
    print(f"Base de datos: {config['database']}")
    print(f"Autenticación: {config['auth']}")
    print(f"Usuario: {config.get('username', '')}")
    print(f"Driver: {driver}")
    print("====================================================")

    connection_string = construir_connection_string(
        config=config,
        driver=driver,
        usar_alternativo=usar_alternativo,
    )

    try:
        with pyodbc.connect(connection_string, timeout=8) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    @@SERVERNAME AS servidor,
                    DB_NAME() AS base_datos,
                    SUSER_SNAME() AS usuario
                """
            )
            row = cursor.fetchone()

            print("✅ CONEXIÓN EXITOSA")
            print(f"Servidor SQL: {row.servidor}")
            print(f"Base actual: {row.base_datos}")
            print(f"Usuario conectado: {row.usuario}")
            print()
            return True

    except Exception as exc:
        print("❌ ERROR DE CONEXIÓN")
        print(str(exc))
        print()
        return False


def main():
    print("PRUEBA DE CONEXIÓN SQL SERVER - ORION DIARIO")
    print()

    driver = obtener_driver_sql_server()

    local_ok = probar_conexion(
        nombre="SQL_LOCAL",
        config=SQL_LOCAL,
        driver=driver,
        usar_alternativo=False,
    )

    remoto_ok = probar_conexion(
        nombre="SQL_REMOTO por nombre",
        config=SQL_REMOTO,
        driver=driver,
        usar_alternativo=False,
    )

    if not remoto_ok:
        print("Intentando conexión remota alternativa por IP...")
        remoto_ok = probar_conexion(
            nombre="SQL_REMOTO por IP alternativa",
            config=SQL_REMOTO,
            driver=driver,
            usar_alternativo=True,
        )

    print("====================================================")
    print("RESUMEN")
    print("====================================================")
    print(f"SQL_LOCAL: {'OK' if local_ok else 'FALLÓ'}")
    print(f"SQL_REMOTO: {'OK' if remoto_ok else 'FALLÓ'}")

    if not local_ok or not remoto_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()