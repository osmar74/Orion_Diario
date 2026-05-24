"""
Servicio de exportación de entidades ASTER.

Responsabilidad:
- Resolver entidades finales filtradas.
- Generar entidades_aster_YYYYMMDD.xlsx en:
  data\\YYYYMMDD\\Aster\\aster_YYYYMMDD\\Entidades
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from app.services.daily_paths import ruta_aster_subcarpeta


def normalizar_entidades_filtradas_finales_aster(
    entidades_validadas: list[dict[str, Any]] | Any,
    cobranza: list[dict[str, Any]] | Any,
    integral: list[dict[str, Any]] | Any,
    no_seleccionadas: list[dict[str, Any]] | Any,
) -> list[dict[str, Any]]:
    """
    Obtiene entidades filtradas finales ASTER.

    Prioridad:
    1. Entidades SQL validadas por conciliación.
    2. Bases Cobranza + Integral + No seleccionadas.
    """
    if isinstance(entidades_validadas, list) and entidades_validadas:
        origen = entidades_validadas
    else:
        origen = []

        if isinstance(cobranza, list):
            origen.extend(cobranza)

        if isinstance(integral, list):
            origen.extend(integral)

        if isinstance(no_seleccionadas, list):
            origen.extend(no_seleccionadas)

    entidades: dict[str, dict[str, Any]] = {}

    for fila in origen:
        if not isinstance(fila, dict):
            continue

        entidad = str(fila.get("entidad") or "").strip()

        if not entidad:
            continue

        try:
            numero = int(fila.get("numero") or 0)
        except Exception:
            numero = 0

        entidades[entidad] = {
            "entidad": entidad,
            "numero": numero,
            "SSS": str(fila.get("SSS") or f"'{entidad}'"),
        }

    return [
        entidades[entidad]
        for entidad in sorted(entidades.keys())
    ]


def generar_excel_entidades_aster(
    data_dir: str,
    fecha_yyyymmdd: str,
    entidades: list[dict[str, Any]] | Any,
) -> dict[str, Any]:
    """
    Genera Excel con entidades filtradas finales.

    Archivo:
    entidades_aster_YYYYMMDD.xlsx
    """
    fecha_limpia = str(fecha_yyyymmdd or "").strip()

    if not fecha_limpia:
        return {
            "success": False,
            "error": "No se recibió fecha de proceso ASTER.",
        }

    if not isinstance(entidades, list):
        entidades = []

    carpeta_entidades = ruta_aster_subcarpeta(
        data_dir,
        fecha_limpia,
        "Entidades",
    )
    os.makedirs(carpeta_entidades, exist_ok=True)

    nombre_archivo = f"entidades_aster_{fecha_limpia}.xlsx"
    ruta_archivo = os.path.join(carpeta_entidades, nombre_archivo)

    filas = []

    for idx, entidad_info in enumerate(entidades, start=1):
        if not isinstance(entidad_info, dict):
            continue

        entidad = str(entidad_info.get("entidad") or "").strip()

        if not entidad:
            continue

        try:
            numero = int(entidad_info.get("numero") or 0)
        except Exception:
            numero = 0

        filas.append(
            {
                "Nro": len(filas) + 1,
                "Entidad": entidad,
                "Numero": numero,
                "SSS": str(entidad_info.get("SSS") or f"'{entidad}'"),
            }
        )

    df_entidades = pd.DataFrame(
        filas,
        columns=["Nro", "Entidad", "Numero", "SSS"],
    )

    df_entidades.to_excel(ruta_archivo, index=False)

    return {
        "success": True,
        "ruta_archivo": ruta_archivo,
        "nombre_archivo": nombre_archivo,
        "total_entidades": len(df_entidades),
    }
