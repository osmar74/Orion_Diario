import sys
from pathlib import Path

import pandas as pd
import pyodbc


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import construir_cadena_conexion


FECHA = "2026-05-12"
MESES = "202605"


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
    print("DEBUG CONSOLIDADO - ORION DIARIO")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")
    print(f"Fecha: {FECHA}")
    print(f"Meses: {MESES}")

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=30) as conn:
        # 1. Conteos base por fecha
        imprimir_df(
            "1. CONTEOS BASE POR FECHA",
            leer_sql(
                conn,
                f"""
                SELECT 'Discador fecha' AS Paso, COUNT(*) AS Total
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '{FECHA}'

                UNION ALL

                SELECT 'Lote fecha' AS Paso, COUNT(*) AS Total
                FROM dbo.Lote
                WHERE CAST(Fecha AS DATE) = '{FECHA}'

                UNION ALL

                SELECT 'Causales fecha' AS Paso, COUNT(*) AS Total
                FROM dbo.Causales
                WHERE CAST(FechayHora AS DATE) = '{FECHA}'

                UNION ALL

                SELECT 'Causales fecha + tipo' AS Paso, COUNT(*) AS Total
                FROM dbo.Causales
                WHERE CAST(FechayHora AS DATE) = '{FECHA}'
                  AND Tipo_de_evento = 'Categorización'
                """,
            ),
        )

        # 2. Valores reales Discador
        imprimir_df(
            "2. VALORES REALES EN DISCADOR DE PRUEBA",
            leer_sql(
                conn,
                f"""
                SELECT
                    NroCliente_Contrato,
                    FechayHora,
                    NumeroTelefonico,
                    Lote,
                    Campana,
                    Agente,
                    '[' + ISNULL(Categoria, '') + ']' AS Categoria,
                    LEN(ISNULL(Categoria, '')) AS LargoCategoria,
                    '[' + ISNULL(Subcategoria, '') + ']' AS Subcategoria,
                    LEN(ISNULL(Subcategoria, '')) AS LargoSubcategoria,
                    '[' + ISNULL(EstadoActualContacto, '') + ']' AS EstadoActualContacto,
                    LEN(ISNULL(EstadoActualContacto, '')) AS LargoEstado
                FROM dbo.Discador
                WHERE Lote = 'LOTE_PRUEBA_01'
                  AND NroCliente_Contrato IN ('CLI001', 'CLI002')
                ORDER BY NroCliente_Contrato
                """,
            ),
        )

        # 3. Valores reales Lote
        imprimir_df(
            "3. VALORES REALES EN LOTE DE PRUEBA",
            leer_sql(
                conn,
                f"""
                SELECT
                    Fecha,
                    phone_number,
                    Nombre_Lote,
                    codigo_cliente,
                    segmento
                FROM dbo.Lote
                WHERE Nombre_Lote = 'LOTE_PRUEBA_01'
                  AND codigo_cliente IN ('CLI001', 'CLI002')
                ORDER BY codigo_cliente
                """,
            ),
        )

        # 4. Valores reales Causales
        imprimir_df(
            "4. VALORES REALES EN CAUSALES DE PRUEBA",
            leer_sql(
                conn,
                f"""
                SELECT
                    Codigo,
                    FechayHora,
                    NroDeAgente,
                    Telefono_utilizado,
                    Campana,
                    '[' + ISNULL(Tipo_de_evento, '') + ']' AS Tipo_de_evento,
                    LEN(ISNULL(Tipo_de_evento, '')) AS LargoTipoEvento,
                    '[' + ISNULL(Categoria, '') + ']' AS Categoria,
                    LEN(ISNULL(Categoria, '')) AS LargoCategoria,
                    '[' + ISNULL(Subcategoria, '') + ']' AS Subcategoria,
                    LEN(ISNULL(Subcategoria, '')) AS LargoSubcategoria,
                    Usuario,
                    Comentario
                FROM dbo.Causales
                WHERE Comentario LIKE 'Prueba controlada causales%'
                ORDER BY Codigo
                """,
            ),
        )

        # 5. Filtro exacto de EstadoActualContacto
        imprimir_df(
            "5. FILTRO EXACTO ESTADO = ' Contactada'",
            leer_sql(
                conn,
                f"""
                SELECT COUNT(*) AS Total
                FROM dbo.Discador
                WHERE CAST(FechayHora AS DATE) = '{FECHA}'
                  AND EstadoActualContacto = ' Contactada'
                  AND Lote = 'LOTE_PRUEBA_01'
                """,
            ),
        )

        # 6. Cruce Discador + Lote
        imprimir_df(
            "6. CRUCE DISCADOR + LOTE",
            leer_sql(
                conn,
                f"""
                SELECT
                    d.NroCliente_Contrato,
                    d.NumeroTelefonico,
                    d.Lote,
                    l.codigo_cliente,
                    l.phone_number,
                    l.Nombre_Lote
                FROM dbo.Discador d
                INNER JOIN dbo.Lote l
                    ON d.NumeroTelefonico = l.phone_number
                   AND LTRIM(RTRIM(d.Lote)) = LTRIM(RTRIM(l.Nombre_Lote))
                   AND LTRIM(RTRIM(d.NroCliente_Contrato)) = LTRIM(RTRIM(l.codigo_cliente))
                WHERE CAST(d.FechayHora AS DATE) = '{FECHA}'
                  AND CAST(l.Fecha AS DATE) = '{FECHA}'
                  AND d.Lote = 'LOTE_PRUEBA_01'
                """,
            ),
        )

        # 7. Cruce Discador + Lote + Causales
        imprimir_df(
            "7. CRUCE DISCADOR + LOTE + CAUSALES",
            leer_sql(
                conn,
                f"""
                SELECT
                    d.NroCliente_Contrato,
                    d.NumeroTelefonico,
                    d.Lote,
                    d.Campana AS CampanaDiscador,
                    c.Campana AS CampanaCausales,
                    d.Agente,
                    c.NroDeAgente,
                    l.codigo_cliente,
                    c.Codigo,
                    '[' + ISNULL(d.Categoria, '') + ']' AS CategoriaDiscador,
                    '[' + ISNULL(c.Categoria, '') + ']' AS CategoriaCausales,
                    '[' + ISNULL(d.Subcategoria, '') + ']' AS SubcategoriaDiscador,
                    '[' + ISNULL(c.Subcategoria, '') + ']' AS SubcategoriaCausales,
                    '[' + ISNULL(d.EstadoActualContacto, '') + ']' AS EstadoActualContacto,
                    '[' + ISNULL(c.Tipo_de_evento, '') + ']' AS TipoDeEvento
                FROM dbo.Discador d
                INNER JOIN dbo.Lote l
                    ON d.NumeroTelefonico = l.phone_number
                   AND LTRIM(RTRIM(d.Lote)) = LTRIM(RTRIM(l.Nombre_Lote))
                   AND LTRIM(RTRIM(d.NroCliente_Contrato)) = LTRIM(RTRIM(l.codigo_cliente))
                INNER JOIN dbo.Causales c
                    ON CAST(d.FechayHora AS DATE) = CAST(c.FechayHora AS DATE)
                   AND LTRIM(RTRIM(d.Campana)) = LTRIM(RTRIM(c.Campana))
                   AND LTRIM(RTRIM(d.Subcategoria)) = LTRIM(RTRIM(c.Subcategoria))
                   AND LTRIM(RTRIM(l.codigo_cliente)) = LTRIM(RTRIM(c.Codigo))
                   AND d.NumeroTelefonico = c.Telefono_utilizado
                   AND LTRIM(RTRIM(d.NroCliente_Contrato)) = LTRIM(RTRIM(c.Codigo))
                   AND LTRIM(RTRIM(d.Categoria)) = LTRIM(RTRIM(c.Categoria))
                   AND d.Agente = c.NroDeAgente
                WHERE CAST(d.FechayHora AS DATE) = '{FECHA}'
                  AND CAST(l.Fecha AS DATE) = '{FECHA}'
                  AND c.Tipo_de_evento = 'Categorización'
                  AND d.EstadoActualContacto = ' Contactada'
                  AND d.Lote = 'LOTE_PRUEBA_01'
                """,
            ),
        )

        # 8. Tabla externa de asesores
        imprimir_df(
            "8. ASESORES PARA MES DE GESTIÓN",
            leer_sql(
                conn,
                f"""
                SELECT TOP 20
                    '[' + LTRIM(RTRIM(Grabador)) + ']' AS Grabador,
                    Asesor,
                    Mes_Gestion
                FROM Vencorp_V2.gestion.gestion_adminfo_onedrive
                WHERE Mes_Gestion IN (
                    SELECT TRY_CAST(value AS INT)
                    FROM STRING_SPLIT('{MESES}', ',')
                )
                  AND Asesor IS NOT NULL
                  AND Asesor NOT IN ('Asesor', 'NULL')
                ORDER BY Grabador
                """,
            ),
        )

    print()
    print("====================================================")
    print("✅ DEBUG FINALIZADO")
    print("====================================================")


if __name__ == "__main__":
    main()