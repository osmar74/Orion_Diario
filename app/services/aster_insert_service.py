"""
Servicio de inserción ASTER Fase H.

Responsabilidad:
- Leer Excel ASTER normalizado.
- Preparar DataFrame insertable.
- Validar columnas mínimas.
- Validar datos.
- Diagnosticar errores reales SQL Server usando tabla temporal.
- Validar duplicados ASTER.
- Insertar datos en SQL Server.
- Aplicar commit o rollback según cuadre final.

Este service NO genera HTML.
"""

from __future__ import annotations

from typing import Any

import os

import pandas as pd
import pyodbc

from app.services.aster_insert_prepare_service import (
    construir_dataframe_insert_aster,
    es_valor_vacio_aster,
    normalizar_dataframe_sql_aster,
    preparar_columnas_insert_aster,
    validar_columnas_minimas_insert_aster,
    validar_dataframe_insert_aster,
)


def sql_identificador_aster(nombre: str) -> str:
    """
    Escapa identificadores SQL Server con corchetes.
    """
    return f"[{str(nombre).replace(']', ']]')}]"


def nombre_tabla_sql_aster(schema: str, tabla: str) -> str:
    """
    Devuelve nombre calificado de tabla destino ASTER.
    """
    return (
        f"{sql_identificador_aster(schema)}."
        f"{sql_identificador_aster(tabla)}"
    )


def limpiar_parametro_sql_aster(valor: Any) -> Any:
    """
    Limpia valores antes de enviarlos a SQL Server.
    """
    if es_valor_vacio_aster(valor):
        return None

    texto = str(valor).strip()

    if texto.lower() in {"nan", "nat", "none", "null"}:
        return None

    return valor


def resolver_columna_sql_aster(
    columnas_insert: list[dict[str, Any]],
    posibles_nombres: list[str],
) -> str | None:
    """
    Busca una columna SQL disponible usando varios nombres posibles.
    """
    nombres_sql = {
        str(col["sql"]).lower(): str(col["sql"])
        for col in columnas_insert
    }

    for nombre in posibles_nombres:
        columna = nombres_sql.get(nombre.lower())

        if columna:
            return columna

    return None


def seleccionar_columnas_clave_duplicados_aster(
    columnas_insert: list[dict[str, Any]],
) -> list[str]:
    """
    Selecciona clave anti-duplicados ASTER.

    Regla:
    Fecha_Hora + Atendido_por + Codigo
    """
    columna_fecha = resolver_columna_sql_aster(
        columnas_insert,
        ["Fecha_Hora", "FechaHora", "Fecha"],
    )

    columna_atendido_por = resolver_columna_sql_aster(
        columnas_insert,
        ["Atendido_por", "AtendidoPor"],
    )

    columna_codigo = resolver_columna_sql_aster(
        columnas_insert,
        ["Codigo", "Código"],
    )

    columnas_faltantes = []

    if not columna_fecha:
        columnas_faltantes.append("Fecha_Hora")

    if not columna_atendido_por:
        columnas_faltantes.append("Atendido_por")

    if not columna_codigo:
        columnas_faltantes.append("Codigo")

    if columnas_faltantes:
        raise ValueError(
            "No se puede validar duplicados ASTER. "
            "Faltan columnas clave en la comparación Excel vs SQL: "
            + ", ".join(columnas_faltantes)
        )

    return [
        columna_fecha,
        columna_atendido_por,
        columna_codigo,
    ]


def info_columna_insert_aster(
    columna: str,
    columnas_insert: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Obtiene metadatos SQL de una columna insertable.
    """
    for col in columnas_insert:
        if str(col["sql"]).lower() == str(columna).lower():
            return col

    return None


def es_tipo_texto_sql_aster(tipo_sql: str) -> bool:
    """
    Indica si un tipo SQL Server es texto y puede requerir COLLATE.
    """
    return str(tipo_sql).lower() in {
        "varchar",
        "nvarchar",
        "char",
        "nchar",
        "text",
        "ntext",
    }


def tipo_sql_temporal_aster(
    columna: str,
    columnas_insert: list[dict[str, Any]],
) -> str:
    """
    Devuelve tipo SQL seguro para crear columna temporal.
    """
    info = info_columna_insert_aster(columna, columnas_insert)

    if not info:
        return "NVARCHAR(4000) COLLATE DATABASE_DEFAULT"

    tipo = str(info.get("tipo_sql") or "").lower()
    longitud = info.get("longitud")
    precision = info.get("precision")
    escala = info.get("escala")

    if tipo in {"varchar", "char"}:
        if not longitud or int(longitud) <= 0 or int(longitud) > 4000:
            return "VARCHAR(4000) COLLATE DATABASE_DEFAULT"

        return f"VARCHAR({int(longitud)}) COLLATE DATABASE_DEFAULT"

    if tipo in {"nvarchar", "nchar"}:
        if not longitud or int(longitud) <= 0 or int(longitud) > 4000:
            return "NVARCHAR(4000) COLLATE DATABASE_DEFAULT"

        return f"NVARCHAR({int(longitud)}) COLLATE DATABASE_DEFAULT"

    if tipo in {"int", "bigint", "smallint", "tinyint"}:
        return tipo.upper()

    if tipo in {"decimal", "numeric"}:
        p = int(precision or 18)
        s = int(escala or 0)

        return f"DECIMAL({p},{s})"

    if tipo in {"float", "real"}:
        return "FLOAT"

    if tipo in {"bit"}:
        return "BIT"

    if tipo in {"date"}:
        return "DATE"

    if tipo in {"datetime", "datetime2", "smalldatetime"}:
        return "DATETIME2"

    if tipo in {"time"}:
        return "TIME"

    return "NVARCHAR(4000) COLLATE DATABASE_DEFAULT"


def tipo_sql_columna_insert_aster(
    columna: str,
    columnas_insert: list[dict[str, Any]],
) -> str:
    """
    Devuelve descripción del tipo SQL para una columna insertable.
    """
    for col in columnas_insert:
        if str(col["sql"]).lower() == str(columna).lower():
            tipo = str(col.get("tipo_sql") or "")
            precision = col.get("precision")
            escala = col.get("escala")
            longitud = col.get("longitud")

            if tipo.lower() in {"decimal", "numeric"}:
                return f"{tipo}({precision},{escala})"

            if tipo.lower() in {"varchar", "nvarchar", "char", "nchar"}:
                return f"{tipo}({longitud})"

            return tipo

    return ""


def contar_duplicados_sql_aster(
    cursor: Any,
    df_insert: pd.DataFrame,
    columnas_clave: list[str],
    columnas_insert: list[dict[str, Any]],
    schema: str,
    tabla: str,
    limite_ejemplos: int = 10,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Verifica duplicados usando tabla temporal SQL Server.

    Clave:
    Fecha_Hora + Atendido_por + Codigo
    """
    if df_insert.empty or not columnas_clave:
        return 0, []

    duplicados_excel = df_insert.duplicated(
        subset=columnas_clave,
        keep=False,
    )

    if duplicados_excel.any():
        ejemplos: list[dict[str, Any]] = []

        for _, fila in df_insert.loc[duplicados_excel, columnas_clave].head(
            limite_ejemplos
        ).iterrows():
            ejemplos.append(
                {
                    columna: fila[columna]
                    for columna in columnas_clave
                }
            )

        return int(duplicados_excel.sum()), ejemplos

    cursor.execute(
        "IF OBJECT_ID('tempdb..#aster_claves') IS NOT NULL DROP TABLE #aster_claves"
    )

    columnas_temp = []

    for columna in columnas_clave:
        tipo_temp = tipo_sql_temporal_aster(columna, columnas_insert)
        columnas_temp.append(f"{sql_identificador_aster(columna)} {tipo_temp} NULL")

    cursor.execute(
        "CREATE TABLE #aster_claves ("
        + ", ".join(columnas_temp)
        + ")"
    )

    df_claves = df_insert[columnas_clave].drop_duplicates().copy()
    df_claves = df_claves.where(pd.notna(df_claves), None)

    columnas_sql = ", ".join(
        sql_identificador_aster(columna)
        for columna in columnas_clave
    )
    placeholders = ", ".join("?" for _ in columnas_clave)

    sql_insert_temp = f"""
        INSERT INTO #aster_claves ({columnas_sql})
        VALUES ({placeholders})
    """

    valores_temp = [
        tuple(
            limpiar_parametro_sql_aster(row[columna])
            for columna in columnas_clave
        )
        for _, row in df_claves.iterrows()
    ]

    cursor.fast_executemany = True
    cursor.executemany(sql_insert_temp, valores_temp)

    tabla_sql = nombre_tabla_sql_aster(schema, tabla)

    condiciones_join = []

    for columna in columnas_clave:
        col = sql_identificador_aster(columna)
        info_columna = info_columna_insert_aster(columna, columnas_insert)
        tipo_sql = str(info_columna.get("tipo_sql") or "") if info_columna else ""

        if es_tipo_texto_sql_aster(tipo_sql):
            condiciones_join.append(
                f"""(
                    (t.{col} COLLATE DATABASE_DEFAULT = k.{col} COLLATE DATABASE_DEFAULT)
                    OR (t.{col} IS NULL AND k.{col} IS NULL)
                )"""
            )
        else:
            condiciones_join.append(
                f"((t.{col} = k.{col}) OR (t.{col} IS NULL AND k.{col} IS NULL))"
            )

    join_sql = " AND ".join(condiciones_join)

    columnas_select = ", ".join(
        f"t.{sql_identificador_aster(columna)}"
        for columna in columnas_clave
    )

    sql_ejemplos = f"""
        SELECT TOP ({limite_ejemplos})
            {columnas_select}
        FROM {tabla_sql} t
        INNER JOIN #aster_claves k
            ON {join_sql}
    """

    cursor.execute(sql_ejemplos)
    rows = cursor.fetchall()

    ejemplos: list[dict[str, Any]] = []

    for row in rows:
        ejemplo = {}

        for idx, columna in enumerate(columnas_clave):
            ejemplo[columna] = row[idx]

        ejemplos.append(ejemplo)

    if ejemplos:
        return len(ejemplos), ejemplos

    return 0, []


def crear_tabla_temporal_debug_aster(
    cursor: Any,
    columnas: list[str],
    schema: str,
    tabla: str,
    nombre_temp: str = "#aster_insert_debug",
) -> None:
    """
    Crea tabla temporal con los mismos tipos de columnas que la tabla real.
    """
    tabla_sql = nombre_tabla_sql_aster(schema, tabla)

    columnas_select = ", ".join(
        sql_identificador_aster(columna)
        for columna in columnas
    )

    cursor.execute(
        f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"
    )

    cursor.execute(
        f"""
        SELECT TOP 0 {columnas_select}
        INTO {nombre_temp}
        FROM {tabla_sql}
        """
    )


def probar_insert_temporal_aster(
    cursor: Any,
    df_prueba: pd.DataFrame,
    nombre_temp: str = "#aster_insert_debug",
) -> None:
    """
    Intenta insertar en tabla temporal para validar conversión SQL Server.
    """
    columnas = list(df_prueba.columns)

    columnas_sql = ", ".join(
        sql_identificador_aster(columna)
        for columna in columnas
    )
    placeholders = ", ".join("?" for _ in columnas)

    sql_insert = f"""
        INSERT INTO {nombre_temp} ({columnas_sql})
        VALUES ({placeholders})
    """

    valores = [
        tuple(
            limpiar_parametro_sql_aster(row[columna])
            for columna in columnas
        )
        for _, row in df_prueba.iterrows()
    ]

    cursor.fast_executemany = True
    cursor.executemany(sql_insert, valores)


def diagnosticar_insert_sql_aster(
    conn: Any,
    df_insert: pd.DataFrame,
    columnas_insert: list[dict[str, Any]],
    schema: str,
    tabla: str,
    tamano_lote: int = 500,
) -> list[dict[str, Any]]:
    """
    Diagnostica errores reales de SQL Server antes de insertar.
    """
    errores: list[dict[str, Any]] = []

    if df_insert.empty:
        return errores

    columnas = list(df_insert.columns)
    cursor = conn.cursor()

    for inicio in range(0, len(df_insert), tamano_lote):
        bloque = df_insert.iloc[inicio : inicio + tamano_lote].copy()

        try:
            crear_tabla_temporal_debug_aster(
                cursor,
                columnas,
                schema=schema,
                tabla=tabla,
            )
            probar_insert_temporal_aster(cursor, bloque)
            cursor.execute("DROP TABLE #aster_insert_debug")
            continue

        except Exception:
            conn.rollback()

            for idx, fila in bloque.iterrows():
                fila_df = pd.DataFrame([fila.to_dict()])

                try:
                    crear_tabla_temporal_debug_aster(
                        cursor,
                        columnas,
                        schema=schema,
                        tabla=tabla,
                    )
                    probar_insert_temporal_aster(cursor, fila_df)
                    cursor.execute("DROP TABLE #aster_insert_debug")
                    continue

                except Exception as exc_fila:
                    conn.rollback()

                    errores_columna = []

                    for columna in columnas:
                        valor = fila[columna]
                        columna_df = pd.DataFrame([{columna: valor}])

                        try:
                            crear_tabla_temporal_debug_aster(
                                cursor,
                                [columna],
                                schema=schema,
                                tabla=tabla,
                            )
                            probar_insert_temporal_aster(cursor, columna_df)
                            cursor.execute("DROP TABLE #aster_insert_debug")

                        except Exception as exc_columna:
                            conn.rollback()

                            errores_columna.append(
                                {
                                    "fila": int(idx) + 2,
                                    "columna": columna,
                                    "tipo_sql": tipo_sql_columna_insert_aster(
                                        columna,
                                        columnas_insert,
                                    ),
                                    "valor": valor,
                                    "problema": str(exc_columna),
                                }
                            )

                            break

                    if errores_columna:
                        return errores_columna

                    return [
                        {
                            "fila": int(idx) + 2,
                            "columna": "No identificada",
                            "tipo_sql": "",
                            "valor": "",
                            "problema": str(exc_fila),
                        }
                    ]

    return errores


def insertar_dataframe_sql_aster(
    conn: Any,
    df_insert: pd.DataFrame,
    schema: str,
    tabla: str,
    tamano_lote: int = 1000,
) -> int:
    """
    Inserta DataFrame en SQL Server por lotes.
    """
    if df_insert.empty:
        return 0

    columnas = list(df_insert.columns)
    tabla_sql = nombre_tabla_sql_aster(schema, tabla)

    columnas_sql = ", ".join(
        sql_identificador_aster(col)
        for col in columnas
    )
    placeholders = ", ".join("?" for _ in columnas)

    sql_insert = f"""
        INSERT INTO {tabla_sql} ({columnas_sql})
        VALUES ({placeholders})
    """

    total_insertados = 0
    cursor = conn.cursor()
    cursor.fast_executemany = True

    for inicio in range(0, len(df_insert), tamano_lote):
        bloque = df_insert.iloc[inicio : inicio + tamano_lote]

        valores = [
            tuple(
                limpiar_parametro_sql_aster(row[col])
                for col in columnas
            )
            for _, row in bloque.iterrows()
        ]

        cursor.executemany(sql_insert, valores)
        total_insertados += len(valores)

    return total_insertados


def validar_cuadre_final_aster(
    total_filas_excel: int,
    total_insertados: int,
    total_general_aster: Any,
) -> tuple[bool, dict[str, Any]]:
    """
    Valida:
    filas Excel = registros insertados = Total general ASTER
    """
    try:
        total_aster_int = int(total_general_aster)
    except Exception:
        total_aster_int = None

    cumple = (
        total_aster_int is not None
        and int(total_filas_excel) == int(total_insertados)
        and int(total_insertados) == int(total_aster_int)
    )

    detalle = {
        "filas_excel": int(total_filas_excel),
        "registros_insertados": int(total_insertados),
        "total_general_aster": total_aster_int,
        "cumple": cumple,
    }

    return cumple, detalle


def insertar_datos_aster(
    ruta_archivo: str,
    columnas_sql: list[dict[str, Any]],
    cadena_sqlserver: str,
    base: str,
    schema: str,
    tabla: str,
    total_general_aster: Any,
) -> dict[str, Any]:
    """
    Ejecuta inserción completa ASTER Fase H.

    Aplica rollback si:
    - hay errores de validación,
    - hay errores SQL reales,
    - hay duplicados,
    - no cuadra filas Excel = insertados = Total ASTER.
    """
    conn = None
    ruta_archivo = str(ruta_archivo or "").strip()

    if not ruta_archivo:
        return {
            "success": False,
            "status": "sin_archivo",
            "error": "No se recibió archivo ASTER normalizado.",
        }

    if not os.path.isfile(ruta_archivo):
        return {
            "success": False,
            "status": "archivo_no_existe",
            "error": "El archivo ASTER no existe.",
            "ruta_archivo": ruta_archivo,
        }

    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as exc:
        return {
            "success": False,
            "status": "error_lectura",
            "error": f"Error leyendo Excel ASTER: {exc}",
            "ruta_archivo": ruta_archivo,
        }

    if df.empty:
        return {
            "success": False,
            "status": "archivo_vacio",
            "error": "El archivo ASTER no tiene registros para insertar.",
            "ruta_archivo": ruta_archivo,
        }

    columnas_insert = preparar_columnas_insert_aster(df, columnas_sql)

    error_columnas = validar_columnas_minimas_insert_aster(columnas_insert)

    if error_columnas:
        return {
            "success": False,
            "status": "error_columnas",
            "error": error_columnas,
            "ruta_archivo": ruta_archivo,
            "total_leidos": len(df),
        }

    df_insert = construir_dataframe_insert_aster(df, columnas_insert)
    df_insert = normalizar_dataframe_sql_aster(df_insert)

    errores_validacion = validar_dataframe_insert_aster(
        df_insert=df_insert,
        columnas_insert=columnas_insert,
    )

    if errores_validacion:
        return {
            "success": False,
            "status": "errores_validacion",
            "errores": errores_validacion,
            "ruta_archivo": ruta_archivo,
            "total_leidos": len(df),
        }

    try:
        columnas_clave = seleccionar_columnas_clave_duplicados_aster(columnas_insert)

        conn = pyodbc.connect(cadena_sqlserver, timeout=10)
        conn.timeout = 120

        cursor = conn.cursor()
        cursor.execute(f"USE {sql_identificador_aster(base)}")

        errores_sql_reales = diagnosticar_insert_sql_aster(
            conn=conn,
            df_insert=df_insert,
            columnas_insert=columnas_insert,
            schema=schema,
            tabla=tabla,
        )

        if errores_sql_reales:
            conn.rollback()

            return {
                "success": False,
                "status": "errores_sql_reales",
                "errores": errores_sql_reales,
                "ruta_archivo": ruta_archivo,
                "total_leidos": len(df),
            }

        total_duplicados, ejemplos_duplicados = contar_duplicados_sql_aster(
            cursor=cursor,
            df_insert=df_insert,
            columnas_clave=columnas_clave,
            columnas_insert=columnas_insert,
            schema=schema,
            tabla=tabla,
        )

        if total_duplicados > 0:
            conn.rollback()

            return {
                "success": False,
                "status": "duplicados",
                "ruta_archivo": ruta_archivo,
                "total_leidos": len(df),
                "total_duplicados": total_duplicados,
                "ejemplos_duplicados": ejemplos_duplicados,
                "columnas_clave": columnas_clave,
            }

        total_insertados = insertar_dataframe_sql_aster(
            conn=conn,
            df_insert=df_insert,
            schema=schema,
            tabla=tabla,
        )

        cuadre_ok, detalle_cuadre = validar_cuadre_final_aster(
            total_filas_excel=len(df),
            total_insertados=total_insertados,
            total_general_aster=total_general_aster,
        )

        if not cuadre_ok:
            conn.rollback()

            return {
                "success": False,
                "status": "cuadre_fallido",
                "ruta_archivo": ruta_archivo,
                "total_leidos": len(df),
                "total_insertados": total_insertados,
                "detalle_cuadre": detalle_cuadre,
                "columnas_clave": columnas_clave,
                "columnas_insertadas": list(df_insert.columns),
            }

        conn.commit()

        return {
            "success": True,
            "status": "insertado",
            "ruta_archivo": ruta_archivo,
            "total_leidos": len(df),
            "total_insertados": total_insertados,
            "detalle_cuadre": detalle_cuadre,
            "columnas_clave": columnas_clave,
            "columnas_insertadas": list(df_insert.columns),
        }

    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass

        return {
            "success": False,
            "status": "error",
            "error": f"Error insertando datos ASTER: {exc}",
            "ruta_archivo": ruta_archivo,
            "total_leidos": len(df),
        }

    finally:
        if conn is not None:
            conn.close()
