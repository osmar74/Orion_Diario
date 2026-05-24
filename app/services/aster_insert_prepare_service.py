"""
Servicio de preparación de inserción ASTER Fase H.

Responsabilidad:
- Leer Excel ASTER normalizado.
- Comparar columnas Excel vs SQL Server.
- Determinar columnas comunes insertables.
- Validar columnas mínimas.
- Convertir datos según metadatos SQL.
- Validar datos antes del INSERT.

No inserta datos.
"""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


def tipo_excel_aster(serie: pd.Series) -> str:
    """
    Detecta un tipo general de columna Excel sin forzar parseos lentos de fecha.
    """
    serie_no_nula = serie.dropna()

    if serie_no_nula.empty:
        return "vacia"

    valores = serie_no_nula.astype(str).str.strip()
    valores_no_vacios = valores[valores != ""]

    if valores_no_vacios.empty:
        return "texto"

    muestra = valores_no_vacios.head(200)

    numeros = pd.to_numeric(
        muestra.str.replace(",", ".", regex=False),
        errors="coerce",
    )

    porcentaje_numerico = numeros.notna().mean()

    if porcentaje_numerico >= 0.9:
        numeros_validos = numeros.dropna()

        if not numeros_validos.empty and (numeros_validos % 1 == 0).all():
            return "entero"

        return "decimal"

    patron_fecha = re.compile(
        r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
    )

    porcentaje_fecha = muestra.apply(
        lambda valor: bool(patron_fecha.match(str(valor)))
    ).mean()

    if porcentaje_fecha >= 0.8:
        return "fecha_hora"

    return "texto"


def comparar_excel_vs_sql_aster(
    df: pd.DataFrame,
    columnas_sql: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compara columnas del Excel ASTER contra columnas SQL.
    """
    sql_por_nombre = {
        str(col["columna"]).lower(): col
        for col in columnas_sql
    }

    comparacion: list[dict[str, Any]] = []

    for columna_excel in df.columns:
        clave = str(columna_excel).lower()
        col_sql = sql_por_nombre.get(clave)

        existe = col_sql is not None

        comparacion.append(
            {
                "columna_excel": str(columna_excel),
                "tipo_excel": tipo_excel_aster(df[columna_excel]),
                "existe_sql": existe,
                "columna_sql": str(col_sql["columna"]) if col_sql else "",
                "tipo_sql": str(col_sql["tipo_sql"]) if col_sql else "",
                "nullable": str(col_sql["nullable"]) if col_sql else "",
                "longitud": col_sql["longitud"] if col_sql else "",
                "estado": "OK" if existe else "NO_EXISTE_EN_SQL",
            }
        )

    columnas_excel_lower = {
        str(col).lower()
        for col in df.columns
    }

    for col_sql in columnas_sql:
        clave_sql = str(col_sql["columna"]).lower()

        if clave_sql in columnas_excel_lower:
            continue

        comparacion.append(
            {
                "columna_excel": "",
                "tipo_excel": "",
                "existe_sql": False,
                "columna_sql": str(col_sql["columna"]),
                "tipo_sql": str(col_sql["tipo_sql"]),
                "nullable": str(col_sql["nullable"]),
                "longitud": col_sql["longitud"],
                "estado": "NO_EXISTE_EN_EXCEL",
            }
        )

    return comparacion


def es_valor_vacio_aster(valor: Any) -> bool:
    """
    Determina si un valor debe enviarse como NULL.
    """
    if valor is None:
        return True

    try:
        if pd.isna(valor):
            return True
    except Exception:
        pass

    texto = str(valor).strip()

    return texto == "" or texto.lower() in {"nan", "nat", "none", "null"}


def convertir_valor_sql_aster(valor: Any, tipo_sql: str) -> Any:
    """
    Convierte un valor del Excel al tipo compatible con SQL Server.
    """
    if es_valor_vacio_aster(valor):
        return None

    tipo = str(tipo_sql).lower()
    texto = str(valor).strip()

    if tipo in {"int", "bigint", "smallint", "tinyint"}:
        numero = pd.to_numeric(texto.replace(",", "."), errors="coerce")

        if pd.isna(numero):
            return None

        return int(numero)

    if tipo in {"decimal", "numeric", "money", "smallmoney"}:
        try:
            return Decimal(texto.replace(",", "."))
        except InvalidOperation:
            return None

    if tipo in {"float", "real"}:
        return float(texto.replace(",", "."))

    if tipo in {"bit"}:
        texto_lower = texto.lower()

        if texto_lower in {"1", "true", "si", "sí", "yes", "y"}:
            return 1

        if texto_lower in {"0", "false", "no", "n"}:
            return 0

        return int(float(texto.replace(",", ".")))

    if tipo in {"date"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return None

        return fecha.date()

    if tipo in {"datetime", "datetime2", "smalldatetime"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return None

        return fecha.to_pydatetime()

    if tipo in {"time"}:
        fecha = pd.to_datetime(texto, errors="coerce")

        if pd.isna(fecha):
            return texto

        return fecha.time()

    return texto


def normalizar_dataframe_sql_aster(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza un DataFrame antes de INSERT/diagnóstico SQL.
    """
    df_normalizado = df.astype(object)
    df_normalizado = df_normalizado.where(pd.notna(df_normalizado), None)

    return df_normalizado


def preparar_columnas_insert_aster(
    df: pd.DataFrame,
    columnas_sql: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Determina columnas comunes entre Excel y SQL para insertar.
    Excluye columnas identity.
    Conserva metadatos SQL para validar antes del INSERT.
    """
    excel_por_lower = {
        str(col).lower(): str(col)
        for col in df.columns
    }

    columnas_insert: list[dict[str, Any]] = []

    for col_sql in columnas_sql:
        if int(col_sql.get("is_identity") or 0) == 1:
            continue

        nombre_sql = str(col_sql["columna"])
        nombre_excel = excel_por_lower.get(nombre_sql.lower())

        if not nombre_excel:
            continue

        columnas_insert.append(
            {
                "excel": nombre_excel,
                "sql": nombre_sql,
                "tipo_sql": str(col_sql["tipo_sql"]),
                "nullable": str(col_sql["nullable"]),
                "longitud": col_sql.get("longitud"),
                "precision": col_sql.get("precision"),
                "escala": col_sql.get("escala"),
            }
        )

    return columnas_insert


def validar_columnas_minimas_insert_aster(
    columnas_insert: list[dict[str, Any]],
) -> str | None:
    """
    Valida que existan columnas mínimas para una inserción útil.
    """
    nombres = {str(col["sql"]).lower() for col in columnas_insert}

    if not nombres:
        return "No hay columnas comunes entre Excel y SQL para insertar."

    if "entidad" not in nombres:
        return "No existe columna Entidad coincidente entre Excel y SQL."

    return None


def construir_dataframe_insert_aster(
    df: pd.DataFrame,
    columnas_insert: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Construye DataFrame con columnas SQL y datos convertidos.
    """
    data_convertida: dict[str, list[Any]] = {}

    for col in columnas_insert:
        nombre_excel = str(col["excel"])
        nombre_sql = str(col["sql"])
        tipo_sql = str(col["tipo_sql"])

        data_convertida[nombre_sql] = [
            convertir_valor_sql_aster(valor, tipo_sql)
            for valor in df[nombre_excel].tolist()
        ]

    return pd.DataFrame(data_convertida)


def validar_dataframe_insert_aster(
    df_insert: pd.DataFrame,
    columnas_insert: list[dict[str, Any]],
    limite_errores: int = 100,
) -> list[dict[str, Any]]:
    """
    Valida datos antes del INSERT usando tipos reales de SQL Server.

    Detecta:
    - NULL en columnas NOT NULL.
    - enteros fuera de rango.
    - decimal/numeric fuera de precisión/escala.
    - money/smallmoney fuera de rango.
    - texto más largo que varchar/nvarchar/char/nchar.
    """
    errores: list[dict[str, Any]] = []

    info_por_columna = {
        str(col["sql"]): col
        for col in columnas_insert
    }

    rangos_enteros = {
        "tinyint": (0, 255),
        "smallint": (-32768, 32767),
        "int": (-2147483648, 2147483647),
        "bigint": (-9223372036854775808, 9223372036854775807),
    }

    rangos_money = {
        "smallmoney": (Decimal("-214748.3648"), Decimal("214748.3647")),
        "money": (
            Decimal("-922337203685477.5808"),
            Decimal("922337203685477.5807"),
        ),
    }

    for idx, row in df_insert.iterrows():
        fila_excel = int(idx) + 2

        for columna in df_insert.columns:
            info = info_por_columna.get(str(columna))

            if not info:
                continue

            valor = row[columna]
            tipo_sql = str(info.get("tipo_sql") or "").lower()
            nullable = str(info.get("nullable") or "YES").upper()
            longitud = info.get("longitud")
            precision = info.get("precision")
            escala = info.get("escala")

            if es_valor_vacio_aster(valor):
                valor = None

            if valor is None:
                if nullable == "NO":
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": "",
                            "problema": "La columna no permite NULL",
                        }
                    )

                if len(errores) >= limite_errores:
                    return errores

                continue

            if tipo_sql in rangos_enteros:
                minimo, maximo = rangos_enteros[tipo_sql]

                try:
                    valor_entero = int(valor)
                except Exception:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": valor,
                            "problema": "No se puede convertir a entero",
                        }
                    )

                    if len(errores) >= limite_errores:
                        return errores

                    continue

                if valor_entero < minimo or valor_entero > maximo:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": valor,
                            "problema": f"Valor fuera de rango permitido ({minimo} a {maximo})",
                        }
                    )

            elif tipo_sql in {"decimal", "numeric"}:
                try:
                    valor_decimal = Decimal(str(valor))
                except Exception:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": valor,
                            "problema": "No se puede convertir a decimal",
                        }
                    )

                    if len(errores) >= limite_errores:
                        return errores

                    continue

                p = int(precision or 18)
                s = int(escala or 0)
                max_enteros = p - s

                texto_decimal = format(abs(valor_decimal), "f")
                partes = texto_decimal.split(".")
                parte_entera = partes[0].lstrip("0")
                parte_decimal = partes[1].rstrip("0") if len(partes) > 1 else ""

                digitos_enteros = len(parte_entera) if parte_entera else 1
                digitos_decimales = len(parte_decimal)

                if digitos_enteros > max_enteros or digitos_decimales > s:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": f"{tipo_sql}({p},{s})",
                            "valor": valor,
                            "problema": "Valor excede precisión/escala permitida",
                        }
                    )

            elif tipo_sql in rangos_money:
                minimo, maximo = rangos_money[tipo_sql]

                try:
                    valor_decimal = Decimal(str(valor))
                except Exception:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": valor,
                            "problema": "No se puede convertir a money/smallmoney",
                        }
                    )

                    if len(errores) >= limite_errores:
                        return errores

                    continue

                if valor_decimal < minimo or valor_decimal > maximo:
                    errores.append(
                        {
                            "fila": fila_excel,
                            "columna": columna,
                            "tipo_sql": tipo_sql,
                            "valor": valor,
                            "problema": f"Valor fuera de rango permitido ({minimo} a {maximo})",
                        }
                    )

            elif tipo_sql in {"varchar", "nvarchar", "char", "nchar"}:
                if longitud not in {None, -1, ""}:
                    texto = str(valor)

                    if len(texto) > int(longitud):
                        errores.append(
                            {
                                "fila": fila_excel,
                                "columna": columna,
                                "tipo_sql": f"{tipo_sql}({longitud})",
                                "valor": texto[:150],
                                "problema": f"Texto excede longitud máxima ({longitud})",
                            }
                        )

            if len(errores) >= limite_errores:
                return errores

    return errores


def preparar_insercion_aster(
    ruta_archivo: str,
    columnas_sql: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Ejecuta preparación completa de inserción ASTER.
    No inserta datos.
    """
    ruta_archivo = str(ruta_archivo or "").strip()

    if not ruta_archivo:
        return {
            "success": False,
            "status": "sin_archivo",
            "error": "No se recibió ruta del archivo ASTER normalizado.",
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

    comparacion = comparar_excel_vs_sql_aster(df, columnas_sql)

    columnas_insert = preparar_columnas_insert_aster(df, columnas_sql)
    error_columnas = validar_columnas_minimas_insert_aster(columnas_insert)

    if error_columnas:
        return {
            "success": False,
            "status": "error_columnas",
            "error": error_columnas,
            "ruta_archivo": ruta_archivo,
            "total_registros": len(df),
            "comparacion": comparacion,
            "columnas_insert": columnas_insert,
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
            "errores_validacion": errores_validacion,
            "ruta_archivo": ruta_archivo,
            "total_registros": len(df),
            "comparacion": comparacion,
            "columnas_insert": columnas_insert,
        }

    return {
        "success": True,
        "status": "ok",
        "ruta_archivo": ruta_archivo,
        "total_registros": len(df),
        "comparacion": comparacion,
        "columnas_insert": columnas_insert,
        "columnas_insertadas": [str(col["sql"]) for col in columnas_insert],
    }

