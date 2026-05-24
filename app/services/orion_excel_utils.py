"""
Utilidades comunes para procesamiento ORION.

Responsabilidad:
- Lectura estándar de Excel/CSV como texto.
- Escritura segura de Excel.
- Listado de archivos por extensión.
- Generación estándar de preview HTML.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


def listar_archivos_por_extension(
    carpeta: str,
    extension: str,
) -> list[str]:
    """
    Lista archivos de una carpeta por extensión.
    Retorna lista ordenada alfabéticamente.
    """
    if not os.path.isdir(carpeta):
        return []

    extension = extension.lower().strip()

    return sorted(
        archivo
        for archivo in os.listdir(carpeta)
        if archivo.lower().endswith(extension)
    )


def leer_excel_texto(
    ruta_archivo: str,
    skiprows: int | None = None,
) -> pd.DataFrame:
    """
    Lee Excel tratando todas las columnas como texto.
    """
    kwargs: dict[str, Any] = {"dtype": str}

    if skiprows is not None:
        kwargs["skiprows"] = skiprows

    return pd.read_excel(ruta_archivo, **kwargs)


def leer_csv_texto_latin1(
    ruta_archivo: str,
    sep: str = ";",
) -> pd.DataFrame:
    """
    Lee CSV ORION usando latin-1 y columnas como texto.
    """
    return pd.read_csv(
        ruta_archivo,
        sep=sep,
        dtype=str,
        encoding="latin-1",
    )


def escribir_excel(
    df: pd.DataFrame,
    ruta_salida: str,
) -> None:
    """
    Escribe un Excel creando la carpeta destino si no existe.
    """
    carpeta = os.path.dirname(ruta_salida)

    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    df.to_excel(ruta_salida, index=False)


def generar_preview_html(
    df: pd.DataFrame,
    filas: int = 10,
) -> str:
    """
    Genera preview HTML estándar para renderers ORION.
    """
    return df.head(filas).to_html(index=False, classes="dataframe")
