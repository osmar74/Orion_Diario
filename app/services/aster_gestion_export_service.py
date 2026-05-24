"""
Servicio de exportación Gestión ASTER.

Responsabilidad:
- Ejecutar consulta final Gestión ASTER.
- Aplicar tratamiento previo al Excel.
- Exportar YYYYMMDD_Gestion_aster.xlsx.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import pyodbc

from app.services.aster_sqlserver_service import obtener_cadena_sqlserver_aster
from app.services.daily_paths import ruta_aster_subcarpeta


def ejecutar_consulta_gestion_aster_fase_i(
    cursor: Any,
    fecha_yyyymmdd: str,
) -> pd.DataFrame:
    """
    Ejecuta la consulta final de Gestión ASTER para la fecha del proceso.
    """
    fecha_inicio = datetime.strptime(fecha_yyyymmdd, "%Y%m%d")
    fecha_fin = fecha_inicio + timedelta(days=1)

    sql = """
    WITH
    CTE_Aster_Base AS (
        SELECT
            Codigo,
            Fecha_Hora,
            Duracion,
            Estado,
            Atendio,
            Numero,
            Cartera,
            CASE
                WHEN Estado = 'ATENDIDO'
                 AND Atendio IN ('HUMANO', 'DESCONOCIDO')
                THEN 1 ELSE 0
            END AS EsHumano
        FROM [dbo].[aster_dia_nc]
        WHERE Fecha_Hora >= ? AND Fecha_Hora < ?
    ),

    CTE_Comentarios_Base AS (
        SELECT
            [data],
            resultado1,
            resultado2,
            datapers,
            usuario,
            comentario
        FROM [dbo].[comentarios]
        WHERE fecha >= ? AND fecha < ?
    ),

    CTE_Maquinas AS (
        SELECT DISTINCT
            Codigo AS Cliente_Nro,
            Fecha_Hora,
            Duracion,
            CASE
                WHEN Estado = 'OCUPADO' AND Atendio = 'NULL' THEN 'Telefono Ocupado'
                WHEN Estado = 'ATENDIDO' AND Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                WHEN Estado = 'NO ATENDIDO' AND Atendio = 'NULL' THEN 'No contestan'
                WHEN Estado = 'ATENDIDO' AND Atendio = 'CORTO' THEN 'No contestan'
                WHEN Estado = 'CONGESTION' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                WHEN Estado = 'SIN CANALES' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                ELSE 'Usuario pide volver a llamar'
            END AS [Descripcion Codigo De Gestion],
            '' AS Fecha_Compromiso,
            '' AS Grabador,
            Numero AS Telefonos,
            CASE
                WHEN Codigo IS NULL OR LTRIM(RTRIM(Codigo)) = '' THEN NULL
                WHEN Codigo LIKE 'M%' THEN 'Mobile'
                ELSE 'Home'
            END AS [Tipo Cartera],
            '' AS Asesor,
            Cartera AS [Antiguedad De La Cartera],
            '' AS [Nota de la Gestion],
            'codmaquina' AS [Clase de Gestion],
            '' AS [Causal de Mora/Respuesta]
        FROM CTE_Aster_Base
        WHERE EsHumano = 0
    ),

    CTE_Humanos_Processed AS (
        SELECT
            _dia.Codigo AS Cliente_Nro,
            _dia.Fecha_Hora,
            _dia.Duracion,
            _dia.Numero AS Telefonos,
            _dia.Cartera AS [Antiguedad De La Cartera],
            CASE
                WHEN _contactada.resultado1 IS NULL
                  OR LTRIM(RTRIM(_contactada.resultado1)) = ''
                THEN 'codmaquina'
                ELSE 'TEL'
            END AS [Clase de Gestion],

            LTRIM(RTRIM(CASE
                WHEN _contactada.resultado1 IS NULL
                  OR LTRIM(RTRIM(_contactada.resultado1)) = ''
                THEN
                    CASE
                        WHEN _dia.Estado = 'OCUPADO' AND _dia.Atendio = 'NULL' THEN 'Telefono Ocupado'
                        WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                        WHEN _dia.Estado = 'NO ATENDIDO' AND _dia.Atendio = 'NULL' THEN 'No contestan'
                        WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CORTO' THEN 'No contestan'
                        WHEN _dia.Estado = 'CONGESTION' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                        WHEN _dia.Estado = 'SIN CANALES' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                        ELSE 'Usuario pide volver a llamar'
                    END
                ELSE [dbo].[Obtener_Estado](_contactada.resultado1, _contactada.resultado2)
            END)) AS [Desc_Raw],

            CASE
                WHEN CHARINDEX('compromisos<=>', _contactada.datapers) > 0 THEN
                    REPLACE(
                        SUBSTRING(
                            _contactada.datapers,
                            CHARINDEX('compromisos<=>', _contactada.datapers) + 14,
                            CASE
                                WHEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers)) > 0
                                THEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers))
                                   - (CHARINDEX('compromisos<=>', _contactada.datapers) + 14)
                                ELSE 10
                            END
                        ),
                        '-',
                        '/'
                    )
                ELSE ''
            END AS Fecha_Compromiso,

            [dbo].[Obtener_Usuario](_contactada.usuario) AS Grabador,

            CASE
                WHEN _dia.Codigo IS NULL OR LTRIM(RTRIM(_dia.Codigo)) = '' THEN NULL
                WHEN _dia.Codigo LIKE 'M%' THEN 'Mobile'
                ELSE 'Home'
            END AS [Tipo Cartera],

            _contactada.usuario AS Asesor,

            LTRIM(RTRIM(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(_contactada.comentario, CHAR(9), ''),
                            CHAR(10),
                            ''
                        ),
                        CHAR(13),
                        ''
                    ),
                    CHAR(160),
                    ' '
                )
            )) AS [Nota_Clean],

            LTRIM(RTRIM([dbo].[Obtener_Causal_Mora](_contactada.resultado2)))
                AS [Causal de Mora/Respuesta]
        FROM CTE_Aster_Base _dia
        LEFT JOIN CTE_Comentarios_Base _contactada
            ON _dia.Codigo = _contactada.[data]
        WHERE _dia.EsHumano = 1
    ),

    CTE_Humanos_Final AS (
        SELECT DISTINCT
            Cliente_Nro,
            Fecha_Hora,
            Duracion,
            CASE
                WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
                 AND [Clase de Gestion] = 'codmaquina'
                THEN 'No contestan'
                ELSE [Desc_Raw]
            END AS [Descripcion Codigo De Gestion],
            Fecha_Compromiso,
            Grabador,
            Telefonos,
            [Tipo Cartera],
            Asesor,
            [Antiguedad De La Cartera],
            CASE
                WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
                 AND [Clase de Gestion] = 'codmaquina'
                THEN ''
                ELSE [Nota_Clean]
            END AS [Nota de la Gestion],
            [Clase de Gestion],
            [Causal de Mora/Respuesta]
        FROM CTE_Humanos_Processed
    ),

    CTE_Universo AS (
        SELECT * FROM CTE_Maquinas
        UNION ALL
        SELECT * FROM CTE_Humanos_Final
    )

    SELECT
        Cliente_Nro AS [Cliente Nro.],
        FORMAT(Fecha_Hora, 'dd/MM/yyyy') AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), Fecha_Hora, 108), '00:00:00') AS [Hora De Gestion],
        FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(Duracion AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
        [Descripcion Codigo De Gestion],
        Fecha_Compromiso,
        Grabador,
        'Vencorp' AS [Responsable De Cobro],
        Telefonos,
        [Tipo Cartera],
        Asesor,
        [Antiguedad De La Cartera],
        [Nota de la Gestion],
        [Clase de Gestion],
        [Causal de Mora/Respuesta]
    FROM CTE_Universo
    ORDER BY [Clase de Gestion], [Hora De Gestion]
    """

    cursor.execute(sql, fecha_inicio, fecha_fin, fecha_inicio, fecha_fin)

    columnas = [columna[0] for columna in cursor.description]
    filas = cursor.fetchall()

    return pd.DataFrame.from_records(filas, columns=columnas)

def tratar_gestion_aster_antes_excel(
    df_gestion: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Tratamiento final antes de exportar Gestión ASTER a Excel.

    Reglas:
    1. Eliminar valores NULL / None / NaN / NaT / 'NULL' / 'nan' reemplazándolos por vacío.
    2. Si 'Descripcion Codigo De Gestion' inicia con 'Acuerdo',
       debe conservar Fecha_Compromiso.
    3. Si NO inicia con 'Acuerdo',
       Fecha_Compromiso debe quedar vacío.
    """
    df_tratado = df_gestion.copy()

    total_filas = len(df_tratado)

    df_tratado = df_tratado.replace(
        {
            None: "",
            pd.NA: "",
            pd.NaT: "",
        }
    )

    df_tratado = df_tratado.fillna("")

    valores_null_texto = {
        "NULL",
        "null",
        "None",
        "none",
        "NaN",
        "nan",
        "NaT",
        "nat",
    }

    celdas_null_texto = 0

    for columna in df_tratado.columns:
        serie_texto = df_tratado[columna].astype(str).str.strip()
        mascara_null_texto = serie_texto.isin(valores_null_texto)
        celdas_null_texto += int(mascara_null_texto.sum())
        df_tratado.loc[mascara_null_texto, columna] = ""

    col_descripcion = "Descripcion Codigo De Gestion"
    col_fecha_compromiso = "Fecha_Compromiso"

    fechas_compromiso_limpiadas = 0
    acuerdos_sin_fecha_compromiso = 0
    acuerdos_con_fecha_compromiso = 0

    if col_descripcion in df_tratado.columns and col_fecha_compromiso in df_tratado.columns:
        descripcion = df_tratado[col_descripcion].astype(str).str.strip()
        fecha_compromiso = df_tratado[col_fecha_compromiso].astype(str).str.strip()

        mascara_acuerdo = descripcion.str.startswith("Acuerdo", na=False)
        mascara_no_acuerdo = ~mascara_acuerdo

        fechas_compromiso_limpiadas = int(
            (mascara_no_acuerdo & (fecha_compromiso != "")).sum()
        )

        df_tratado.loc[mascara_no_acuerdo, col_fecha_compromiso] = ""

        fecha_compromiso_post = df_tratado[col_fecha_compromiso].astype(str).str.strip()

        acuerdos_con_fecha_compromiso = int(
            (mascara_acuerdo & (fecha_compromiso_post != "")).sum()
        )

        acuerdos_sin_fecha_compromiso = int(
            (mascara_acuerdo & (fecha_compromiso_post == "")).sum()
        )

    resumen = {
        "total_filas": total_filas,
        "celdas_null_texto_limpiadas": celdas_null_texto,
        "fechas_compromiso_limpiadas_no_acuerdo": fechas_compromiso_limpiadas,
        "acuerdos_con_fecha_compromiso": acuerdos_con_fecha_compromiso,
        "acuerdos_sin_fecha_compromiso": acuerdos_sin_fecha_compromiso,
    }

    return df_tratado, resumen


def ruta_gestion_aster_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> tuple[str, str]:
    """
    Devuelve nombre y ruta del Excel Gestión ASTER.

    Ubicación:
    data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Gestion
    """
    carpeta_gestion = ruta_aster_subcarpeta(
        data_dir,
        fecha_yyyymmdd,
        "Gestion",
    )
    os.makedirs(carpeta_gestion, exist_ok=True)

    nombre_archivo = f"{fecha_yyyymmdd}_Gestion_aster.xlsx"
    ruta_archivo = os.path.join(carpeta_gestion, nombre_archivo)

    return nombre_archivo, ruta_archivo

def generar_gestion_aster_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
) -> dict[str, Any]:
    """
    Genera Excel de Gestión ASTER después de Fase I.
    """
    conn_sql = None

    try:
        conexion_normalizada = str(conexion or "local").strip().lower()

        if conexion_normalizada not in {"local", "remoto"}:
            conexion_normalizada = "local"

        cadena = obtener_cadena_sqlserver_aster(
            conexion=conexion_normalizada,
            sql_local=sql_local,
            sql_remoto=sql_remoto,
            database_default=base,
        )

        conn_sql = pyodbc.connect(cadena, timeout=10)
        conn_sql.timeout = 120

        cursor = conn_sql.cursor()
        cursor.execute(f"USE [{base}]")

        df_gestion = ejecutar_consulta_gestion_aster_fase_i(
            cursor,
            fecha_yyyymmdd,
        )

        df_gestion, resumen_tratamiento = tratar_gestion_aster_antes_excel(
            df_gestion
        )

        nombre_archivo, ruta_archivo = ruta_gestion_aster_fase_i(
            data_dir=data_dir,
            fecha_yyyymmdd=fecha_yyyymmdd,
        )

        df_gestion.to_excel(ruta_archivo, index=False)

        return {
            "success": True,
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "conexion": conexion_normalizada,
            "registros_generados": len(df_gestion),
            "nombre_archivo": nombre_archivo,
            "ruta_archivo": ruta_archivo,
            "resumen_tratamiento": resumen_tratamiento,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "conexion": conexion,
        }

    finally:
        if conn_sql is not None:
            conn_sql.close()

