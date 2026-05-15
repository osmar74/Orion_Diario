import os

# Ruta absoluta de la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpeta donde se almacenarán los datos generados
DATA_DIR = os.path.join(BASE_DIR, "data")

# Unidad de red para archivos Orion (dejar el % literal, Windows lo maneja)
# Posibles rutas de red (UNC y unidad mapeada)
RED_BASE_PATHS = [
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion"
]

# Ruta del ejecutable de Tesseract-OCR (instalación por defecto en Windows)
TESSERACT_PATH = r"D:\Programs\Tesseract-OCR\tesseract.exe"

# Base de datos de logs
LOG_DB_PATH = os.path.join(DATA_DIR, "orion_logs.db")

# Configuración de conexiones a SQL Server
SQL_LOCAL = {
    'server': r'(localdb)\MSSQLLocalDB',
    'port': '',                     # no se usa para LocalDB
    'database': 'Orion',
    'auth': 'windows',
    'username': '',
    'password': ''
}

SQL_REMOTO = {
    'server': '172.24.80.32',       # o 'VC-EIDER'
    'port': '1433',
    'database': 'Orion',
    'auth': 'sql',
    'username': 'Admin1',
    'password': '1234'
}
