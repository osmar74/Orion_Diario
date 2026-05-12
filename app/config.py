import os

# Ruta absoluta de la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpeta donde se almacenarán los datos generados
DATA_DIR = os.path.join(BASE_DIR, "data")

# Unidad de red para archivos Orion (dejar el % literal, Windows lo maneja)
RED_BASE_PATH = (
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba_carga_diaria_Aster_voip\Orion"
)
