"""
Servicio de normalización ASTER.

Responsabilidad:
- Normalizar encabezados del Excel ASTER.
- Evitar nombres duplicados.
- Guardar el archivo normalizado en:
  data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Normalizado
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import pandas as pd

from app.services.daily_paths import ruta_aster_subcarpeta


def normalizar_encabezado_aster(encabezado: Any) -> str:
    """
    Normaliza un encabezado ASTER.

    Reglas:
    - Quitar acentos.
    - Reemplazar espacios, /, *, - por _
    - Eliminar caracteres especiales no necesarios.
    - Colapsar múltiples guiones bajos.
    """
    texto = str(encabezado).strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(car for car in texto if not unicodedata.combining(car))

    texto = re.sub(r"[\s/\*\-]+", "_", texto)
    texto = re.sub(r"[^A-Za-z0-9_]", "", texto)
    texto = re.sub(r"_+", "_", texto)
    texto = texto.strip("_")

    if not texto:
        texto = "Columna"

    return texto


def normalizar_lista_encabezados_aster(columnas: list[Any]) -> list[str]:
    """
    Normaliza una lista de encabezados y evita nombres duplicados.
    """
    columnas_normalizadas: list[str] = []
    contador: dict[str, int] = {}

    for columna in columnas:
        nombre_base = normalizar_encabezado_aster(columna)

        if nombre_base not in contador:
            contador[nombre_base] = 1
            columnas_normalizadas.append(nombre_base)
            continue

        contador[nombre_base] += 1
        columnas_normalizadas.append(f"{nombre_base}_{contador[nombre_base]}")

    return columnas_normalizadas


def _resolver_fecha_para_normalizado(
    fecha_yyyymmdd: str,
    ruta_archivo: str,
) -> str:
    """
    Resuelve fecha YYYYMMDD usando:
    1. fecha recibida
    2. nombre del archivo
    """
    fecha_limpia = re.sub(r"[^0-9]", "", fecha_yyyymmdd or "")

    if len(fecha_limpia) >= 8:
        return fecha_limpia[:8]

    coincidencia_fecha = re.search(
        r"(\d{8})",
        os.path.basename(ruta_archivo),
    )

    if coincidencia_fecha:
        return coincidencia_fecha.group(1)

    return ""


def normalizar_archivo_aster(
    data_dir: str,
    ruta_archivo: str,
    fecha_yyyymmdd: str = "",
) -> dict[str, Any]:
    """
    Normaliza encabezados de archivo ASTER y exporta copia normalizada.

    Devuelve:
    - ruta_normalizado
    - columnas_originales
    - columnas_normalizadas
    """
    ruta_archivo = str(ruta_archivo or "").strip()

    if not ruta_archivo:
        return {
            "success": False,
            "error": "No hay archivo ASTER copiado en sesión. Primero ejecute la Fase B.",
        }

    if not os.path.isfile(ruta_archivo):
        return {
            "success": False,
            "error": "El archivo ASTER no existe en la ruta indicada.",
            "ruta_archivo": ruta_archivo,
        }

    fecha_resuelta = _resolver_fecha_para_normalizado(
        fecha_yyyymmdd,
        ruta_archivo,
    )

    if not fecha_resuelta:
        return {
            "success": False,
            "error": "No se pudo determinar la fecha del proceso ASTER para guardar el archivo normalizado.",
        }

    df = pd.read_excel(ruta_archivo, dtype=str)

    columnas_originales = list(df.columns)
    columnas_normalizadas = normalizar_lista_encabezados_aster(columnas_originales)

    df.columns = columnas_normalizadas

    carpeta_normalizado = ruta_aster_subcarpeta(
        data_dir,
        fecha_resuelta,
        "Normalizado",
    )
    os.makedirs(carpeta_normalizado, exist_ok=True)

    nombre_original = os.path.basename(ruta_archivo)
    nombre_base, extension = os.path.splitext(nombre_original)

    if nombre_base.lower().endswith("_normalizado"):
        nombre_normalizado = f"{nombre_base}{extension}"
    else:
        nombre_normalizado = f"{nombre_base}_normalizado{extension}"

    ruta_normalizado = os.path.join(
        carpeta_normalizado,
        nombre_normalizado,
    )

    df.to_excel(ruta_normalizado, index=False)

    return {
        "success": True,
        "fecha_yyyymmdd": fecha_resuelta,
        "ruta_origen": ruta_archivo,
        "ruta_normalizado": ruta_normalizado,
        "columnas_originales": [str(col) for col in columnas_originales],
        "columnas_normalizadas": columnas_normalizadas,
    }
    
