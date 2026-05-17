import hashlib
import os
import sqlite3
from datetime import datetime

from app.config import DATA_DIR


LOAD_REGISTRY_DB = os.path.join(DATA_DIR, "load_registry.db")


def inicializar_load_registry():
    """
    Crea la tabla local de historial de cargas si no existe.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    with sqlite3.connect(LOAD_REGISTRY_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS load_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                conexion TEXT NOT NULL,
                tabla_destino TEXT NOT NULL,
                nombre_archivo TEXT NOT NULL,
                ruta_archivo TEXT NOT NULL,
                archivo_hash TEXT NOT NULL,
                registros_archivo INTEGER NOT NULL,
                registros_insertados INTEGER NOT NULL,
                fecha_carga TEXT NOT NULL,
                UNIQUE(tipo, conexion, tabla_destino, archivo_hash)
            )
            """
        )
        conn.commit()


def calcular_sha256(ruta_archivo):
    """
    Calcula el hash SHA256 de un archivo.

    Este hash permite identificar si el mismo archivo ya fue cargado antes.
    """
    sha256 = hashlib.sha256()

    with open(ruta_archivo, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            sha256.update(bloque)

    return sha256.hexdigest()


def buscar_carga_previa(tipo, conexion, tabla_destino, archivo_hash):
    """
    Busca si ya existe una carga registrada para el mismo archivo.
    """
    inicializar_load_registry()

    with sqlite3.connect(LOAD_REGISTRY_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                tipo,
                conexion,
                tabla_destino,
                nombre_archivo,
                ruta_archivo,
                archivo_hash,
                registros_archivo,
                registros_insertados,
                fecha_carga
            FROM load_history
            WHERE tipo = ?
              AND conexion = ?
              AND tabla_destino = ?
              AND archivo_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (tipo, conexion, tabla_destino, archivo_hash),
        )
        row = cursor.fetchone()

    return dict(row) if row else None


def registrar_carga(
    tipo,
    conexion,
    tabla_destino,
    nombre_archivo,
    ruta_archivo,
    archivo_hash,
    registros_archivo,
    registros_insertados,
):
    """
    Registra una carga exitosa.

    Si ya existe el mismo hash, no duplica el historial.
    """
    inicializar_load_registry()

    fecha_carga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(LOAD_REGISTRY_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO load_history (
                tipo,
                conexion,
                tabla_destino,
                nombre_archivo,
                ruta_archivo,
                archivo_hash,
                registros_archivo,
                registros_insertados,
                fecha_carga
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tipo,
                conexion,
                tabla_destino,
                nombre_archivo,
                ruta_archivo,
                archivo_hash,
                registros_archivo,
                registros_insertados,
                fecha_carga,
            ),
        )
        conn.commit()