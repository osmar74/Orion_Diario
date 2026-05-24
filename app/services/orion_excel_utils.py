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

def generar_preview_data(
    df: pd.DataFrame,
    filas: int = 10,
) -> dict[str, Any]:
    """
    Genera datos de preview sin HTML.

    El renderer será responsable de convertir esto a tabla HTML.
    """
    if df is None or df.empty:
        return {
            "columns": [],
            "rows": [],
        }

    preview_df = df.head(filas).copy()
    preview_df = preview_df.where(pd.notna(preview_df), "")

    columnas = [str(col) for col in preview_df.columns]
    filas_preview = []

    for _, row in preview_df.iterrows():
        fila = {}

        for col in preview_df.columns:
            valor = row[col]
            fila[str(col)] = "" if pd.isna(valor) else str(valor)

        filas_preview.append(fila)

    return {
        "columns": columnas,
        "rows": filas_preview,
    }
    
