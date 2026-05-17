import sys
from pathlib import Path

import pandas as pd
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


def imprimir_df(titulo, df):
    print()
    print("====================================================")
    print(titulo)
    print("====================================================")

    if df.empty:
        print("SIN FILAS")
    else:
        print(df.to_string(index=False))


def leer_sql(conn, sql):
    return pd.read_sql(sql, conn)


def main():
    nombre_conexion, cfg = obtener_configuracion()

    print("====================================================")
    print("INSPECCIÓN DE VALORES PARA CONSOLIDADO")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=30) as conn:
        imprimir_df(
            "1. LONGITUDES DE COLUMNAS CRÍTICAS",
            leer_sql(
                conn,
                """
                SELECT
                    TABLE_NAME,
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME IN ('Discador', 'Causales', 'Lote')
                  AND COLUMN_NAME IN (
                      'Categoria',
                      'Subcategoria',
                      'EstadoActualContacto',
                      'Tipo_de_evento',
                      'Resultado',
                      'Campana',
                      'Lote',
                      'Nombre_Lote',
                      'NroCliente_Contrato',
                      'codigo_cliente',
                      'Codigo',
                      'Usuario',
                      'Comentario',
                      'Causal_de_mora'
                  )
                ORDER BY TABLE_NAME, COLUMN_NAME
                """,
            ),
        )

        imprimir_df(
            "2. VALORES EXACTOS EN DISCADOR DE PRUEBA",
            leer_sql(
                conn,
                """
                SELECT
                    NroCliente_Contrato,
                    FechayHora,
                    NumeroTelefonico,
                    '[' + ISNULL(Lote, '') + ']' AS Lote,
                    LEN(ISNULL(Lote, '')) AS LenLote,
                    '[' + ISNULL(Campana, '') + ']' AS Campana,
                    LEN(ISNULL(Campana, '')) AS LenCampana,
                    Agente,
                    '[' + ISNULL(Categoria, '') + ']' AS Categoria,
                    LEN(ISNULL(Categoria, '')) AS LenCategoria,
                    '[' + ISNULL(Subcategoria, '') + ']' AS Subcategoria,
                    LEN(ISNULL(Subcategoria, '')) AS LenSubcategoria,
                    '[' + ISNULL(Resultado, '') + ']' AS Resultado,
                    LEN(ISNULL(Resultado, '')) AS LenResultado,
                    '[' + ISNULL(EstadoActualContacto, '') + ']' AS EstadoActualContacto,
                    LEN(ISNULL(EstadoActualContacto, '')) AS LenEstado
                FROM dbo.Discador
                WHERE Lote = 'LOTE_PRUEBA_01'
                   OR NroCliente_Contrato IN ('CLI001', 'CLI002')
                ORDER BY NroCliente_Contrato
                """,
            ),
        )

        imprimir_df(
            "3. VALORES EXACTOS EN CAUSALES DE PRUEBA",
            leer_sql(
                conn,
                """
                SELECT
                    Codigo,
                    FechayHora,
                    NroDeAgente,
                    Telefono_utilizado,
                    '[' + ISNULL(Campana, '') + ']' AS Campana,
                    LEN(ISNULL(Campana, '')) AS LenCampana,
                    '[' + ISNULL(Tipo_de_evento, '') + ']' AS TipoDeEvento,
                    LEN(ISNULL(Tipo_de_evento, '')) AS LenTipoEvento,
                    '[' + ISNULL(Categoria, '') + ']' AS Categoria,
                    LEN(ISNULL(Categoria, '')) AS LenCategoria,
                    '[' + ISNULL(Subcategoria, '') + ']' AS Subcategoria,
                    LEN(ISNULL(Subcategoria, '')) AS LenSubcategoria,
                    '[' + ISNULL(Usuario, '') + ']' AS Usuario,
                    '[' + ISNULL(Comentario, '') + ']' AS Comentario
                FROM dbo.Causales
                WHERE Comentario LIKE 'Prueba controlada causales%'
                   OR Codigo IN ('CLI001', 'CLI002')
                ORDER BY Codigo
                """,
            ),
        )

        imprimir_df(
            "4. VALORES EXACTOS EN LOTE DE PRUEBA",
            leer_sql(
                conn,
                """
                SELECT
                    Fecha,
                    phone_number,
                    '[' + ISNULL(Nombre_Lote, '') + ']' AS Nombre_Lote,
                    LEN(ISNULL(Nombre_Lote, '')) AS LenNombreLote,
                    '[' + ISNULL(codigo_cliente, '') + ']' AS codigo_cliente,
                    LEN(ISNULL(codigo_cliente, '')) AS LenCodigoCliente,
                    '[' + ISNULL(segmento, '') + ']' AS segmento,
                    LEN(ISNULL(segmento, '')) AS LenSegmento
                FROM dbo.Lote
                WHERE Nombre_Lote = 'LOTE_PRUEBA_01'
                   OR codigo_cliente IN ('CLI001', 'CLI002')
                ORDER BY codigo_cliente
                """,
            ),
        )

        imprimir_df(
            "5. FILTROS DEL CONSOLIDADO SOBRE DISCADOR",
            leer_sql(
                conn,
                """
                SELECT
                    'Fecha 2026-05-12' AS Filtro,
                    COUNT(*) AS Total
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'

                UNION ALL

                SELECT
                    'Fecha + contrato no vacío',
                    COUNT(*)
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND NroCliente_Contrato IS NOT NULL
                  AND NroCliente_Contrato <> ''

                UNION ALL

                SELECT
                    'Fecha + Estado exacto con espacio',
                    COUNT(*)
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND EstadoActualContacto = ' Contactada'

                UNION ALL

                SELECT
                    'Fecha + Estado sin espacio usando TRIM',
                    COUNT(*)
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND LTRIM(RTRIM(EstadoActualContacto)) = 'Contactada'

                UNION ALL

                SELECT
                    'Fecha + Lote prueba',
                    COUNT(*)
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND Lote = 'LOTE_PRUEBA_01'
                """,
            ),
        )

        imprimir_df(
            "6. FILTROS DEL CONSOLIDADO SOBRE CAUSALES",
            leer_sql(
                conn,
                """
                SELECT
                    'Fecha 2026-05-12' AS Filtro,
                    COUNT(*) AS Total
                FROM dbo.Causales
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'

                UNION ALL

                SELECT
                    'Fecha + Tipo exacto',
                    COUNT(*)
                FROM dbo.Causales
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND Tipo_de_evento = 'Categorización'

                UNION ALL

                SELECT
                    'Fecha + Tipo usando TRIM',
                    COUNT(*)
                FROM dbo.Causales
                WHERE CAST(FechayHora AS DATE) = '2026-05-12'
                  AND LTRIM(RTRIM(Tipo_de_evento)) = 'Categorización'

                UNION ALL

                SELECT
                    'Comentarios de prueba',
                    COUNT(*)
                FROM dbo.Causales
                WHERE Comentario LIKE 'Prueba controlada causales%'
                """,
            ),
        )

    print()
    print("====================================================")
    print("✅ INSPECCIÓN FINALIZADA")
    print("====================================================")


if __name__ == "__main__":
    main()