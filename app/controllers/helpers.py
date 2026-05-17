"""
Funciones auxiliares compartidas por los blueprints del controlador.
"""

import re
import unicodedata

import pandas as pd
import pyodbc


def obtener_log_service():
    """
    Devuelve una instancia de LogService usando la ruta de base de datos configurada.
    """
    from app.config import LOG_DB_PATH
    from app.services.log_service import LogService

    return LogService(LOG_DB_PATH)


def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto para comparación de columnas o nombres.

    Reglas:
    - Convierte a minúsculas.
    - Reemplaza ñ por n.
    - Elimina acentos.
    - Elimina caracteres que no sean letras o números.
    """
    texto = str(texto).strip().lower()
    texto = texto.replace("ñ", "n")
    texto = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


def obtener_driver_sql_server() -> str:
    """
    Obtiene el mejor driver ODBC disponible para SQL Server.

    Prioridad:
    1. ODBC Driver 18 for SQL Server
    2. ODBC Driver 17 for SQL Server
    3. SQL Server
    """
    drivers_instalados = list(pyodbc.drivers())

    drivers_preferidos = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]

    for driver in drivers_preferidos:
        if driver in drivers_instalados:
            return driver

    raise RuntimeError(
        "No se encontró un driver ODBC para SQL Server. "
        "Instala ODBC Driver 17 o 18 for SQL Server."
    )


def construir_servidor(cfg: dict) -> str:
    """
    Construye el valor SERVER para la cadena ODBC.

    Si existe puerto, devuelve:
        servidor,puerto

    Si no existe puerto, devuelve:
        servidor
    """
    server = str(cfg.get("server", "")).strip()
    port = str(cfg.get("port", "")).strip()

    if port:
        return f"{server},{port}"

    return server


def construir_cadena_conexion(cfg: dict) -> str:
    """
    Construye la cadena de conexión ODBC a partir de un diccionario.

    Soporta:
    - Autenticación Windows.
    - Autenticación SQL Server.
    - Driver ODBC 18, 17 o driver SQL Server clásico.
    """
    driver = obtener_driver_sql_server()
    server_part = construir_servidor(cfg)

    partes = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server_part}",
        f"DATABASE={cfg['database']}",
        "TrustServerCertificate=yes",
    ]

    if driver == "ODBC Driver 18 for SQL Server":
        partes.append("Encrypt=no")

    if cfg.get("auth") == "windows":
        partes.append("Trusted_Connection=yes")
    else:
        partes.append(f"UID={cfg['username']}")
        partes.append(f"PWD={cfg['password']}")

    return ";".join(partes) + ";"


def normalizar_usuario(usuario: str) -> str:
    """
    Elimina prefijos numéricos y guiones de un nombre de usuario.
    """
    if pd.isna(usuario):
        return usuario

    return re.sub(r"^\d+-", "", str(usuario)).strip()


def mapear_columnas_archivo(columnas_archivo: list, tipo: str) -> list:
    """
    Aplica mapeo manual de columnas para un tipo de carga específico.

    Actualmente:
    - Discador:
        codigo_cliente -> NroCliente_Contrato
    """
    if tipo == "discador":
        mapeo = {
            "codigo_cliente": "NroCliente_Contrato",
        }
        return [mapeo.get(col, col) for col in columnas_archivo]

    return columnas_archivo[:]