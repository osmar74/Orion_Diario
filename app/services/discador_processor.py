import os
from typing import Dict, List, Optional

import pandas as pd


class DiscadorProcessor:
    """Procesa el archivo de Discador: valida, filtra, limpia y controla cuadre."""

    # Columnas mínimas que debe tener el archivo de discador
    COLUMNAS_REQUERIDAS = [
        "Lote",
        "Campaña",
        "EstadoActualContacto",
        "TiempoEnCola",
        "Agente",
        "TiempoHablado",
        "DuracionTotal",
    ]

    # Columnas a limpiar (reemplazar '-' por None)
    COLUMNAS_LIMPIAR = ["TiempoEnCola", "Agente", "TiempoHablado", "DuracionTotal"]

    def validar_encabezados(self, df: pd.DataFrame) -> None:
        """Lanza ValueError si faltan columnas requeridas."""
        faltantes = set(self.COLUMNAS_REQUERIDAS) - set(df.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en Discador: {faltantes}")

    def filtrar(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Aplica filtros:
        - Campaña == 'Cobranzas Hogar 121 dias'
        - EstadoActualContacto en ['Contactada', 'Vencida']
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

        Args:
            ruta_archivo: Ruta del Excel de discador.
            total_orion_esperado: Número esperado de registros (del OCR).
            carpeta_salida: Carpeta donde se guardarán los archivos generados.

        Returns:
            Diccionario con éxito, cantidad válidos, no válidos, cuadre, rutas.
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

        try:
            # Leer archivo
            df = pd.read_excel(ruta_archivo, dtype=str)

            # Validar encabezados
            self.validar_encabezados(df)

            # Filtrar
            df_validos, df_no_validos = self.filtrar(df)

            # Limpiar válidos
            df_validos = self.limpiar(df_validos)

            total_validos = len(df_validos)
            total_no_validos = len(df_no_validos)

            # Control de cuadre
            cuadre = total_validos == total_orion_esperado
            if cuadre:
                mensaje = "Cuadre correcto: los totales coinciden."
            else:
                mensaje = (
                    f"Advertencia: El total procesado ({total_validos}) "
                    f"no coincide con el esperado ({total_orion_esperado})."
                )

            # Generar nombres de salida
            base = os.path.splitext(os.path.basename(ruta_archivo))[0]
            ruta_limpio = os.path.join(carpeta_salida, f"{base}_limpio.xlsx")
            ruta_no_validos = os.path.join(carpeta_salida, f"{base}_no_validos.xlsx")

            # Guardar archivos
            os.makedirs(carpeta_salida, exist_ok=True)
            df_validos.to_excel(ruta_limpio, index=False)
            df_no_validos.to_excel(ruta_no_validos, index=False)

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
            resultado["mensaje"] = f"Error en procesamiento Discador: {e}"

        return resultado
