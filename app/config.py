import os

from dotenv import load_dotenv


# ============================================================
# Variables de entorno
# ============================================================

load_dotenv()


# ============================================================
# Rutas base del proyecto
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# Rutas de red Orion
# ============================================================

RED_BASE_PATHS = [
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_orion\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
]


# ============================================================
# Tesseract OCR
# ============================================================

def get_tesseract_path():
    env_path = os.getenv("ORION_TESSERACT_PATH")

    if env_path and os.path.exists(env_path):
        return env_path

    possible_paths = [
        r"D:\Program Files\Tesseract-OCR\tesseract.exe",
        r"D:\Programs\Tesseract-OCR\tesseract.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return r"C:\Program Files\Tesseract-OCR\tesseract.exe"


TESSERACT_PATH = get_tesseract_path()


# ============================================================
# Base de datos local de logs
# ============================================================

LOG_DB_PATH = os.path.join(DATA_DIR, "orion_logs.db")


# ============================================================
# Flask
# ============================================================

SECRET_KEY = os.getenv("ORION_FLASK_SECRET_KEY", "orion_secret_key_dev")


# ============================================================
# SQL Server local
# ============================================================

SQL_LOCAL = {
    "server": os.getenv("ORION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV"),
    "port": os.getenv("ORION_SQL_LOCAL_PORT", ""),
    "database": os.getenv("ORION_SQL_LOCAL_DATABASE", "Orion"),
    "auth": os.getenv("ORION_SQL_LOCAL_AUTH", "sql"),
    "username": os.getenv("ORION_SQL_LOCAL_USERNAME", "Admin1"),
    "password": os.getenv("ORION_SQL_LOCAL_PASSWORD", ""),
}


# ============================================================
# SQL Server remoto
# ============================================================

SQL_REMOTO = {
    "server": os.getenv("ORION_SQL_REMOTO_SERVER", "VC-EIDER"),
    "alt_server": os.getenv("ORION_SQL_REMOTO_ALT_SERVER", "172.24.80.32"),
    "port": os.getenv("ORION_SQL_REMOTO_PORT", ""),
    "alt_port": os.getenv("ORION_SQL_REMOTO_ALT_PORT", "1433"),
    "database": os.getenv("ORION_SQL_REMOTO_DATABASE", "Orion"),
    "auth": os.getenv("ORION_SQL_REMOTO_AUTH", "sql"),
    "username": os.getenv("ORION_SQL_REMOTO_USERNAME", "Admin1"),
    "password": os.getenv("ORION_SQL_REMOTO_PASSWORD", ""),
}

# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_BEGIN ===
# Puente de configuración SQL Server local para Gestión Diaria Orion.
#
# Motivo:
#   Algunos módulos usan variables ORION_SQL_LOCAL_*.
#   Otros scripts/servicios ya usaban SQLSERVER_*.
#   Este bloque unifica ambas familias de variables para evitar Login failed
#   por password vacío o variable no encontrada.
#
# Fecha generación: 2026-05-30 09:00:21.495546


def _orion_env_first(*names, default=""):
    for _name in names:
        _value = os.getenv(_name)
        if _value is not None and str(_value).strip() != "":
            return str(_value).strip()
    return default


_ORION_LOCAL_SQLSERVER_CONFIG = {
    "driver": _orion_env_first(
        "ORION_SQL_LOCAL_DRIVER",
        "SQLSERVER_DRIVER",
        default="ODBC Driver 18 for SQL Server",
    ),
    "server": _orion_env_first(
        "ORION_SQL_LOCAL_SERVER",
        "SQLSERVER_SERVER",
        default=r"localhost\SQL2025DEV",
    ),
    "database": _orion_env_first(
        "ORION_SQL_LOCAL_DATABASE",
        "SQLSERVER_DATABASE",
        default="gestioncomercial_dev",
    ),
    "username": _orion_env_first(
        "ORION_SQL_LOCAL_USERNAME",
        "SQLSERVER_USER",
        default="Admin1",
    ),
    "password": _orion_env_first(
        "ORION_SQL_LOCAL_PASSWORD",
        "SQLSERVER_PASSWORD",
        default="1234",
    ),
    "encrypt": _orion_env_first(
        "ORION_SQL_LOCAL_ENCRYPT",
        default="yes",
    ),
    "trust_server_certificate": _orion_env_first(
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
        default="yes",
    ),
}


def _orion_apply_local_sqlserver_bridge():
    """
    Aplica la conexión local correcta sobre los diccionarios de configuración
    que existan en este módulo, sin tocar configuración remota.
    """

    _candidate_names = [
        "SQL_SERVER_CONFIG",
        "SQLSERVER_CONFIG",
        "ORION_SQLSERVER_CONFIG",
        "ORION_SQL_SERVER_CONFIG",
    ]

    for _name in _candidate_names:
        _cfg = globals().get(_name)

        if not isinstance(_cfg, dict):
            continue

        # Caso típico: {"local": {...}, "remoto": {...}}
        if isinstance(_cfg.get("local"), dict):
            _cfg["local"].update(_ORION_LOCAL_SQLSERVER_CONFIG)

        # Caso alternativo: {"server": ..., "database": ...}
        elif "server" in _cfg or "database" in _cfg or "username" in _cfg:
            _cfg.update(_ORION_LOCAL_SQLSERVER_CONFIG)


_orion_apply_local_sqlserver_bridge()

# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_END ===

# === FIX_ORION_DATABASE_NAME_FINAL_BEGIN ===
# Override final para separar bases:
# - SQLSERVER_DATABASE / gestioncomercial_dev: ASTER local como reemplazo de MySQL remoto.
# - ORION_SQL_LOCAL_DATABASE / Orion: Gestión Diaria Orion, Causales, Discador y Lotes.
#
# Fecha generación: 2026-05-30 09:10:12.820474


def _orion_final_env_first(*names, default=""):
    for _name in names:
        _value = os.getenv(_name)
        if _value is not None and str(_value).strip() != "":
            return str(_value).strip()
    return default


ORION_CARGAS_SQLSERVER_CONFIG = {
    "driver": _orion_final_env_first(
        "ORION_CARGAS_SQL_DRIVER",
        "ORION_SQL_LOCAL_DRIVER",
        default="ODBC Driver 18 for SQL Server",
    ),
    "server": _orion_final_env_first(
        "ORION_CARGAS_SQL_SERVER",
        "ORION_SQL_LOCAL_SERVER",
        default=r"localhost\SQL2025DEV",
    ),
    "database": _orion_final_env_first(
        "ORION_CARGAS_SQL_DATABASE",
        "ORION_SQL_LOCAL_DATABASE",
        default="Orion",
    ),
    "username": _orion_final_env_first(
        "ORION_CARGAS_SQL_USER",
        "ORION_SQL_LOCAL_USERNAME",
        default="Admin1",
    ),
    "password": _orion_final_env_first(
        "ORION_CARGAS_SQL_PASSWORD",
        "ORION_SQL_LOCAL_PASSWORD",
        default="1234",
    ),
    "encrypt": _orion_final_env_first(
        "ORION_CARGAS_SQL_ENCRYPT",
        "ORION_SQL_LOCAL_ENCRYPT",
        default="yes",
    ),
    "trust_server_certificate": _orion_final_env_first(
        "ORION_CARGAS_SQL_TRUST_SERVER_CERTIFICATE",
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
        default="yes",
    ),
}


def get_orion_cargas_sqlserver_config():
    return dict(ORION_CARGAS_SQLSERVER_CONFIG)


def get_orion_cargas_connection_string():
    cfg = get_orion_cargas_sqlserver_config()

    return (
        f"DRIVER={{{cfg.get('driver', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={cfg.get('server', r'localhost\SQL2025DEV')};"
        f"DATABASE={cfg.get('database', 'Orion')};"
        f"UID={cfg.get('username', 'Admin1')};"
        f"PWD={cfg.get('password', '1234')};"
        f"Encrypt={cfg.get('encrypt', 'yes')};"
        f"TrustServerCertificate={cfg.get('trust_server_certificate', 'yes')};"
    )


def _apply_orion_final_database_override():
    """
    Reaplica a la configuración local de Orion la base correcta: Orion.
    Esto evita que Causales, Discador y Lotes busquen en gestioncomercial_dev.
    """

    for _name in [
        "SQL_SERVER_CONFIG",
        "SQLSERVER_CONFIG",
        "ORION_SQLSERVER_CONFIG",
        "ORION_SQL_SERVER_CONFIG",
    ]:
        _cfg = globals().get(_name)

        if not isinstance(_cfg, dict):
            continue

        if isinstance(_cfg.get("local"), dict):
            _cfg["local"].update(ORION_CARGAS_SQLSERVER_CONFIG)

        elif "server" in _cfg or "database" in _cfg or "username" in _cfg:
            _cfg.update(ORION_CARGAS_SQLSERVER_CONFIG)


_apply_orion_final_database_override()

# === FIX_ORION_DATABASE_NAME_FINAL_END ===
