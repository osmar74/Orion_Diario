import os
import re
from typing import Dict, List, Optional

import pandas as pd

from app.services.log_service import LogService


class LotesProcessor:
    """
    Procesa los archivos CSV de lotes:
    - Detecta y aplica pivoteo si hay columnas phone_number_*.
    - Limpia la columna Cuenta.
    - Añade metadatos (Fecha, Nombre_Lote).
    - Realiza validación cruzada contra Discador.
    - Exporta un único Excel consolidado.
    """

    def __init__(self, log_service: Optional[LogService] = None):
        self.log_service = log_service

    def detectar_columnas_telefono(self, df: pd.DataFrame) -> List[str]:
        """Devuelve lista de columnas que coinciden con phone_number_*."""
        patron = re.compile(r"phone_number_\d+", re.IGNORECASE)
        return [col for col in df.columns if patron.match(col)]

    def pivotear_largo(
        self, df: pd.DataFrame, columnas_telefono: List[str]
    ) -> pd.DataFrame:
        """Transforma columnas phone_number_X a formato largo."""
        id_vars = [col for col in df.columns if col not in columnas_telefono]
        df_largo = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=columnas_telefono,
            var_name="Origen_Telefono",
            value_name="Telefono",
        )
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
        """Añade columnas Fecha y Nombre_Lote."""
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
        """Comprueba que los lotes existan en el Discador limpio."""
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
        Procesa todos los CSV en la carpeta de lotes.

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

        if self.log_service:
            self.log_service.log(
                "4.3",
                "Procesar Lotes",
                "info",
                f"Iniciando procesamiento de carpeta: {ruta_carpeta}",
            )

        try:
            archivos_csv = [
                f for f in os.listdir(ruta_carpeta) if f.lower().endswith(".csv")
            ]
            if not archivos_csv:
                msg = "No se encontraron archivos CSV en la carpeta."
                resultado["mensajes"].append(msg)
                if self.log_service:
                    self.log_service.log("4.3", "Procesar Lotes", "advertencia", msg)
                return resultado

            dataframes = []
            mensajes = []

            for archivo in archivos_csv:
                ruta_completa = os.path.join(ruta_carpeta, archivo)
                nombre_lote = os.path.splitext(archivo)[0]

                try:
                    df = pd.read_csv(ruta_completa, dtype=str)
                except Exception as e:
                    mensajes.append(f"Error al leer {archivo}: {e}")
                    continue

                cols_tel = self.detectar_columnas_telefono(df)
                if cols_tel:
                    df = self.pivotear_largo(df, cols_tel)
                    mensajes.append(
                        f"{archivo}: pivoteo aplicado sobre {len(cols_tel)} columnas telefónicas."
                    )

                df = self.limpiar_cuenta(df)
                df = self.agregar_metadatos(df, nombre_lote, fecha_str)

                dataframes.append(df)
                mensajes.append(f"{archivo}: procesado ({len(df)} filas).")

            if not dataframes:
                resultado["mensajes"] = mensajes + [
                    "Ningún archivo pudo ser procesado."
                ]
                if self.log_service:
                    self.log_service.log(
                        "4.3", "Procesar Lotes", "error", "Ningún archivo procesable."
                    )
                return resultado

            df_consolidado = pd.concat(dataframes, ignore_index=True)

            # Exportar consolidado
            fecha_archivo = fecha_str.replace("_", "")[4:]
            nombre_consolidado = f"Lote_Consolidado_{fecha_archivo}.xlsx"
            ruta_consolidado = os.path.join(ruta_carpeta, nombre_consolidado)
            df_consolidado.to_excel(ruta_consolidado, index=False)

            validacion = None
            if ruta_discador_limpio and os.path.isfile(ruta_discador_limpio):
                validacion = self.validar_cruzado(df_consolidado, ruta_discador_limpio)
                mensajes.extend(validacion["mensajes"])

            preview_html = df_consolidado.head(10).to_html(
                index=False, classes="dataframe"
            )

            if self.log_service:
                if validacion and not validacion["ok"]:
                    self.log_service.log(
                        "4.3",
                        "Procesar Lotes",
                        "advertencia",
                        f'Validación cruzada fallida: {validacion["mensajes"]}',
                    )
                else:
                    self.log_service.log(
                        "4.3",
                        "Procesar Lotes",
                        "éxito",
                        f"Total filas: {len(df_consolidado)}",
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
            if self.log_service:
                self.log_service.log("4.3", "Procesar Lotes", "error", str(e))
            resultado["mensajes"].append(f"Error general: {e}")

        return resultado
