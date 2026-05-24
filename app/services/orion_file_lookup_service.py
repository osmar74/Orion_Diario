"""
Servicios de búsqueda de archivos ORION.

Este módulo centraliza búsquedas físicas de archivos dentro de:

data\\YYYYMMDD\\Orion
├── Discador
├── Causales
├── Lotes
└── Consolidados

La idea es evitar que los controladores tengan lógica de os.listdir,
prioridades y selección de archivos.
"""

from __future__ import annotations

import os


def buscar_archivo_discador_procesamiento(carpeta_orion: str) -> str | None:
    """
    Busca el archivo Discador fuente para Fase F: Procesar Discador.

    Prioridad:
    1. data\\YYYYMMDD\\Orion\\Discador
    2. data\\YYYYMMDD\\Orion

    Acepta archivos Excel que contengan 'discador' en el nombre.
    """
    carpetas_busqueda = [
        os.path.join(carpeta_orion, "Discador"),
        carpeta_orion,
    ]

    candidatos: list[dict] = []

    for carpeta in carpetas_busqueda:
        if not os.path.isdir(carpeta):
            continue

        for archivo in os.listdir(carpeta):
            nombre = archivo.lower()

            if not nombre.endswith(".xlsx"):
                continue

            if "discador" not in nombre:
                continue

            ruta = os.path.join(carpeta, archivo)

            prioridad = 0

            if os.path.basename(carpeta).lower() == "discador":
                prioridad += 10

            if "consolidado" in nombre:
                prioridad += 3

            if "limpio" in nombre:
                prioridad += 1

            candidatos.append(
                {
                    "ruta": ruta,
                    "prioridad": prioridad,
                    "modificado": os.path.getmtime(ruta),
                }
            )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda item: (item["prioridad"], item["modificado"]),
        reverse=True,
    )

    return str(candidatos[0]["ruta"])


def buscar_archivo_discador_para_lotes(carpeta_orion: str) -> str | None:
    """
    Busca el Discador consolidado o limpio para asignar Nombre_Lote.

    Prioridad:
    1. data\\YYYYMMDD\\Orion\\Consolidados
    2. data\\YYYYMMDD\\Orion\\Discador
    3. data\\YYYYMMDD\\Orion
    """
    carpetas_busqueda = [
        os.path.join(carpeta_orion, "Consolidados"),
        os.path.join(carpeta_orion, "Discador"),
        carpeta_orion,
    ]

    candidatos: list[dict] = []

    for carpeta in carpetas_busqueda:
        if not os.path.isdir(carpeta):
            continue

        for archivo in os.listdir(carpeta):
            nombre = archivo.lower()

            if not nombre.endswith(".xlsx"):
                continue

            if "discador" not in nombre:
                continue

            if "limpio" not in nombre and "consolidado" not in nombre:
                continue

            ruta = os.path.join(carpeta, archivo)

            prioridad = 0

            if os.path.basename(carpeta).lower() == "consolidados":
                prioridad += 10

            if "limpio" in nombre:
                prioridad += 2

            if "consolidado" in nombre:
                prioridad += 1

            candidatos.append(
                {
                    "ruta": ruta,
                    "prioridad": prioridad,
                    "modificado": os.path.getmtime(ruta),
                }
            )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda item: (item["prioridad"], item["modificado"]),
        reverse=True,
    )

    return str(candidatos[0]["ruta"])


def buscar_archivo_consolidado_orion(
    carpeta_orion: str,
    tipo: str,
) -> tuple[str | None, str | None]:
    """
    Busca archivos consolidados ORION en:

    data\\YYYYMMDD\\Orion\\Consolidados

    Tipos:
    - causales
    - lote
    - discador
    """
    carpeta_consolidados = os.path.join(carpeta_orion, "Consolidados")

    if not os.path.isdir(carpeta_consolidados):
        return None, None

    archivos: list[str] = []

    for archivo in os.listdir(carpeta_consolidados):
        nombre = archivo.lower()

        if not nombre.endswith(".xlsx"):
            continue

        if tipo == "causales" and nombre.startswith("causales_consolidado"):
            archivos.append(archivo)

        elif tipo == "lote" and nombre.startswith("lote_consolidado"):
            archivos.append(archivo)

        elif tipo == "discador":
            if "discador" in nombre and nombre.endswith("consolidado.xlsx"):
                archivos.append(archivo)

    if not archivos:
        return None, None

    archivos.sort()

    nombre_archivo = archivos[0]
    ruta_archivo = os.path.join(carpeta_consolidados, nombre_archivo)

    return ruta_archivo, nombre_archivo