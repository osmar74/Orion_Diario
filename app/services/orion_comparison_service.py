"""
Servicio de comparación de lotes ORION.

Responsabilidad:
- Buscar consolidados ORION.
- Comparar Discador[Lote] contra Lotes[Nombre_Lote].
- Generar Resumen_Comparacion_DDMM.xlsx.
- Retornar datos estructurados para que el controlador solo arme la respuesta visual.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.services.orion_file_lookup_service import buscar_archivo_consolidado_orion


def _fecha_archivo_resumen_orion(fecha: str) -> str:
    """
    Convierte:
    - 202605_21 -> 0521
    - 20260521  -> 0521
    """
    fecha_limpia = str(fecha or "").replace("_", "")

    if len(fecha_limpia) >= 8:
        return fecha_limpia[4:8]

    return fecha_limpia


def _valores_unicos_texto(df: pd.DataFrame, columna: str) -> set[str]:
    """
    Devuelve valores únicos no vacíos como texto.
    """
    if columna not in df.columns:
        return set()

    valores = set()

    for valor in df[columna].dropna().tolist():
        texto = str(valor).strip()

        if texto:
            valores.add(texto)

    return valores


def _exportar_resumen_comparacion(
    ruta_resumen: str,
    datos_comparacion: list[dict[str, Any]],
) -> None:
    """
    Exporta Excel de resumen de comparación.
    """
    wb = Workbook()
    ws = wb.active

    if ws is None:
        ws = wb.create_sheet("Comparación")

    ws.title = "Comparación"

    ws.append(["Lote", "En Discador", "En Lotes"])

    for fila in datos_comparacion:
        ws.append(
            [
                fila["Lote"],
                fila["En Discador"],
                fila["En Lotes"],
            ]
        )

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="4F81BD",
        end_color="4F81BD",
        fill_type="solid",
    )
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col in range(1, 4):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    os.makedirs(os.path.dirname(ruta_resumen), exist_ok=True)
    wb.save(ruta_resumen)


def comparar_lotes_orion(carpeta_orion: str, fecha: str) -> dict[str, Any]:
    """
    Ejecuta comparación ORION entre:
    - Discador consolidado
    - Lote consolidado

    También valida presencia de Causales consolidado porque forma parte
    de los archivos esperados de Fase F.
    """
    carpeta_consolidados = os.path.join(carpeta_orion, "Consolidados")
    os.makedirs(carpeta_consolidados, exist_ok=True)

    ruta_disc, nombre_disc = buscar_archivo_consolidado_orion(
        carpeta_orion,
        "discador",
    )
    ruta_lotes, nombre_lotes = buscar_archivo_consolidado_orion(
        carpeta_orion,
        "lote",
    )
    ruta_caus, nombre_caus = buscar_archivo_consolidado_orion(
        carpeta_orion,
        "causales",
    )

    resultado: dict[str, Any] = {
        "success": False,
        "carpeta_consolidados": carpeta_consolidados,
        "rutas": {
            "discador": ruta_disc,
            "causales": ruta_caus,
            "lotes": ruta_lotes,
        },
        "nombres": {
            "discador": nombre_disc,
            "causales": nombre_caus,
            "lotes": nombre_lotes,
        },
        "faltantes": [],
        "comparacion": [],
        "faltan_en_discador": [],
        "faltan_en_lotes": [],
        "match_ok": False,
        "ruta_resumen": "",
        "errores": [],
    }

    faltantes = []

    if not ruta_disc:
        faltantes.append("Discador")

    if not ruta_caus:
        faltantes.append("Causales")

    if not ruta_lotes:
        faltantes.append("Lotes")

    resultado["faltantes"] = faltantes

    datos_comparacion: list[dict[str, Any]] = []

    if ruta_disc and ruta_lotes:
        try:
            df_disc = pd.read_excel(ruta_disc, dtype=str)
            df_lotes = pd.read_excel(ruta_lotes, dtype=str)

            if "Lote" not in df_disc.columns:
                resultado["errores"].append(
                    "El consolidado Discador no contiene la columna Lote."
                )

            if "Nombre_Lote" not in df_lotes.columns:
                resultado["errores"].append(
                    "El consolidado Lotes no contiene la columna Nombre_Lote."
                )

            if not resultado["errores"]:
                lotes_discador = _valores_unicos_texto(df_disc, "Lote")
                lotes_lotes = _valores_unicos_texto(df_lotes, "Nombre_Lote")

                todos_lotes = sorted(lotes_discador.union(lotes_lotes))

                for lote in todos_lotes:
                    en_discador = lote in lotes_discador
                    en_lotes = lote in lotes_lotes

                    datos_comparacion.append(
                        {
                            "Lote": lote,
                            "En Discador": "Sí" if en_discador else "No",
                            "En Lotes": "Sí" if en_lotes else "No",
                            "en_discador_bool": en_discador,
                            "en_lotes_bool": en_lotes,
                        }
                    )

                faltan_en_discador = sorted(lotes_lotes - lotes_discador)
                faltan_en_lotes = sorted(lotes_discador - lotes_lotes)

                resultado["comparacion"] = datos_comparacion
                resultado["faltan_en_discador"] = faltan_en_discador
                resultado["faltan_en_lotes"] = faltan_en_lotes
                resultado["match_ok"] = (
                    not faltan_en_discador
                    and not faltan_en_lotes
                )

        except Exception as exc:
            resultado["errores"].append(f"Error al comparar lotes: {exc}")

    fecha_archivo = _fecha_archivo_resumen_orion(fecha)

    ruta_resumen = os.path.join(
        carpeta_consolidados,
        f"Resumen_Comparacion_{fecha_archivo}.xlsx",
    )

    try:
        _exportar_resumen_comparacion(
            ruta_resumen,
            datos_comparacion,
        )
        resultado["ruta_resumen"] = ruta_resumen
    except Exception as exc:
        resultado["errores"].append(
            f"Error al generar Excel de resumen: {exc}"
        )

    resultado["success"] = not resultado["errores"]

    return resultado