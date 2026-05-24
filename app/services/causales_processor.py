import os
import re
from typing import Dict, List, Optional

import pandas as pd

from app.services.log_service import LogService
from app.services.orion_excel_utils import (
    escribir_excel,
    generar_preview_html,
    leer_excel_texto,
    listar_archivos_por_extension,
)


class CausalesProcessor:
    """Procesa archivos de causales: salto de filas, filtrado, normalización y consolidación."""

    COLUMNAS_REQUERIDAS = ['Campaña', 'Tipo de evento', 'Usuario']

    # Sinónimos de columnas (clave canónica -> lista de variantes)
    SINONIMOS_COLUMNAS = {
        'Fecha de compromiso': ['fecha de compromiso', 'fecha de compropiso'],
        'Fecha de Compromiso Anterior': ['fecha de compromiso anterior'],
        'Ultima Fecha Pago': ['ultima fecha pago'],
        'Tipo Corte': ['tipo corte'],
        'Orden': ['orden'],
        'Pago Asignacion': ['pago asignacion'],
        'Gross': ['gross'],
        'Cuenta OLD': ['cuenta old'],
        'SITUACION_EQUIPO_CUENTA': ['situacion_equipo_cuenta'],
        'NO_USAR': ['no_usar'],
    }

    def __init__(self, log_service: Optional[LogService] = None):
        self.log_service = log_service

    def normalizar_usuario(self, usuario: str) -> str:
        """Elimina prefijos numéricos y guiones."""
        if pd.isna(usuario):
            return usuario
        return re.sub(r'^\d+-', '', usuario).strip()

    def _normalizar_texto(self, texto: str) -> str:
        """Elimina tildes, convierte a minúsculas y elimina espacios extra."""
        texto = str(texto).strip().lower()
        reemplazos = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u'}
        for acc, sin in reemplazos.items():
            texto = texto.replace(acc, sin)
        texto = re.sub(r'\s+', ' ', texto)
        return texto

    def _mapear_columnas(self, columnas_originales: List[str]) -> Dict[str, str]:
        """
        Devuelve un diccionario {nombre_original: nombre_canonico} basado en sinónimos.
        Si no se encuentra sinónimo, se usa el nombre original normalizado.
        """
        mapeo = {}
        normalizado_a_canonico = {}
        for canonico, variantes in self.SINONIMOS_COLUMNAS.items():
            canon_norm = self._normalizar_texto(canonico)
            normalizado_a_canonico[canon_norm] = canonico
            for var in variantes:
                var_norm = self._normalizar_texto(var)
                normalizado_a_canonico[var_norm] = canonico

        for col in columnas_originales:
            col_norm = self._normalizar_texto(col)
            if col_norm in normalizado_a_canonico:
                mapeo[col] = normalizado_a_canonico[col_norm]
            else:
                mapeo[col] = col
        return mapeo

    def procesar_carpeta_causales(
        self,
        ruta_carpeta: str,
        carpeta_salida: str
    ) -> Dict:
        """
        Procesa todos los archivos .xlsx en la carpeta de causales, los filtra,
        normaliza y consolida en un único archivo.
        Retorna resultado con estadísticas detalladas por archivo y preview del consolidado.
        """
        resultado = {
            'success': False,
            'mensajes': [],
            'ruta_consolidado': '',
            'total_filas': 0,
            'total_archivos': 0,
            'estadisticas_archivos': [],
            'preview_html': ''
        }

        if self.log_service:
            self.log_service.log('4.2', 'Procesar Causales', 'info',
                                 f'Procesando carpeta: {ruta_carpeta}')

        if not os.path.isdir(ruta_carpeta):
            resultado['mensajes'].append('La carpeta Causales no existe.')
            return resultado

        archivos = listar_archivos_por_extension(ruta_carpeta, ".xlsx")
        if not archivos:
            resultado['mensajes'].append('No hay archivos .xlsx en Causales.')
            return resultado

        dataframes = []
        estadisticas = []

        for archivo in archivos:
            ruta_archivo = os.path.join(ruta_carpeta, archivo)
            try:
                df = leer_excel_texto(ruta_archivo, skiprows=2)
            except Exception as e:
                resultado['mensajes'].append(f"Error al leer {archivo}: {e}")
                continue

            # Mapear columnas a canónicas
            mapeo = self._mapear_columnas(df.columns.tolist())
            df.rename(columns=mapeo, inplace=True)

            faltantes = set(self.COLUMNAS_REQUERIDAS) - set(df.columns)
            if faltantes:
                resultado['mensajes'].append(f"{archivo}: faltan columnas {faltantes}. Saltando.")
                continue

            total_original = len(df)

            # Filtro 1: Campaña contiene "Cobranzas"
            mask_campania = df['Campaña'].str.contains('Cobranzas', case=False, na=False)
            df_campania = df[mask_campania]
            total_campania = len(df_campania)

            # Filtro 2: Tipo de evento contiene "Categorizaci" (sobre el resultado de Campaña)
            mask_evento = df_campania['Tipo de evento'].str.contains('Categorizaci', case=False, na=False)
            df_final = df_campania[mask_evento].copy()
            total_valido = len(df_final)

            # Normalizar Usuario
            normalizaciones = 0
            if 'Usuario' in df_final.columns:
                for idx, usuario in df_final['Usuario'].items():
                    nuevo = self.normalizar_usuario(usuario)
                    if nuevo != usuario:
                        normalizaciones += 1
                    df_final.at[idx, 'Usuario'] = nuevo

            dataframes.append(df_final)

            estadisticas.append({
                'archivo': archivo,
                'original': total_original,
                'tras_campania': total_campania,
                'tras_evento': total_valido,
                'normalizaciones': normalizaciones
            })
            resultado['mensajes'].append(
                f"{archivo}: {total_original} → {total_campania} → {total_valido} filas (normalizados: {normalizaciones})."
            )

        if not dataframes:
            resultado['mensajes'].append("Ningún archivo pudo ser procesado.")
            return resultado

        df_consolidado = pd.concat(dataframes, ignore_index=True)
        nombre_consolidado = "Causales_Consolidado.xlsx"
        ruta_consolidado = os.path.join(carpeta_salida, nombre_consolidado)
        escribir_excel(df_consolidado, ruta_consolidado)

        preview_html = generar_preview_html(df_consolidado, filas=10)

        resultado.update({
            'success': True,
            'ruta_consolidado': ruta_consolidado,
            'total_filas': len(df_consolidado),
            'total_archivos': len(dataframes),
            'estadisticas_archivos': estadisticas,
            'preview_html': preview_html
        })

        if self.log_service:
            self.log_service.log('4.2', 'Procesar Causales', 'éxito',
                                 f'Consolidado: {len(df_consolidado)} filas de {len(dataframes)} archivos.')

        return resultado