import os

# Ruta absoluta de la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpeta donde se almacenarán los datos generados
DATA_DIR = os.path.join(BASE_DIR, 'data')