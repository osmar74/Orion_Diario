import os
from typing import Dict, List, Optional

import pandas as pd

from app.services.log_service import LogService


class DiscadorProcessor:
    """Procesa el archivo de Discador: valida, filtra, limpia y controla cuadre."""

    COLUMNAS_REQUERIDAS = [
        "Lote",
        "Campaña",
        "EstadoActualContacto",
        "TiempoEnCola",
        "Agente",
        "TiempoHablado",
        "DuracionTotal",
    ]

    COLUMNAS_LIMPIAR = ["TiempoEnCola", "Agente", "TiempoHablado", "DuracionTotal"]

    def __init__(self, log_service: Optional[LogService] = None):
        self.log_service = log_service

    def validar_encabezados(self, df: pd.DataFrame) -> None:
        """Lanza ValueError si faltan columnas requeridas."""
        faltantes = set(self.COLUMNAS_REQUERIDAS) - set(df.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en Discador: {faltantes}")

    def filtrar(self, df: pd.DataFrame) -> tuple:
        """
        Filtra según Campaña y EstadoActualContacto.
        Retorna (df_validos, df_no_validos).
        """
        mascara_campania = df["Campaña"] == "Cobranzas Hogar 121 dias"
        mascara_estado = df["EstadoActualContacto"].isin(["Contactada", "Vencida"])
        mascura_total = mascara_campania & mascara_estado
        df_validos = df[mascura_total].copy()
        df_no_validos = df[~mascura_total].copy()
        return df_validos, df_no_validos

    def limpiar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reemplaza '-' por None en columnas de limpieza."""
        for col in self.COLUMNAS_LIMPIAR:
            if col in df.columns:
                df[col] = df[col].replace("-", None)
        return df

    def procesar(
        self, ruta_archivo: str, total_orion_esperado: int, carpeta_salida: str
    ) -> Dict:
        """
        Ejecuta el flujo completo de Discador.

        Returns:
            Diccionario con éxito, cantidad válidos, no válidos, cuadre, mensaje, rutas.
        """
        resultado = {
            "success": False,
            "total_esperado": total_orion_esperado,
            "total_validos": 0,
            "total_no_validos": 0,
            "cuadre_ok": False,
            "mensaje": "",
            "ruta_limpio": "",
            "ruta_no_validos": "",
        }

        if self.log_service:
            self.log_service.log(
                "4.1",
                "Procesar Discador",
                "info",
                f"Iniciando procesamiento de {ruta_archivo}",
            )

        try:
            df = pd.read_excel(ruta_archivo, dtype=str)
            self.validar_encabezados(df)

            df_validos, df_no_validos = self.filtrar(df)
            df_validos = self.limpiar(df_validos)

            total_validos = len(df_validos)
            total_no_validos = len(df_no_validos)

            cuadre = total_validos == total_orion_esperado
            if cuadre:
                mensaje = "Cuadre correcto: los totales coinciden."
            else:
                mensaje = (
                    f"Advertencia: El total procesado ({total_validos}) "
                    f"no coincide con el esperado ({total_orion_esperado})."
                )

            base = os.path.splitext(os.path.basename(ruta_archivo))[0]
            ruta_limpio = os.path.join(carpeta_salida, f"{base}_limpio.xlsx")
            ruta_no_validos = os.path.join(carpeta_salida, f"{base}_no_validos.xlsx")

            os.makedirs(carpeta_salida, exist_ok=True)
            df_validos.to_excel(ruta_limpio, index=False)
            df_no_validos.to_excel(ruta_no_validos, index=False)

            if self.log_service:
                if cuadre:
                    self.log_service.log(
                        "4.1",
                        "Procesar Discador",
                        "éxito",
                        f"Válidos: {total_validos}, No válidos: {total_no_validos}. Cuadre OK.",
                    )
                else:
                    self.log_service.log(
                        "4.1", "Procesar Discador", "advertencia", mensaje
                    )

            resultado.update(
                {
                    "success": True,
                    "total_validos": total_validos,
                    "total_no_validos": total_no_validos,
                    "cuadre_ok": cuadre,
                    "mensaje": mensaje,
                    "ruta_limpio": ruta_limpio,
                    "ruta_no_validos": ruta_no_validos,
                }
            )

        except Exception as e:
            if self.log_service:
                self.log_service.log("4.1", "Procesar Discador", "error", str(e))
            resultado["mensaje"] = f"Error en procesamiento Discador: {e}"

        return resultado
