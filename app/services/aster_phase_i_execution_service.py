"""
Servicio de ejecución Fase I ASTER.

Responsabilidad:
- Leer usuarios desde MySQL usuarios.crm.
- Leer comentarios desde MySQL gestioncomercial.comentarios.
- Excluir usuario SystemUser.
- Transformar fechaagenda 1900-01-01 a NULL.
- Preparar DataFrames para SQL Server.
- Validar claves anti-duplicados en comentarios.
- Validar duplicados en SQL Server.
- Borrar usuarios destino.
- Insertar usuarios.
- Insertar comentarios.
- Devolver pipeline/resumen estructurado.

Este service ejecuta DELETE/INSERT en SQL Server.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pyodbc

from app.services.sql_loader import cargar_sql
from app.services.aster_insert_prepare_service import (
    convertir_valor_sql_aster,
    es_valor_vacio_aster,
    normalizar_dataframe_sql_aster,
)
from app.services.aster_insert_service import (
    limpiar_parametro_sql_aster,
    sql_identificador_aster,
    sql_use_database_aster,
)
from app.services.aster_phase_i_prepare_service import (
    columnas_mysql_comentarios_fase_i,
    columnas_mysql_usuarios_fase_i,
    conectar_mysql_fase_i,
    leer_entidades_fase_i,
    obtener_fecha_fase_i,
    validar_sql_mysql_solo_select,
)
from app.services.aster_sqlserver_service import (
    obtener_cadena_sqlserver_aster,
    obtener_columnas_sqlserver_tabla,
)


def nombre_tabla_sql_fase_i(schema: str, tabla: str) -> str:
    """
    Devuelve nombre calificado para tablas Fase I.
    """
    return (
        f"{sql_identificador_aster(schema)}."
        f"{sql_identificador_aster(tabla)}"
    )


def numero_fila_excel_fase_i(indice: Any) -> int:
    """
    Convierte índice de DataFrame a número de fila Excel aproximado.
    """
    try:
        return int(indice) + 2
    except Exception:
        return 0


def agregar_paso_pipeline_fase_i(
    pipeline: list[dict[str, Any]],
    paso: int,
    proceso: str,
    origen: str,
    destino: str,
    accion: str,
    cantidad: int | str,
    estado: str = "OK",
) -> None:
    """
    Agrega un paso al pipeline visual de Fase I.
    """
    pipeline.append(
        {
            "paso": paso,
            "proceso": proceso,
            "origen": origen,
            "destino": destino,
            "accion": accion,
            "cantidad": cantidad,
            "estado": estado,
        }
    )


def leer_usuarios_mysql_fase_i(db_usuarios: str) -> pd.DataFrame:
    """
    Lee usuarios desde MySQL usuarios.crm.
    Solo SELECT.
    """
    columnas = columnas_mysql_usuarios_fase_i()

    columnas_sql = ", ".join(
        f"`{col}` AS `{col}`"
        for col in columnas
    )

    sql = cargar_sql("aster/fase_i/mysql_select_usuarios.sql").format(
        columnas=columnas_sql
    )

    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_usuarios)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            filas = cursor.fetchall()

        return pd.DataFrame(filas, columns=columnas)

    finally:
        conn.close()


def leer_comentarios_mysql_fase_i(
    db_gestion: str,
    fecha_yyyymmdd: str,
    entidades: list[str],
) -> pd.DataFrame:
    """
    Lee comentarios desde MySQL gestioncomercial.comentarios.

    Regla importante:
    - Excluye usuario SystemUser.
    """
    columnas = columnas_mysql_comentarios_fase_i()

    if not entidades:
        return pd.DataFrame(columns=columnas)

    columnas_sql = ", ".join(
        f"`{col}` AS `{col}`"
        for col in columnas
    )

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    placeholders = ", ".join(["%s"] * len(entidades))

    sql = cargar_sql("aster/fase_i/mysql_select_comentarios.sql").format(
        columnas=columnas_sql,
        placeholders=placeholders,
    )

    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_gestion)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, [fecha_sql, *entidades])
            filas = cursor.fetchall()

        return pd.DataFrame(filas, columns=columnas)

    finally:
        conn.close()


def transformar_comentarios_fase_i(df: pd.DataFrame) -> pd.DataFrame:
    """
    Regla SSIS:
    fechaagenda = 1900-01-01 00:00:00 -> NULL
    """
    df_transformado = df.copy()

    if "fechaagenda" in df_transformado.columns:
        fechas_agenda = pd.to_datetime(
            df_transformado["fechaagenda"],
            errors="coerce",
        )

        fecha_base = pd.Timestamp("1900-01-01 00:00:00")

        df_transformado.loc[
            fechas_agenda == fecha_base,
            "fechaagenda",
        ] = None

    return df_transformado


def preparar_columnas_insert_fase_i(
    df: pd.DataFrame,
    columnas_sql: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Determina columnas comunes entre origen y destino.
    Excluye identity.
    """
    origen_por_lower = {
        str(col).lower(): str(col)
        for col in df.columns
    }

    columnas_insert: list[dict[str, Any]] = []

    for col_sql in columnas_sql:
        if int(col_sql.get("is_identity") or 0) == 1:
            continue

        nombre_sql = str(col_sql["columna"])
        nombre_origen = origen_por_lower.get(nombre_sql.lower())

        if not nombre_origen:
            continue

        columnas_insert.append(
            {
                "origen": nombre_origen,
                "sql": nombre_sql,
                "tipo_sql": str(col_sql["tipo_sql"]),
                "nullable": str(col_sql["nullable"]),
                "longitud": col_sql.get("longitud"),
                "precision": col_sql.get("precision"),
                "escala": col_sql.get("escala"),
            }
        )

    return columnas_insert


def construir_dataframe_insert_fase_i(
    df: pd.DataFrame,
    columnas_insert: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Construye DataFrame listo para insertar en SQL Server.
    """
    data_convertida: dict[str, list[Any]] = {}

    for col in columnas_insert:
        nombre_origen = str(col["origen"])
        nombre_sql = str(col["sql"])
        tipo_sql = str(col["tipo_sql"])

        data_convertida[nombre_sql] = [
            convertir_valor_sql_aster(valor, tipo_sql)
            for valor in df[nombre_origen].tolist()
        ]

    df_insert = pd.DataFrame(data_convertida)
    df_insert = normalizar_dataframe_sql_aster(df_insert)

    return df_insert


def validar_columnas_minimas_fase_i(
    columnas_insert: list[dict[str, Any]],
    columnas_requeridas: list[str],
    nombre_tabla: str,
) -> str | None:
    """
    Valida columnas mínimas para insertar.
    """
    nombres = {
        str(col["sql"]).lower()
        for col in columnas_insert
    }

    faltantes = [
        columna
        for columna in columnas_requeridas
        if columna.lower() not in nombres
    ]

    if faltantes:
        return (
            f"Faltan columnas requeridas para {nombre_tabla}: "
            + ", ".join(faltantes)
        )

    return None


def insertar_dataframe_sql_fase_i(
    cursor: Any,
    schema: str,
    tabla: str,
    df_insert: pd.DataFrame,
    tamano_lote: int = 1000,
) -> int:
    """
    Inserta un DataFrame en SQL Server por lotes.
    """
    if df_insert.empty:
        return 0

    columnas = list(df_insert.columns)
    tabla_sql = nombre_tabla_sql_fase_i(schema, tabla)

    columnas_sql = ", ".join(
        sql_identificador_aster(columna)
        for columna in columnas
    )
    placeholders = ", ".join("?" for _ in columnas)

    sql_insert = cargar_sql("aster/insert_table.sql").format(
        tabla=tabla_sql,
        columnas=columnas_sql,
        placeholders=placeholders,
    )

    total_insertados = 0
    cursor.fast_executemany = True

    for inicio in range(0, len(df_insert), tamano_lote):
        bloque = df_insert.iloc[inicio : inicio + tamano_lote]

        valores = [
            tuple(
                limpiar_parametro_sql_aster(row[columna])
                for columna in columnas
            )
            for _, row in bloque.iterrows()
        ]

        cursor.executemany(sql_insert, valores)
        total_insertados += len(valores)

    return total_insertados


def validar_columnas_duplicado_comentarios_fase_i(
    df_insert: pd.DataFrame,
) -> list[str]:
    """
    Clave anti-duplicados:
    id + data + usuario
    """
    columnas_clave = ["id", "data", "usuario"]

    columnas_lower = {
        str(col).lower(): str(col)
        for col in df_insert.columns
    }

    faltantes = [
        columna
        for columna in columnas_clave
        if columna.lower() not in columnas_lower
    ]

    if faltantes:
        raise ValueError(
            "No se puede validar duplicados en comentarios. Faltan columnas: "
            + ", ".join(faltantes)
        )

    return [
        columnas_lower[columna.lower()]
        for columna in columnas_clave
    ]


def validar_claves_comentarios_fase_i(
    df_insert: pd.DataFrame,
    limite_ejemplos: int = 20,
) -> list[dict[str, Any]]:
    """
    Valida que la clave id + data + usuario esté completa.
    """
    columnas_clave = validar_columnas_duplicado_comentarios_fase_i(df_insert)

    errores: list[dict[str, Any]] = []

    for idx, row in df_insert.iterrows():
        faltantes = []

        for columna in columnas_clave:
            valor = row[columna]

            if es_valor_vacio_aster(valor):
                faltantes.append(columna)

        if faltantes:
            errores.append(
                {
                    "fila": numero_fila_excel_fase_i(idx),
                    "id": row.get("id", ""),
                    "data": row.get("data", ""),
                    "usuario": row.get("usuario", ""),
                    "problema": "Clave anti-duplicados incompleta: "
                    + ", ".join(faltantes),
                }
            )

        if len(errores) >= limite_ejemplos:
            return errores

    return errores


def contar_duplicados_comentarios_fase_i(
    cursor: Any,
    schema: str,
    tabla_comentarios: str,
    df_insert: pd.DataFrame,
    limite_ejemplos: int = 10,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Valida duplicados en SQL Server usando:
    id + data + usuario
    """
    columnas_clave = validar_columnas_duplicado_comentarios_fase_i(df_insert)

    if df_insert.empty:
        return 0, []

    df_claves_base = df_insert[columnas_clave].copy()
    df_claves_base = normalizar_dataframe_sql_aster(df_claves_base)

    duplicados_origen = df_claves_base.duplicated(
        subset=columnas_clave,
        keep=False,
    )

    if duplicados_origen.any():
        ejemplos_origen = []

        for _, fila in df_claves_base.loc[
            duplicados_origen,
            columnas_clave,
        ].head(limite_ejemplos).iterrows():
            ejemplos_origen.append(
                {
                    columna: fila[columna]
                    for columna in columnas_clave
                }
            )

        return int(duplicados_origen.sum()), ejemplos_origen

    cursor.execute(
        cargar_sql("aster/drop_temp_table_if_exists.sql").format(
            tabla="#fase_i_comentarios_claves"
        )
    )

    columnas_temp_select = ",\n    ".join(
        sql_identificador_aster(columna)
        for columna in columnas_clave
    )

    cursor.execute(
        cargar_sql("aster/fase_i/select_top_0_claves_comentarios.sql").format(
            columnas_select=columnas_temp_select,
            tabla_temp="#fase_i_comentarios_claves",
            tabla_origen=nombre_tabla_sql_fase_i(schema, tabla_comentarios),
        )
    )

    df_claves = df_claves_base.drop_duplicates().copy()

    columnas_sql = ", ".join(
        sql_identificador_aster(columna)
        for columna in columnas_clave
    )
    placeholders = ", ".join("?" for _ in columnas_clave)

    sql_insert_temp = cargar_sql("aster/insert_table.sql").format(
        tabla="#fase_i_comentarios_claves",
        columnas=columnas_sql,
        placeholders=placeholders,
    )

    valores_temp = [
        tuple(
            limpiar_parametro_sql_aster(row[columna])
            for columna in columnas_clave
        )
        for _, row in df_claves.iterrows()
    ]

    cursor.fast_executemany = True
    cursor.executemany(sql_insert_temp, valores_temp)

    condiciones_join = []

    for columna in columnas_clave:
        col = sql_identificador_aster(columna)

        if columna.lower() in {"data", "usuario"}:
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

    sql_ejemplos = cargar_sql("aster/select_duplicados_temp.sql").format(
        limite=limite_ejemplos,
        columnas_select=columnas_select,
        tabla_origen=nombre_tabla_sql_fase_i(schema, tabla_comentarios),
        tabla_temp="#fase_i_comentarios_claves",
        join_sql=join_sql,
    )

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


def ejecutar_fase_i_aster(
    data_dir: str,
    fecha_raw: str,
    fecha_default: str,
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla_usuarios: str,
    tabla_comentarios: str,
    db_usuarios: str,
    db_gestion: str,
) -> dict[str, Any]:
    """
    Ejecuta Fase I completa.

    Hace COMMIT solo si todo termina correctamente.
    Hace ROLLBACK ante error, duplicados o claves incompletas.
    """
    conn_sql = None
    pipeline: list[dict[str, Any]] = []

    conexion_normalizada = str(conexion or "local").strip().lower()

    if conexion_normalizada not in {"local", "remoto"}:
        conexion_normalizada = "local"

    try:
        fecha_yyyymmdd = obtener_fecha_fase_i(
            fecha_raw=fecha_raw,
            fecha_default=fecha_default,
        )

        entidades, ruta_entidades = leer_entidades_fase_i(
            data_dir=data_dir,
            fecha_yyyymmdd=fecha_yyyymmdd,
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            1,
            "Leer entidades filtro",
            ruta_entidades,
            "Filtro entidad IN (...)",
            "Traídos",
            len(entidades),
        )

        df_usuarios = leer_usuarios_mysql_fase_i(db_usuarios)

        agregar_paso_pipeline_fase_i(
            pipeline,
            2,
            "Traer usuarios",
            "MySQL usuarios.crm",
            "Python DataFrame usuarios",
            "Traídos",
            len(df_usuarios),
        )

        df_comentarios = leer_comentarios_mysql_fase_i(
            db_gestion=db_gestion,
            fecha_yyyymmdd=fecha_yyyymmdd,
            entidades=entidades,
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            3,
            "Traer comentarios",
            "MySQL gestioncomercial.comentarios excluyendo SystemUser",
            "Python DataFrame comentarios",
            "Traídos",
            len(df_comentarios),
        )

        columnas_clave_origen = ["id", "fecha", "fechainicio", "telefono"]

        faltan_origen = [
            columna
            for columna in columnas_clave_origen
            if columna not in df_comentarios.columns
        ]

        if faltan_origen:
            return {
                "success": False,
                "status": "faltan_columnas_origen",
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "conexion": conexion_normalizada,
                "ruta_entidades": ruta_entidades,
                "total_entidades": len(entidades),
                "usuarios_leidos": len(df_usuarios),
                "comentarios_leidos": len(df_comentarios),
                "pipeline": pipeline,
                "error": "Faltan columnas clave en origen MySQL comentarios: "
                + ", ".join(faltan_origen),
            }

        df_comentarios = transformar_comentarios_fase_i(df_comentarios)

        columnas_sql_usuarios = obtener_columnas_sqlserver_tabla(
            conexion=conexion_normalizada,
            sql_local=sql_local,
            sql_remoto=sql_remoto,
            base=base,
            schema=schema,
            tabla=tabla_usuarios,
        )

        columnas_sql_comentarios = obtener_columnas_sqlserver_tabla(
            conexion=conexion_normalizada,
            sql_local=sql_local,
            sql_remoto=sql_remoto,
            base=base,
            schema=schema,
            tabla=tabla_comentarios,
        )

        columnas_insert_usuarios = preparar_columnas_insert_fase_i(
            df_usuarios,
            columnas_sql_usuarios,
        )

        columnas_insert_comentarios = preparar_columnas_insert_fase_i(
            df_comentarios,
            columnas_sql_comentarios,
        )

        error_usuarios = validar_columnas_minimas_fase_i(
            columnas_insert_usuarios,
            ["id", "usuario"],
            "usuarios",
        )

        if error_usuarios:
            return {
                "success": False,
                "status": "error_columnas",
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "conexion": conexion_normalizada,
                "ruta_entidades": ruta_entidades,
                "total_entidades": len(entidades),
                "usuarios_leidos": len(df_usuarios),
                "comentarios_leidos": len(df_comentarios),
                "pipeline": pipeline,
                "error": error_usuarios,
            }

        error_comentarios = validar_columnas_minimas_fase_i(
            columnas_insert_comentarios,
            ["id", "data", "usuario", "entidad"],
            "comentarios",
        )

        if error_comentarios:
            return {
                "success": False,
                "status": "error_columnas",
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "conexion": conexion_normalizada,
                "ruta_entidades": ruta_entidades,
                "total_entidades": len(entidades),
                "usuarios_leidos": len(df_usuarios),
                "comentarios_leidos": len(df_comentarios),
                "pipeline": pipeline,
                "error": error_comentarios,
            }

        df_insert_usuarios = construir_dataframe_insert_fase_i(
            df_usuarios,
            columnas_insert_usuarios,
        )

        df_insert_comentarios = construir_dataframe_insert_fase_i(
            df_comentarios,
            columnas_insert_comentarios,
        )

        errores_clave = validar_claves_comentarios_fase_i(
            df_insert_comentarios
        )

        if errores_clave:
            return {
                "success": False,
                "status": "claves_invalidas",
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "conexion": conexion_normalizada,
                "ruta_entidades": ruta_entidades,
                "total_entidades": len(entidades),
                "usuarios_leidos": len(df_usuarios),
                "comentarios_leidos": len(df_comentarios),
                "usuarios_insertados": 0,
                "comentarios_insertados": 0,
                "errores_clave": errores_clave,
                "pipeline": pipeline,
            }

        cadena = obtener_cadena_sqlserver_aster(
            conexion=conexion_normalizada,
            sql_local=sql_local,
            sql_remoto=sql_remoto,
            database_default=base,
        )

        conn_sql = pyodbc.connect(cadena, timeout=10)
        conn_sql.timeout = 120

        cursor = conn_sql.cursor()
        cursor.execute(sql_use_database_aster(base))

        total_duplicados, ejemplos_duplicados = contar_duplicados_comentarios_fase_i(
            cursor=cursor,
            schema=schema,
            tabla_comentarios=tabla_comentarios,
            df_insert=df_insert_comentarios,
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            4,
            "Validar duplicados comentarios",
            "Clave id + data + usuario",
            nombre_tabla_sql_fase_i(schema, tabla_comentarios),
            "Duplicados detectados",
            total_duplicados,
            "OK" if total_duplicados == 0 else "ERROR",
        )

        if total_duplicados > 0:
            conn_sql.rollback()

            return {
                "success": False,
                "status": "duplicados",
                "fecha_yyyymmdd": fecha_yyyymmdd,
                "conexion": conexion_normalizada,
                "ruta_entidades": ruta_entidades,
                "total_entidades": len(entidades),
                "usuarios_leidos": len(df_usuarios),
                "comentarios_leidos": len(df_comentarios),
                "usuarios_insertados": 0,
                "comentarios_insertados": 0,
                "total_duplicados": total_duplicados,
                "ejemplos_duplicados": ejemplos_duplicados,
                "pipeline": pipeline,
            }

        cursor.execute(
            cargar_sql("aster/fase_i/count_table.sql").format(
                tabla=nombre_tabla_sql_fase_i(schema, tabla_usuarios)
            )
        )
        row_usuarios_antes = cursor.fetchone()
        usuarios_borrados = (
            int(row_usuarios_antes[0] or 0)
            if row_usuarios_antes
            else 0
        )

        cursor.execute(
            cargar_sql("aster/fase_i/delete_table.sql").format(
                tabla=nombre_tabla_sql_fase_i(schema, tabla_usuarios)
            )
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            5,
            "Borrar usuarios destino",
            nombre_tabla_sql_fase_i(schema, tabla_usuarios),
            nombre_tabla_sql_fase_i(schema, tabla_usuarios),
            "Borrados",
            usuarios_borrados,
        )

        usuarios_insertados = insertar_dataframe_sql_fase_i(
            cursor=cursor,
            schema=schema,
            tabla=tabla_usuarios,
            df_insert=df_insert_usuarios,
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            6,
            "Insertar usuarios",
            "Python DataFrame usuarios",
            nombre_tabla_sql_fase_i(schema, tabla_usuarios),
            "Insertados",
            usuarios_insertados,
        )

        comentarios_insertados = insertar_dataframe_sql_fase_i(
            cursor=cursor,
            schema=schema,
            tabla=tabla_comentarios,
            df_insert=df_insert_comentarios,
        )

        agregar_paso_pipeline_fase_i(
            pipeline,
            7,
            "Insertar comentarios",
            "Python DataFrame comentarios",
            nombre_tabla_sql_fase_i(schema, tabla_comentarios),
            "Insertados",
            comentarios_insertados,
        )

        conn_sql.commit()

        return {
            "success": True,
            "status": "correcto",
            "fecha_yyyymmdd": fecha_yyyymmdd,
            "conexion": conexion_normalizada,
            "ruta_entidades": ruta_entidades,
            "total_entidades": len(entidades),
            "usuarios_leidos": len(df_usuarios),
            "usuarios_insertados": usuarios_insertados,
            "comentarios_leidos": len(df_comentarios),
            "comentarios_insertados": comentarios_insertados,
            "pipeline": pipeline,
        }

    except Exception as exc:
        if conn_sql is not None:
            try:
                conn_sql.rollback()
            except Exception:
                pass

        return {
            "success": False,
            "status": "error",
            "conexion": conexion_normalizada,
            "error": str(exc),
            "pipeline": pipeline,
        }

    finally:
        if conn_sql is not None:
            conn_sql.close()

