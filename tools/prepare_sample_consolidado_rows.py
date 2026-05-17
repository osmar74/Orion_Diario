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


def main():
    nombre_conexion, cfg = obtener_configuracion()

    print("====================================================")
    print("PREPARACIÓN DE DATOS PARA CONSOLIDADO")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")
    print("====================================================")

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cursor = conn.cursor()

        print("Actualizando Discador...")
        cursor.execute(
            """
            UPDATE dbo.Discador
            SET
                Categoria = ?,
                Subcategoria = ?,
                Resultado = ?,
                EstadoActualContacto = ?
            WHERE Lote = ?
              AND NroCliente_Contrato = ?
              AND NumeroTelefonico = ?
            """,
            [
                " Contacto",
                " Acuerdo De Pago",
                " OK",
                " Contactada",
                "LOTE_PRUEBA_01",
                "CLI001",
                76543210,
            ],
        )
        discador_1 = cursor.rowcount

        cursor.execute(
            """
            UPDATE dbo.Discador
            SET
                Categoria = ?,
                Subcategoria = ?,
                Resultado = ?,
                EstadoActualContacto = ?
            WHERE Lote = ?
              AND NroCliente_Contrato = ?
              AND NumeroTelefonico = ?
            """,
            [
                " Contacto",
                " Acuerdo De Pago",
                " OK",
                " Contactada",
                "LOTE_PRUEBA_01",
                "CLI002",
                76543211,
            ],
        )
        discador_2 = cursor.rowcount

        print("Actualizando Causales...")
        cursor.execute(
            """
            UPDATE dbo.Causales
            SET
                Tipo_de_evento = ?,
                Categoria = ?,
                Subcategoria = ?,
                Codigo = ?,
                Fecha_de_compromiso = ?,
                Usuario = ?,
                Causal_de_mora = ?
            WHERE Comentario = ?
              AND Telefono_utilizado = ?
            """,
            [
                "Categorización",
                " Contacto",
                " Acuerdo De Pago",
                "CLI001",
                "2026-05-20",
                "1001-JUAN",
                "PAGO",
                "Prueba controlada causales 1",
                76543210,
            ],
        )
        causales_1 = cursor.rowcount

        cursor.execute(
            """
            UPDATE dbo.Causales
            SET
                Tipo_de_evento = ?,
                Categoria = ?,
                Subcategoria = ?,
                Codigo = ?,
                Fecha_de_compromiso = ?,
                Usuario = ?,
                Causal_de_mora = ?
            WHERE Comentario = ?
              AND Telefono_utilizado = ?
            """,
            [
                "Categorización",
                " Contacto",
                " Acuerdo De Pago",
                "CLI002",
                "2026-05-21",
                "1002-MARIA",
                "PAGO",
                "Prueba controlada causales 2",
                76543211,
            ],
        )
        causales_2 = cursor.rowcount

        conn.commit()

    print("====================================================")
    print("RESUMEN DE ACTUALIZACIÓN")
    print("====================================================")
    print(f"Discador CLI001 actualizados: {discador_1}")
    print(f"Discador CLI002 actualizados: {discador_2}")
    print(f"Causales CLI001 actualizados: {causales_1}")
    print(f"Causales CLI002 actualizados: {causales_2}")

    if all(valor == 1 for valor in [discador_1, discador_2, causales_1, causales_2]):
        print("✅ DATOS DE PRUEBA PREPARADOS PARA CONSOLIDADO")
    else:
        print("⚠️ Algún registro no fue actualizado. Revisa conteos antes de continuar.")


if __name__ == "__main__":
    main()