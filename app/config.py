import os


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
]


# ============================================================
# Tesseract OCR
# ============================================================

def get_tesseract_path():
    env_path = os.getenv("ORION_TESSERACT_PATH")

    if env_path and os.path.exists(env_path):
        return env_path

    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
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
# SQL Server local
# ============================================================

SQL_LOCAL = {
    "server": os.getenv("ORION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV"),
    "port": os.getenv("ORION_SQL_LOCAL_PORT", ""),
    "database": os.getenv("ORION_SQL_LOCAL_DATABASE", "Orion"),
    "auth": os.getenv("ORION_SQL_LOCAL_AUTH", "sql"),
    "username": os.getenv("ORION_SQL_LOCAL_USERNAME", "Admin1"),
    "password": os.getenv("ORION_SQL_LOCAL_PASSWORD", "1234"),
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
    "password": os.getenv("ORION_SQL_REMOTO_PASSWORD", "1234"),
}