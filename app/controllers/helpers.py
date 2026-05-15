"""
Funciones auxiliares compartidas por los blueprints del controlador.
"""

import re
import unicodedata
import pandas as pd


def obtener_log_service():
    """Devuelve una instancia de LogService usando la ruta de base de datos configurada."""
    from app.services.log_service import LogService
    from app.config import LOG_DB_PATH

    return LogService(LOG_DB_PATH)


def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto para comparación de columnas o nombres:
    - minúsculas
    - reemplaza 'ñ' por 'n'
    - elimina acentos (NFKD)
    - elimina cualquier carácter que no sea letra o dígito
    """
    texto = str(texto).strip().lower()
    texto = texto.replace("ñ", "n")
    texto = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    )
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


# def construir_cadena_conexion(cfg: dict) -> str:
#     """
#     Construye la cadena de conexión ODBC a partir de un diccionario de configuración.
#     Soporta autenticación Windows y SQL Server.
#     """
#     if cfg["auth"] == "windows":
#         return (
#             f"DRIVER={{ODBC Driver 17 for SQL Server}};"
#             f"SERVER={cfg['server']};"
#             f"DATABASE={cfg['database']};"
#             f"Trusted_Connection=yes;"
#         )
#     else:
#         return (
#             f"DRIVER={{ODBC Driver 17 for SQL Server}};"
#             f"SERVER={cfg['server']},{cfg['port']};"
#             f"DATABASE={cfg['database']};"
#             f"UID={cfg['username']};"
#             f"PWD={cfg['password']};"
#         )


def construir_cadena_conexion(cfg: dict) -> str:
    """
    Construye la cadena de conexión ODBC a partir de un diccionario de configuración.
    Soporta autenticación Windows y SQL Server.
    Agrega parámetros de cifrado requeridos por versiones modernas de SQL Server.
    """
    if cfg["auth"] == "windows":
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"Trusted_Connection=yes;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        # Si se especifica puerto, lo incluimos; si no, se omite para que el driver lo resuelva
        server_part = (
            f"{cfg['server']},{cfg['port']}" if cfg.get("port") else cfg["server"]
        )
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_part};"
            f"DATABASE={cfg['database']};"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )

def normalizar_usuario(usuario: str) -> str:
    """Elimina prefijos numéricos y guiones de un nombre de usuario."""
    if pd.isna(usuario):
        return usuario
    return re.sub(r"^\d+-", "", usuario).strip()


def mapear_columnas_archivo(columnas_archivo: list, tipo: str) -> list:
    """
    Aplica mapeo manual de columnas para un tipo de carga específico.
    Actualmente solo Discador tiene mapeo: codigo_cliente -> NroCliente_Contrato.
    Devuelve una nueva lista con los nombres mapeados.
    """
    if tipo == "discador":
        mapeo = {"codigo_cliente": "NroCliente_Contrato"}
        return [mapeo.get(col, col) for col in columnas_archivo]
    return columnas_archivo[:]  # copia sin cambios
