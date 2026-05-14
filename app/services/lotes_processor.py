import os
import re
from typing import Dict, List, Optional

import pandas as pd

from app.services.log_service import LogService


class LotesProcessor:
    """
    Procesa los archivos CSV de lotes:
    - Detecta y aplica pivoteo si hay columnas phone_number_*.
    - Limpia la columna Cuenta (vacía) y cuenta cuántas filas tenían datos.
    - Añade metadatos (Fecha, Nombre_Lote).
    - Realiza validación cruzada contra Discador (opcional).
    - Exporta un único Excel consolidado.
    - Retorna estadísticas detalladas por archivo.
    """

    def __init__(self, log_service: Optional[LogService] = None):
        self.log_service = log_service

    def detectar_columnas_telefono(self, df: pd.DataFrame) -> List[str]:
        """
        Devuelve lista de columnas que EMPIEZAN con 'phone_number_'
        (ignorando mayúsculas).
        """
        patron = re.compile(r'^phone_number_\d+', re.IGNORECASE)
        return [col for col in df.columns if patron.match(col)]

    def pivotear_largo(
        self, df: pd.DataFrame, columnas_telefono: List[str]
    ) -> pd.DataFrame:
        """
        Transforma columnas phone_number_X a formato largo.
        Cada fila se replica por cada teléfono no vacío.
        Elimina la columna 'Origen_Telefono' y renombra 'Telefono' a 'phone_number'.
        """
        id_vars = [col for col in df.columns if col not in columnas_telefono]
        df_largo = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=columnas_telefono,
            var_name='Origen_Telefono',
            value_name='Telefono'
        )
        # Eliminar filas sin teléfono
        df_largo = df_largo[df_largo['Telefono'].notna() & (df_largo['Telefono'] != '')]
        # Eliminar columna Origen_Telefono
        df_largo.drop(columns=['Origen_Telefono'], inplace=True)
        # Renombrar Telefono a phone_number
        df_largo.rename(columns={'Telefono': 'phone_number'}, inplace=True)
        return df_largo.reset_index(drop=True)

    def limpiar_cuenta(self, df: pd.DataFrame) -> (pd.DataFrame, int):
        """
        Vacía la columna 'Cuenta' si existe.
        Retorna (DataFrame, número de filas que tenían dato antes de vaciar).
        """
        filas_con_dato = 0
        if 'Cuenta' in df.columns:
            # Contar filas no vacías (no NaN y no cadena vacía)
            mask = df['Cuenta'].notna() & (df['Cuenta'] != '')
            filas_con_dato = int(mask.sum())
            df['Cuenta'] = ''
        return df, filas_con_dato

    def agregar_metadatos(
        self, df: pd.DataFrame, nombre_lote: str, fecha_str: str
    ) -> pd.DataFrame:
        """
        Añade columnas Fecha (dd/mm/aaaa) y Nombre_Lote.
        """
        partes = fecha_str.split('_')
        if len(partes) == 2:
            anio = partes[0][:4]
            mes = partes[0][4:]
            dia = partes[1]
            fecha_formateada = f"{dia}/{mes}/{anio}"
        else:
            fecha_formateada = fecha_str

        df['Fecha'] = fecha_formateada
        df['Nombre_Lote'] = nombre_lote
        return df

    def validar_cruzado(
        self, df_consolidado: pd.DataFrame, ruta_discador: str
    ) -> Dict:
        """Comprueba que los lotes existan en el Discador limpio."""
        try:
            df_disc = pd.read_excel(ruta_discador)
            lotes_discador = set(df_disc['Lote'].dropna().unique())
            lotes_consolidado = set(df_consolidado['Nombre_Lote'].dropna().unique())

            faltantes = lotes_consolidado - lotes_discador
            if faltantes:
                return {
                    'ok': False,
                    'mensajes': [
                        f"Lotes en consolidado pero no en Discador: {faltantes}"
                    ]
                }
            else:
                return {'ok': True, 'mensajes': ["Validación cruzada correcta."]}
        except Exception as e:
            return {'ok': False, 'mensajes': [f"Error en validación cruzada: {e}"]}

    def procesar_carpeta_lotes(
        self,
        ruta_carpeta: str,
        fecha_str: str,
        ruta_discador_limpio: Optional[str] = None
    ) -> Dict:
        """
        Procesa todos los CSV en la carpeta de lotes.
        Retorna diccionario con resultado, estadísticas por archivo, y preview.
        """
        resultado = {
            'success': False,
            'mensajes': [],
            'ruta_consolidado': '',
            'total_filas': 0,
            'validacion_cruzada': None,
            'preview_html': '',
            'estadisticas_archivos': []  # Lista de dict con datos por archivo
        }

        if self.log_service:
            self.log_service.log('4.3', 'Procesar Lotes', 'info',
                                 f'Iniciando procesamiento de carpeta: {ruta_carpeta}')

        try:
            archivos_csv = [
                f for f in os.listdir(ruta_carpeta) if f.lower().endswith('.csv')
            ]
            if not archivos_csv:
                msg = "No se encontraron archivos CSV en la carpeta."
                resultado['mensajes'].append(msg)
                if self.log_service:
                    self.log_service.log('4.3', 'Procesar Lotes', 'advertencia', msg)
                return resultado

            dataframes = []
            mensajes = []
            estadisticas = []

            for archivo in archivos_csv:
                ruta_completa = os.path.join(ruta_carpeta, archivo)
                nombre_lote = os.path.splitext(archivo)[0]

                try:
                    df = pd.read_csv(ruta_completa, sep=';', dtype=str, encoding='latin-1')
                except Exception as e:
                    mensajes.append(f"Error al leer {archivo}: {e}")
                    continue

                filas_originales = len(df)
                pivot_aplicado = False
                filas_despues_pivot = filas_originales
                codigo_cliente_forzado = False
                cuenta_filas_con_dato = 0

                # Verificar si existe columna codigo_cliente y registrar que se forzó a texto
                if 'codigo_cliente' in df.columns:
                    codigo_cliente_forzado = True  # Ya se leyó como str con dtype=str

                # Contar filas con datos en Cuenta antes de limpiar
                if 'Cuenta' in df.columns:
                    mask_cuenta = df['Cuenta'].notna() & (df['Cuenta'] != '')
                    cuenta_filas_con_dato = int(mask_cuenta.sum())

                # Detectar columnas telefónicas
                cols_tel = self.detectar_columnas_telefono(df)
                if cols_tel:
                    df = self.pivotear_largo(df, cols_tel)
                    pivot_aplicado = True
                    filas_despues_pivot = len(df)
                    mensajes.append(
                        f"{archivo}: pivoteo aplicado ({len(cols_tel)} columnas). "
                        f"De {filas_originales} a {filas_despues_pivot} filas."
                    )
                else:
                    mensajes.append(f"{archivo}: sin columnas phone_number. Filas: {filas_originales}.")

                # Limpiar Cuenta y obtener conteo
                df, filas_cuenta = self.limpiar_cuenta(df)
                # Si no habíamos contado antes (caso raro), actualizamos
                if cuenta_filas_con_dato == 0:
                    cuenta_filas_con_dato = filas_cuenta

                # Metadatos
                df = self.agregar_metadatos(df, nombre_lote, fecha_str)

                dataframes.append(df)

                # Guardar estadísticas
                estadisticas.append({
                    'archivo': archivo,
                    'pivot_aplicado': pivot_aplicado,
                    'filas_originales': filas_originales,
                    'filas_despues_pivot': filas_despues_pivot,
                    'codigo_cliente_forzado': codigo_cliente_forzado,
                    'cuenta_filas_con_dato': cuenta_filas_con_dato
                })

            if not dataframes:
                resultado['mensajes'] = mensajes + ["Ningún archivo pudo ser procesado."]
                if self.log_service:
                    self.log_service.log('4.3', 'Procesar Lotes', 'error', 'Ningún archivo procesable.')
                return resultado

            # Consolidar
            df_consolidado = pd.concat(dataframes, ignore_index=True)

            # Exportar consolidado
            fecha_archivo = fecha_str.replace('_', '')[4:]   # DDMMYYYY
            nombre_consolidado = f"Lote_Consolidado_{fecha_archivo}.xlsx"
            ruta_consolidado = os.path.join(ruta_carpeta, nombre_consolidado)
            df_consolidado.to_excel(ruta_consolidado, index=False)

            # Validación cruzada opcional
            validacion = None
            if ruta_discador_limpio and os.path.isfile(ruta_discador_limpio):
                validacion = self.validar_cruzado(df_consolidado, ruta_discador_limpio)
                if validacion:
                    mensajes.extend(validacion['mensajes'])

            # Vista previa (primeras 10 filas)
            preview_html = df_consolidado.head(10).to_html(
                index=False, classes='dataframe'
            )

            if self.log_service:
                if validacion and not validacion['ok']:
                    self.log_service.log('4.3', 'Procesar Lotes', 'advertencia',
                                         f'Validación cruzada fallida: {validacion["mensajes"]}')
                else:
                    self.log_service.log('4.3', 'Procesar Lotes', 'éxito',
                                         f'Total filas consolidadas: {len(df_consolidado)}')

            resultado.update({
                'success': True,
                'mensajes': mensajes,
                'ruta_consolidado': ruta_consolidado,
                'total_filas': len(df_consolidado),
                'validacion_cruzada': validacion,
                'preview_html': preview_html,
                'estadisticas_archivos': estadisticas
            })

        except Exception as e:
            if self.log_service:
                self.log_service.log('4.3', 'Procesar Lotes', 'error', str(e))
            resultado['mensajes'].append(f"Error general: {e}")

        return resultado