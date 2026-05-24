"""
Servicio de historial de cargas ASTER.

Responsabilidad:
- Crear la base SQLite local de historial.
- Registrar cargas o intentos de carga ASTER.
- Consultar últimos registros de historial.

Este service evita que aster_blueprint.py maneje sqlite3 directamente.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any


def inicializar_historial_aster(db_path: str) -> None:
    """
    Crea la base SQLite local para historial de cargas ASTER si no existe.
    """
    carpeta_db = os.path.dirname(db_path)

    if carpeta_db:
        os.makedirs(carpeta_db, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS aster_load_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora_registro TEXT NOT NULL,
                fecha_proceso TEXT,
                archivo_excel TEXT,
                conexion TEXT,
                total_general_aster INTEGER,
                filas_excel INTEGER,
                registros_insertados INTEGER,
                estado TEXT,
                mensaje TEXT,
                archivo_reporte_entidades TEXT,
                ruta_reporte_entidades TEXT
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


def registrar_historial_carga_aster(
    db_path: str,
    fecha_proceso: str,
    archivo_excel: str,
    conexion: str,
    total_general_aster: int | None,
    filas_excel: int,
    registros_insertados: int,
    estado: str,
    mensaje: str,
    archivo_reporte_entidades: str = "",
    ruta_reporte_entidades: str = "",
) -> None:
    """
    Registra una carga o intento de carga ASTER en SQLite local.
    """
    inicializar_historial_aster(db_path)

    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO aster_load_history (
                fecha_hora_registro,
                fecha_proceso,
                archivo_excel,
                conexion,
                total_general_aster,
                filas_excel,
                registros_insertados,
                estado,
                mensaje,
                archivo_reporte_entidades,
                ruta_reporte_entidades
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(fecha_proceso or ""),
                str(archivo_excel or ""),
                str(conexion or ""),
                total_general_aster,
                int(filas_excel or 0),
                int(registros_insertados or 0),
                str(estado or ""),
                str(mensaje or ""),
                str(archivo_reporte_entidades or ""),
                str(ruta_reporte_entidades or ""),
            ),
        )

        conn.commit()

    finally:
        conn.close()


def obtener_historial_cargas_aster(
    db_path: str,
    limite: int = 30,
) -> list[dict[str, Any]]:
    """
    Obtiene los últimos registros del historial ASTER.
    """
    inicializar_historial_aster(db_path)

    try:
        limite = int(limite)
    except Exception:
        limite = 30

    if limite <= 0:
        limite = 30

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                fecha_hora_registro,
                fecha_proceso,
                archivo_excel,
                conexion,
                total_general_aster,
                filas_excel,
                registros_insertados,
                estado,
                mensaje,
                archivo_reporte_entidades,
                ruta_reporte_entidades
            FROM aster_load_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        )

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()

