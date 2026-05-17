import sys
from pathlib import Path

import pyodbc


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import construir_cadena_conexion


def obtener_configuracion():
    conexion = "local"

    if len(sys.argv) >= 2:
        conexion = sys.argv[1].strip().lower()

    if conexion == "remoto":
        return "remoto", SQL_REMOTO

    return "local", SQL_LOCAL


def contar(cursor, nombre, sql, parametros=None):
    parametros = parametros or []
    cursor.execute(sql, parametros)
    total = cursor.fetchone()[0]
    print(f"{nombre}: {total}")
    return total


def main():
    nombre_conexion, cfg = obtener_configuracion()

    print("====================================================")
    print("CONTEO DE REGISTROS DE PRUEBA")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")
    print("====================================================")

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cursor = conn.cursor()

        total_causales = contar(
            cursor,
            "Causales prueba",
            """
            SELECT COUNT(*)
            FROM dbo.Causales
            WHERE Comentario LIKE ?
            """,
            ["Prueba controlada causales%"],
        )

        total_lote = contar(
            cursor,
            "Lote prueba",
            """
            SELECT COUNT(*)
            FROM dbo.Lote
            WHERE Nombre_Lote = ?
              AND codigo_cliente IN (?, ?)
            """,
            ["LOTE_PRUEBA_01", "CLI001", "CLI002"],
        )

        total_discador = contar(
            cursor,
            "Discador prueba",
            """
            SELECT COUNT(*)
            FROM dbo.Discador
            WHERE Lote = ?
              AND NroCliente_Contrato IN (?, ?)
            """,
            ["LOTE_PRUEBA_01", "CLI001", "CLI002"],
        )

    print("====================================================")
    print("RESUMEN")
    print("====================================================")
    print(f"Causales: {total_causales}")
    print(f"Lote: {total_lote}")
    print(f"Discador: {total_discador}")

    if total_causales == 0 and total_lote == 0 and total_discador == 0:
        print("✅ No existen registros previos de prueba. Puedes insertar.")
    elif total_causales == 2 and total_lote == 2 and total_discador == 2:
        print("✅ Ya existen los 2 registros de prueba por tabla.")
    else:
        print("⚠️ Hay conteos parciales o duplicados. Revisa antes de volver a insertar.")


if __name__ == "__main__":
    main()