import os
from typing import Dict, List


class FileManager:
    """Gestión de archivos y carpetas para los procesos Orion/Aister."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    def crear_estructura_diaria(self, fecha_str: str) -> Dict:
        """
        Crea la carpeta diaria con sus subcarpetas.

        Args:
            fecha_str: Cadena en formato 'YYYYMM_DD' (ej. '202605_12').

        Returns:
            Diccionario con 'success' (bool) y 'rutas' (dict de rutas creadas).
        """
        nombre_carpeta = f"orion_{fecha_str}"
        carpeta_principal = os.path.join(self.base_path, nombre_carpeta)

        subcarpetas: List[str] = [
            'Reporte_Imagen',
            'Causales',
            'Lotes',
            'Discador'
        ]

        rutas_creadas = {'principal': carpeta_principal}

        try:
            # Crear la carpeta principal
            os.makedirs(carpeta_principal, exist_ok=True)

            # Crear cada subcarpeta
            for sub in subcarpetas:
                ruta_sub = os.path.join(carpeta_principal, sub)
                os.makedirs(ruta_sub, exist_ok=True)
                rutas_creadas[sub] = ruta_sub

            return {'success': True, 'rutas': rutas_creadas}

        except OSError as e:
            return {
                'success': False,
                'error': f"Error al crear la estructura: {str(e)}"
            }