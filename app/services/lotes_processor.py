import os
import re
from typing import Dict, List, Optional

import pandas as pd


class LotesProcessor:
    """
    Procesa los archivos CSV de lotes:
    - Detecta y aplica pivoteo si hay columnas phone_number_*.
    - Limpia la columna Cuenta.
    - Añade metadatos (Fecha, Nombre_Lote).
    - Realiza validación cruzada contra Discador.
    - Exporta un único Excel consolidado.
    """

    def detectar_columnas_telefono(self, df: pd.DataFrame) -> List[str]:
        """Devuelve lista de columnas que coinciden con phone_number_*."""
        patron = re.compile(r"phone_number_\d+", re.IGNORECASE)
        return [col for col in df.columns if patron.match(col)]

    def pivotear_largo(
        self, df: pd.DataFrame, columnas_telefono: List[str]
    ) -> pd.DataFrame:
        """
        Transforma columnas phone_number_X a formato largo.
        Cada fila se replica por cada teléfono no vacío.
        """
        # Columnas que no son teléfono
        id_vars = [col for col in df.columns if col not in columnas_telefono]

        # Melt
        df_largo = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=columnas_telefono,
            var_name="Origen_Telefono",
            value_name="Telefono",
        )

        # Eliminar filas sin teléfono
        df_largo = df_largo[df_largo["Telefono"].notna() & (df_largo["Telefono"] != "")]

        return df_largo.reset_index(drop=True)

    def limpiar_cuenta(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vacía la columna Cuenta si existe."""
        if "Cuenta" in df.columns:
            df["Cuenta"] = ""
        return df

    def agregar_metadatos(
        self, df: pd.DataFrame, nombre_lote: str, fecha_str: str
    ) -> pd.DataFrame:
        """
        Añade columnas:
        - Fecha: en formato dd/mm/aaaa (fecha_str es 'YYYYMM_DD')
        - Nombre_Lote: nombre del archivo sin extensión
        """
        # Convertir fecha: '202605_12' -> '12/05/2026'
        partes = fecha_str.split("_")
        if len(partes) == 2:
            anio = partes[0][:4]
            mes = partes[0][4:]
            dia = partes[1]
            fecha_formateada = f"{dia}/{mes}/{anio}"
        else:
            fecha_formateada = fecha_str

        df["Fecha"] = fecha_formateada
        df["Nombre_Lote"] = nombre_lote
        return df

    def validar_cruzado(self, df_consolidado: pd.DataFrame, ruta_discador: str) -> Dict:
        """
        Comprueba que todos los Nombre_Lote en el consolidado
        existan en la columna 'Lote' del archivo de Discador limpio.

        Returns:
            Dict con 'ok' (bool) y 'mensajes' (list).
        """
        try:
            df_disc = pd.read_excel(ruta_discador)
            lotes_discador = set(df_disc["Lote"].dropna().unique())
            lotes_consolidado = set(df_consolidado["Nombre_Lote"].dropna().unique())

            faltantes = lotes_consolidado - lotes_discador
            if faltantes:
                return {
                    "ok": False,
                    "mensajes": [
                        f"Lotes en consolidado pero no en Discador: {faltantes}"
                    ],
                }
            else:
                return {"ok": True, "mensajes": ["Validación cruzada correcta."]}
        except Exception as e:
            return {"ok": False, "mensajes": [f"Error en validación cruzada: {e}"]}

    def procesar_carpeta_lotes(
        self,
        ruta_carpeta: str,
        fecha_str: str,
        ruta_discador_limpio: Optional[str] = None,
    ) -> Dict:
        """
        Procesa todos los CSV en una carpeta de lotes.

        Args:
            ruta_carpeta: Carpeta que contiene los .csv de lotes.
            fecha_str: Fecha en formato 'YYYYMM_DD'.
            ruta_discador_limpio: Ruta al archivo limpio de Discador para
                                  validación cruzada (opcional).

        Returns:
            Diccionario con resultado del procesamiento.
        """
        resultado = {
            "success": False,
            "mensajes": [],
            "ruta_consolidado": "",
            "total_filas": 0,
            "validacion_cruzada": None,
            "preview_html": "",
        }

        try:
            archivos_csv = [
                f for f in os.listdir(ruta_carpeta) if f.lower().endswith(".csv")
            ]
            if not archivos_csv:
                resultado["mensajes"].append(
                    "No se encontraron archivos CSV en la carpeta."
                )
                return resultado

            dataframes = []
            mensajes = []

            for archivo in archivos_csv:
                ruta_completa = os.path.join(ruta_carpeta, archivo)
                nombre_lote = os.path.splitext(archivo)[0]  # sin extensión

                try:
                    df = pd.read_csv(ruta_completa, dtype=str)
                except Exception as e:
                    mensajes.append(f"Error al leer {archivo}: {e}")
                    continue

                # 1. Detección de pivoteo
                cols_tel = self.detectar_columnas_telefono(df)
                if cols_tel:
                    df = self.pivotear_largo(df, cols_tel)
                    mensajes.append(
                        f"{archivo}: pivoteo aplicado sobre {len(cols_tel)} columnas telefónicas."
                    )

                # 2. Limpiar cuenta
                df = self.limpiar_cuenta(df)

                # 3. Metadatos
                df = self.agregar_metadatos(df, nombre_lote, fecha_str)

                dataframes.append(df)
                mensajes.append(f"{archivo}: procesado ({len(df)} filas).")

            if not dataframes:
                resultado["mensajes"] = mensajes + [
                    "Ningún archivo pudo ser procesado."
                ]
                return resultado

            # Consolidar todos los DataFrames
            df_consolidado = pd.concat(dataframes, ignore_index=True)

            # Exportar consolidado
            fecha_archivo = fecha_str.replace("_", "")[4:]  # DDMMYYYY
            nombre_consolidado = f"Lote_Consolidado_{fecha_archivo}.xlsx"
            ruta_consolidado = os.path.join(ruta_carpeta, nombre_consolidado)
            df_consolidado.to_excel(ruta_consolidado, index=False)

            # Validación cruzada si se proporciona Discador limpio
            validacion = None
            if ruta_discador_limpio and os.path.isfile(ruta_discador_limpio):
                validacion = self.validar_cruzado(df_consolidado, ruta_discador_limpio)
                mensajes.extend(validacion["mensajes"])

            # Generar preview HTML de los primeros 10 registros
            preview_html = df_consolidado.head(10).to_html(
                index=False, classes="dataframe"
            )

            resultado.update(
                {
                    "success": True,
                    "mensajes": mensajes,
                    "ruta_consolidado": ruta_consolidado,
                    "total_filas": len(df_consolidado),
                    "validacion_cruzada": validacion,
                    "preview_html": preview_html,
                }
            )

        except Exception as e:
            resultado["mensajes"].append(f"Error general: {e}")

        return resultado
