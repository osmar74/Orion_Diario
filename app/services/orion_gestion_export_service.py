"""
Servicio de exportación final Gestión ORION.

Responsabilidad:
- Leer archivo temporal temp_consolidado_*.pkl.
- Aplicar limpieza de Fecha_Compromiso según descripciones seleccionadas.
- Calcular estadísticas.
- Exportar YYYYMMDD_Gestion_orion.xlsx en data\\YYYYMMDD\\Orion\\Salidas.
- Devolver resultado estructurado al controlador.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import pandas as pd

from app.services.daily_paths import normalizar_fecha_yyyymmdd, ruta_orion


def _valor_con_dato_serie(serie: pd.Series) -> pd.Series:
    """
    Devuelve máscara de valores no nulos y no vacíos.
    """
    return (
        serie.notna()
        & (serie.astype(str).str.strip() != "")
        & (~serie.astype(str).str.strip().str.lower().isin({"nan", "nat", "none", "null"}))
    )


def exportar_gestion_orion_desde_temporal(
    data_dir: str,
    fecha: str,
    seleccionados: list[str],
    temp_id: str | None,
) -> dict[str, Any]:
    """
    Aplica filtros seleccionados y exporta el Excel final de Gestión ORION.
    """
    if not temp_id:
        return {
            "success": False,
            "error": "Falta identificador de consulta previa.",
        }

    temp_path = os.path.join(data_dir, f"temp_consolidado_{temp_id}.pkl")

    if not os.path.isfile(temp_path):
        return {
            "success": False,
            "error": "Los datos de consulta previa han expirado. Ejecute la consulta nuevamente.",
        }

    try:
        with open(temp_path, "rb") as archivo:
            df = pickle.load(archivo)

        os.remove(temp_path)

    except Exception as exc:
        return {
            "success": False,
            "error": f"Error al cargar datos: {exc}",
        }

    if not isinstance(df, pd.DataFrame):
        return {
            "success": False,
            "error": "El archivo temporal no contiene un DataFrame válido.",
        }

    columnas_requeridas = {
        "Fecha_Compromiso",
        "Descripcion Codigo De Gestion",
    }

    faltantes = sorted(columnas_requeridas - set(df.columns))

    if faltantes:
        return {
            "success": False,
            "error": "Faltan columnas requeridas para exportar Gestión ORION: "
            + ", ".join(faltantes),
        }

    fecha_yyyymmdd = normalizar_fecha_yyyymmdd(fecha)

    # Estadísticas antes.
    total_inicial = len(df)

    mask_fecha_antes = _valor_con_dato_serie(df["Fecha_Compromiso"])
    registros_con_fecha_antes = int(mask_fecha_antes.sum())
    registros_sin_fecha_antes = int(total_inicial - registros_con_fecha_antes)

    # Limpieza: para filas con fecha de compromiso y descripción seleccionada,
    # se limpia Fecha_Compromiso.
    seleccionados_normalizados = [str(valor) for valor in seleccionados]

    mask_seleccionados = df["Descripcion Codigo De Gestion"].astype(str).isin(
        seleccionados_normalizados
    )
    mask_limpiar = mask_fecha_antes & mask_seleccionados

    registros_seleccionados_por_filtro = int(mask_seleccionados.sum())
    registros_limpiados = int(mask_limpiar.sum())

    df.loc[mask_limpiar, "Fecha_Compromiso"] = None

    # Estadísticas después.
    mask_fecha_despues = _valor_con_dato_serie(df["Fecha_Compromiso"])
    registros_con_fecha_despues = int(mask_fecha_despues.sum())
    registros_sin_fecha_despues = int(total_inicial - registros_con_fecha_despues)
    registros_exportados = len(df)

    estadisticas = [
        ("Registros cargados desde consulta temporal", total_inicial),
        ("Descripciones seleccionadas", len(seleccionados_normalizados)),
        ("Registros con Fecha_Compromiso antes", registros_con_fecha_antes),
        ("Registros sin Fecha_Compromiso antes", registros_sin_fecha_antes),
        (
            "Registros que coinciden con las descripciones seleccionadas",
            registros_seleccionados_por_filtro,
        ),
        ("Registros limpiados", registros_limpiados),
        ("Registros con Fecha_Compromiso después", registros_con_fecha_despues),
        ("Registros sin Fecha_Compromiso después", registros_sin_fecha_despues),
        ("Registros exportados", registros_exportados),
    ]

    carpeta_diaria_orion = ruta_orion(data_dir, fecha_yyyymmdd)

    nombre_archivo = f"{fecha_yyyymmdd}_Gestion_orion.xlsx"

    carpeta_salidas = os.path.join(carpeta_diaria_orion, "Salidas")
    os.makedirs(carpeta_salidas, exist_ok=True)

    ruta_salida = os.path.join(carpeta_salidas, nombre_archivo)

    ruta_relativa_descarga = os.path.join(
        fecha_yyyymmdd,
        "Orion",
        "Salidas",
        nombre_archivo,
    ).replace("\\", "/")

    df.to_excel(ruta_salida, index=False)

    return {
        "success": True,
        "fecha": fecha_yyyymmdd,
        "nombre_archivo": nombre_archivo,
        "ruta_salida": ruta_salida,
        "ruta_relativa_descarga": ruta_relativa_descarga,
        "estadisticas": estadisticas,
        "registros_exportados": registros_exportados,
    }