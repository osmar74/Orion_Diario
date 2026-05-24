import hashlib
import os
import sqlite3
from datetime import datetime

from app.config import DATA_DIR
from app.services.sql_loader import cargar_sql


LOAD_REGISTRY_DB = os.path.join(DATA_DIR, "load_registry.db")


def inicializar_load_registry():
    """
    Crea la tabla local de historial de cargas si no existe.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    with sqlite3.connect(LOAD_REGISTRY_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(cargar_sql("local/load_registry_create_table.sql"))
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
            cargar_sql("local/load_registry_find_previous.sql"),
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
            cargar_sql("local/load_registry_insert.sql"),
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