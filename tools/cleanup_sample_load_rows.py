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


def ejecutar_delete(cursor, nombre, sql, parametros):
    cursor.execute(sql, parametros)
    afectados = cursor.rowcount
    print(f"{nombre}: {afectados} registros eliminados")
    return afectados


def main():
    nombre_conexion, cfg = obtener_configuracion()

    print("====================================================")
    print("LIMPIEZA DE REGISTROS DE PRUEBA")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")
    print("====================================================")

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cursor = conn.cursor()

        ejecutar_delete(
            cursor,
            "Discador prueba",
            """
            DELETE FROM dbo.Discador
            WHERE Lote = ?
              AND NroCliente_Contrato IN (?, ?)
            """,
            ["LOTE_PRUEBA_01", "CLI001", "CLI002"],
        )

        ejecutar_delete(
            cursor,
            "Causales prueba",
            """
            DELETE FROM dbo.Causales
            WHERE Comentario LIKE ?
            """,
            ["Prueba controlada causales%"],
        )

        ejecutar_delete(
            cursor,
            "Lote prueba",
            """
            DELETE FROM dbo.Lote
            WHERE Nombre_Lote = ?
              AND codigo_cliente IN (?, ?)
            """,
            ["LOTE_PRUEBA_01", "CLI001", "CLI002"],
        )

        conn.commit()

    print("====================================================")
    print("✅ LIMPIEZA COMPLETADA")
    print("====================================================")


if __name__ == "__main__":
    main()