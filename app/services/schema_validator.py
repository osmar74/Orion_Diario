"""
Validaciones de esquema SQL Server antes de insertar datos.

Este módulo evita errores como:
String or binary data would be truncated

La idea es validar los datos del DataFrame contra las longitudes reales
definidas en INFORMATION_SCHEMA.COLUMNS antes de ejecutar el INSERT.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


TIPOS_TEXTO_SQL = {
    "char",
    "nchar",
    "varchar",
    "nvarchar",
}


@dataclass
class ColumnaTextoSQL:
    tabla: str
    columna: str
    tipo_sql: str
    longitud_maxima: int


@dataclass
class ErrorLongitudSQL:
    tabla: str
    columna: str
    tipo_sql: str
    longitud_maxima: int
    longitud_detectada: int
    cantidad_filas: int
    ejemplos: list[str]


def obtener_columnas_texto_sql(conn: Any, tabla_destino: str) -> list[ColumnaTextoSQL]:
    """
    Obtiene columnas de texto con longitud limitada desde SQL Server.

    Se ignoran columnas con CHARACTER_MAXIMUM_LENGTH NULL o -1.
    - NULL: tipos no textuales.
    - -1: varchar(max), nvarchar(max), varbinary(max), etc.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
          AND DATA_TYPE IN ('char', 'nchar', 'varchar', 'nvarchar')
          AND CHARACTER_MAXIMUM_LENGTH IS NOT NULL
          AND CHARACTER_MAXIMUM_LENGTH > 0
        ORDER BY ORDINAL_POSITION
        """,
        tabla_destino,
    )

    columnas: list[ColumnaTextoSQL] = []

    for row in cursor.fetchall():
        columnas.append(
            ColumnaTextoSQL(
                tabla=tabla_destino,
                columna=str(row.COLUMN_NAME),
                tipo_sql=str(row.DATA_TYPE),
                longitud_maxima=int(row.CHARACTER_MAXIMUM_LENGTH),
            )
        )

    return columnas


def _normalizar_valor_para_longitud(valor: Any) -> str | None:
    """
    Convierte un valor a texto para medir longitud.

    Retorna None si el valor debe considerarse vacío/nulo.
    """
    if pd.isna(valor):
        return None

    texto = str(valor)

    if texto.strip() == "":
        return None

    if texto.strip().lower() in {"nan", "nat", "none", "null"}:
        return None

    return texto


def validar_longitudes_dataframe(
    df: pd.DataFrame,
    columnas_texto: list[ColumnaTextoSQL],
    max_ejemplos_por_columna: int = 5,
) -> list[ErrorLongitudSQL]:
    """
    Valida que los valores del DataFrame no excedan la longitud SQL.

    Solo valida columnas que:
    - existen en el DataFrame
    - son columnas de texto SQL con longitud limitada
    """
    errores: list[ErrorLongitudSQL] = []

    for col_sql in columnas_texto:
        if col_sql.columna not in df.columns:
            continue

        serie_texto = df[col_sql.columna].map(_normalizar_valor_para_longitud)
        longitudes = serie_texto.map(lambda valor: len(valor) if valor is not None else 0)

        mask_excede = longitudes > col_sql.longitud_maxima

        if not mask_excede.any():
            continue

        valores_excedidos = serie_texto[mask_excede]
        longitudes_excedidas = longitudes[mask_excede]

        ejemplos: list[str] = []

        for valor in valores_excedidos.dropna().head(max_ejemplos_por_columna):
            texto = str(valor)

            if len(texto) > 120:
                texto = texto[:117] + "..."

            ejemplos.append(texto)

        errores.append(
            ErrorLongitudSQL(
                tabla=col_sql.tabla,
                columna=col_sql.columna,
                tipo_sql=col_sql.tipo_sql,
                longitud_maxima=col_sql.longitud_maxima,
                longitud_detectada=int(longitudes_excedidas.max()),
                cantidad_filas=int(mask_excede.sum()),
                ejemplos=ejemplos,
            )
        )

    return errores


def generar_html_errores_longitud(errores: list[ErrorLongitudSQL]) -> str:
    """
    Genera un bloque HTML amigable para mostrar errores de longitud.
    """
    if not errores:
        return ""

    html = """
    <div class='log-line error'>
        ❌ La inserción fue bloqueada porque hay valores que exceden la longitud permitida en SQL Server.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#7a1f1f; color:#fff;'>
            <th>Tabla</th>
            <th>Columna</th>
            <th>Tipo SQL</th>
            <th>Longitud permitida</th>
            <th>Longitud encontrada</th>
            <th>Filas afectadas</th>
            <th>Ejemplos</th>
        </tr>
    """

    for error in errores:
        ejemplos_html = "<br>".join(
            f"<code>{ejemplo}</code>" for ejemplo in error.ejemplos
        )

        html += f"""
        <tr>
            <td>{error.tabla}</td>
            <td><b>{error.columna}</b></td>
            <td>{error.tipo_sql}</td>
            <td>{error.longitud_maxima}</td>
            <td style='color:#dc3545; font-weight:bold;'>{error.longitud_detectada}</td>
            <td>{error.cantidad_filas}</td>
            <td>{ejemplos_html}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <div class='log-line warning' style='margin-top:10px;'>
        Sugerencia: corrija el Excel o amplíe la longitud de la columna SQL antes de volver a insertar.
    </div>
    """

    return html