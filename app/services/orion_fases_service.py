"""
Servicio de fases iniciales ORION.

Responsabilidad:
- Normalizar fecha ORION.
- Crear estructura diaria.
- Verificar red y carpetas.
- Preparar distribución de archivos.
- Copiar archivos seleccionados.
"""

from __future__ import annotations

import os
from typing import Any

from app.services.file_manager import FileManager
from app.services.daily_paths import ruta_orion


def normalizar_fecha_orion(fecha_raw: str) -> str:
    """
    Normaliza fecha ORION a formato YYYYMM_DD.

    Acepta:
    - 202604_29
    - 20260429
    - 2026-04-29
    """
    fecha = str(fecha_raw or "").strip()

    if "_" in fecha and len(fecha.replace("_", "")) == 8:
        return fecha

    digitos = "".join(ch for ch in fecha if ch.isdigit())

    if len(digitos) == 8:
        return f"{digitos[:6]}_{digitos[6:8]}"

    return fecha


def crear_estructura_diaria_orion(
    data_dir: str,
    fecha_raw: str,
    log_service: Any = None,
) -> dict[str, Any]:
    """
    Crea estructura diaria ORION.
    """
    fecha = normalizar_fecha_orion(fecha_raw)

    fm = FileManager(data_dir, log_service=log_service)
    resultado = fm.crear_estructura_diaria(fecha)

    return {
        "fecha": fecha,
        "resultado": resultado,
    }


def verificar_red_carpetas_orion(
    data_dir: str,
    fecha_raw: str,
    log_service: Any = None,
) -> dict[str, Any]:
    """
    Verifica red y carpetas ORION.
    """
    fecha = normalizar_fecha_orion(fecha_raw)

    fm = FileManager(data_dir, log_service=log_service)
    resultado = fm.verificar_red_y_carpetas(fecha)

    return {
        "fecha": fecha,
        "resultado": resultado,
        "red_base_activa": resultado.get("red_base_usada") if resultado.get("success") else None,
    }


def preparar_distribucion_archivos_orion(
    data_dir: str,
    fecha_raw: str,
    red_base: str | None,
    log_service: Any = None,
) -> dict[str, Any]:
    """
    Prepara la distribución ORION.

    No copia archivos.
    Solo valida red, carpetas y archivos disponibles.
    """
    fecha = normalizar_fecha_orion(fecha_raw)

    if not red_base:
        return {
            "success": False,
            "status": "sin_red",
            "fecha": fecha,
            "error": "Primero debe verificar la red correctamente.",
        }

    fm = FileManager(data_dir, log_service=log_service)

    resultado_verificacion = fm.verificar_red_y_carpetas(
        fecha,
        red_base_path=red_base,
    )

    if not resultado_verificacion.get("success"):
        return {
            "success": False,
            "status": "error_verificacion",
            "fecha": fecha,
            "error": "No se puede preparar distribución: "
            + str(resultado_verificacion.get("error", "Error desconocido.")),
            "resultado_verificacion": resultado_verificacion,
        }

    carpeta_diaria = ruta_orion(data_dir, fecha)
    os.makedirs(carpeta_diaria, exist_ok=True)

    return {
        "success": True,
        "fecha": fecha,
        "carpeta_diaria": carpeta_diaria,
        "rutas_validadas": resultado_verificacion["rutas_validadas"],
        "archivos_encontrados": resultado_verificacion["archivos_encontrados"],
        "resultado_verificacion": resultado_verificacion,
    }


def _filtrar_archivos_seleccionados_orion(
    seleccionados: list[dict[str, Any]],
    archivos_disponibles: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    Filtra selección del usuario contra archivos realmente disponibles.
    """
    categorias_validas = {"Causales", "Lotes", "Discador"}

    archivos_filtrados = {
        "Causales": [],
        "Lotes": [],
        "Discador": [],
    }

    for item in seleccionados:
        if not isinstance(item, dict):
            continue

        categoria = str(item.get("categoria", "")).strip()
        archivo = str(item.get("archivo", "")).strip()

        if categoria not in categorias_validas or not archivo:
            continue

        disponibles_categoria = archivos_disponibles.get(categoria, []) or []

        if archivo not in disponibles_categoria:
            continue

        archivos_filtrados[categoria].append(archivo)

    return archivos_filtrados


def distribuir_archivos_seleccionados_orion(
    data_dir: str,
    fecha_raw: str,
    seleccionados: list[dict[str, Any]],
    red_base: str | None,
    log_service: Any = None,
) -> dict[str, Any]:
    """
    Copia solo los archivos seleccionados por el usuario.
    """
    fecha = normalizar_fecha_orion(fecha_raw)

    if not seleccionados:
        return {
            "success": False,
            "status": "sin_seleccion",
            "fecha": fecha,
            "error": "No seleccionó archivos para copiar.",
            "error_simple": True,
        }

    if not red_base:
        return {
            "success": False,
            "status": "sin_red",
            "fecha": fecha,
            "error": "Primero debe verificar la red correctamente.",
            "error_simple": True,
        }

    fm = FileManager(data_dir, log_service=log_service)

    resultado_verificacion = fm.verificar_red_y_carpetas(
        fecha,
        red_base_path=red_base,
    )

    if not resultado_verificacion.get("success"):
        return {
            "success": False,
            "status": "error_verificacion",
            "fecha": fecha,
            "error": "No se puede copiar: "
            + str(resultado_verificacion.get("error", "Error desconocido.")),
            "error_simple": True,
            "resultado_verificacion": resultado_verificacion,
        }

    archivos_filtrados = _filtrar_archivos_seleccionados_orion(
        seleccionados=seleccionados,
        archivos_disponibles=resultado_verificacion.get("archivos_encontrados", {}),
    )

    if not any(archivos_filtrados.values()):
        return {
            "success": False,
            "status": "seleccion_no_disponible",
            "fecha": fecha,
            "error": "Ninguno de los archivos seleccionados está disponible en la ruta origen.",
            "error_simple": True,
        }

    carpeta_diaria = ruta_orion(data_dir, fecha)
    os.makedirs(carpeta_diaria, exist_ok=True)

    resultado_distribucion = fm.distribuir_archivos(
        resultado_verificacion["rutas_validadas"],
        carpeta_diaria,
        archivos_filtrados,
    )

    resultado_distribucion["fecha"] = fecha
    resultado_distribucion["carpeta_diaria"] = carpeta_diaria

    return resultado_distribucion

