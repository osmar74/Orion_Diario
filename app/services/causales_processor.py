import os
import re
from typing import Dict, Optional

import pandas as pd

from app.services.log_service import LogService


class CausalesProcessor:
    """Procesa archivos de causales: salto de filas, filtrado y normalización."""

    COLUMNAS_REQUERIDAS = ['Campaña', 'Tipo de evento', 'Usuario']

    def __init__(self, log_service: Optional[LogService] = None):
        self.log_service = log_service

    def normalizar_usuario(self, usuario: str) -> str:
        """Elimina prefijos numéricos y guiones (ej. '1453-Miguel Angel' → 'Miguel Angel')."""
        if pd.isna(usuario):
            return usuario
        return re.sub(r'^\d+-', '', usuario).strip()

    def procesar(
        self,
        ruta_archivo: str,
        carpeta_salida: str
    ) -> Dict:
        """
        Procesa un archivo de causales.

        Returns:
            Diccionario con success, total_validos, total_no_validos, rutas y mensaje.
        """
        resultado = {
            'success': False,
            'total_validos': 0,
            'total_no_validos': 0,
            'ruta_limpio': '',
            'ruta_no_validos': '',
            'mensaje': ''
        }

        if self.log_service:
            self.log_service.log('4.2', 'Procesar Causales', 'info',
                                 f'Iniciando procesamiento de {ruta_archivo}')

        try:
            # Leer ignorando las 2 primeras filas (datos sucios)
            df = pd.read_excel(ruta_archivo, skiprows=2, dtype=str)

            # Validar columnas necesarias
            faltantes = set(self.COLUMNAS_REQUERIDAS) - set(df.columns)
            if faltantes:
                raise ValueError(f"Columnas faltantes: {faltantes}")

            # Filtrar
            mascara_campania = df['Campaña'] == 'Cobranzas Hogar 0-30 días'
            mascara_evento = df['Tipo de evento'] == 'Categorización'
            mascara_total = mascara_campania & mascara_evento

            df_validos = df[mascara_total].copy()
            df_no_validos = df[~mascara_total].copy()

            # Normalizar columna Usuario
            if 'Usuario' in df_validos.columns:
                df_validos['Usuario'] = df_validos['Usuario'].apply(
                    self.normalizar_usuario
                )

            # Guardar archivos
            base = os.path.splitext(os.path.basename(ruta_archivo))[0]
            ruta_limpio = os.path.join(carpeta_salida, f"{base}_limpio.xlsx")
            ruta_no_validos = os.path.join(carpeta_salida, f"{base}_no_validos.xlsx")

            os.makedirs(carpeta_salida, exist_ok=True)
            df_validos.to_excel(ruta_limpio, index=False)
            df_no_validos.to_excel(ruta_no_validos, index=False)

            if self.log_service:
                self.log_service.log('4.2', 'Procesar Causales', 'éxito',
                                     f'Válidos: {len(df_validos)}, No válidos: {len(df_no_validos)}')

            resultado.update({
                'success': True,
                'total_validos': len(df_validos),
                'total_no_validos': len(df_no_validos),
                'ruta_limpio': ruta_limpio,
                'ruta_no_validos': ruta_no_validos,
                'mensaje': "Procesamiento de causales completado correctamente."
            })

        except Exception as e:
            if self.log_service:
                self.log_service.log('4.2', 'Procesar Causales', 'error', str(e))
            resultado['mensaje'] = f"Error en procesamiento de causales: {e}"

        return resultado