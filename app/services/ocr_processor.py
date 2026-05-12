import re
from typing import Dict, Optional

import pytesseract
from PIL import Image, ImageEnhance, ImageOps


class OCRProcessor:
    """Servicio para extraer totales de control desde imágenes."""

    def __init__(self, tesseract_path: str):
        """
        Args:
            tesseract_path: Ruta absoluta del ejecutable tesseract.exe
        """
        self.tesseract_path = tesseract_path
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def _preprocesar_imagen(self, imagen: Image.Image) -> Image.Image:
        """
        Preprocesamiento ligero:
        - Escala de grises con ImageOps
        - Aumento de contraste (1.5)
        """
        imagen = ImageOps.grayscale(imagen)
        enhancer = ImageEnhance.Contrast(imagen)
        imagen = enhancer.enhance(1.5)
        return imagen

    def extraer_texto(self, ruta_imagen: str) -> str:
        """
        Aplica OCR a una imagen y devuelve el texto extraído.

        Args:
            ruta_imagen: Ruta completa al archivo de imagen.

        Returns:
            Cadena con el texto reconocido.
        """
        try:
            imagen = Image.open(ruta_imagen)
            imagen = self._preprocesar_imagen(imagen)
            # --psm 4: asume una columna de texto de tamaño variable
            texto = pytesseract.image_to_string(imagen, lang="spa", config="--psm 4")
            return texto.strip()
        except Exception as e:
            raise RuntimeError(f"Error al procesar la imagen {ruta_imagen}: {e}")

    def extraer_totales(self, texto: str) -> Dict[str, Optional[int]]:
        """
        Busca en el texto los totales generales de Orion y Aister.
        Soporta variaciones como 'Total general Orion', 'Totales Generales Orion'
        con o sin dos puntos.

        Returns:
            Diccionario con 'orion', 'aister' y 'texto_completo'.
        """
        totales = {"orion": None, "aister": None, "texto_completo": texto}

        # Patrón flexible para Orion
        patron_orion = r"(?:Total(?:es)?\s+General(?:es)?\s+Orion\s*:?\s*)(\d+)"
        match_orion = re.search(patron_orion, texto, re.IGNORECASE)
        if match_orion:
            totales["orion"] = int(match_orion.group(1))

        # Patrón flexible para Aister
        patron_aister = r"(?:Total(?:es)?\s+General(?:es)?\s+Aister\s*:?\s*)(\d+)"
        match_aister = re.search(patron_aister, texto, re.IGNORECASE)
        if match_aister:
            totales["aister"] = int(match_aister.group(1))

        return totales
