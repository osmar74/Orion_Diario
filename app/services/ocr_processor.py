import re
from typing import Dict, Optional, List

import pytesseract
from PIL import Image, ImageEnhance, ImageOps

from app.services.log_service import LogService


class OCRProcessor:
    """Servicio para extraer totales de control desde imágenes."""

    def __init__(self, tesseract_path: str, log_service: Optional[LogService] = None):
        """
        Args:
            tesseract_path: Ruta absoluta del ejecutable tesseract.exe
            log_service: Instancia opcional de LogService.
        """
        self.tesseract_path = tesseract_path
        self.log_service = log_service
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def _preprocesar_imagen(self, imagen: Image.Image) -> Image.Image:
        """Preprocesamiento ligero: escala de grises y contraste."""
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
        if self.log_service:
            self.log_service.log(
                "3.2", "Extraer texto OCR", "info", f"Procesando imagen: {ruta_imagen}"
            )

        try:
            imagen = Image.open(ruta_imagen)
            imagen = self._preprocesar_imagen(imagen)
            texto = pytesseract.image_to_string(imagen, lang="spa", config="--psm 6")
            texto_limpio = texto.strip()
            if self.log_service:
                self.log_service.log(
                    "3.2",
                    "Extraer texto OCR",
                    "éxito",
                    f"Texto extraído: {texto_limpio[:100]}...",
                )
            return texto_limpio
        except Exception as e:
            if self.log_service:
                self.log_service.log("3.2", "Extraer texto OCR", "error", str(e))
            raise RuntimeError(f"Error al procesar la imagen {ruta_imagen}: {e}")

    def extraer_totales(self, texto: str) -> Dict[str, Optional[int]]:
        """
        Busca en el texto los totales generales de Orion y Aister.

        Returns:
            Diccionario con 'orion', 'aister' y 'texto_completo'.
        """
        totales = {"orion": None, "aister": None, "texto_completo": texto}

        if self.log_service:
            self.log_service.log(
                "3.2", "Extraer totales", "info", "Analizando texto para totales."
            )

        patron_orion = r"(?:Total(?:es)?\s+General(?:es)?\s+Orion\s*:?\s*)(\d+)"
        match_orion = re.search(patron_orion, texto, re.IGNORECASE)
        if match_orion:
            totales["orion"] = int(match_orion.group(1))

        patron_aister = r"(?:Total(?:es)?\s+General(?:es)?\s+Aister\s*:?\s*)(\d+)"
        match_aister = re.search(patron_aister, texto, re.IGNORECASE)
        if match_aister:
            totales["aister"] = int(match_aister.group(1))

        if totales["orion"] is None and totales["aister"] is None:
            if self.log_service:
                self.log_service.log(
                    "3.2",
                    "Extraer totales",
                    "advertencia",
                    "No se encontraron totales en el texto.",
                )
        else:
            if self.log_service:
                self.log_service.log(
                    "3.2",
                    "Extraer totales",
                    "éxito",
                    f'Orion: {totales["orion"]}, Aister: {totales["aister"]}',
                )

        return totales

    def extraer_totales_generico(self, texto: str) -> List[int]:
        """
        Busca 'Total general' (sin distinción de mayúsculas) y devuelve
        todos los números enteros que aparecen después de esa frase.
        Si no se encuentra, devuelve lista vacía.
        """
        patron = r"Total\s+general\s+(.*?)(?:\n|$)"
        match = re.search(patron, texto, re.IGNORECASE)
        if not match:
            return []
        resto = match.group(1)
        # Extraer todos los números (pueden estar separados por espacios o tabs)
        numeros = re.findall(r"\b\d+\b", resto)
        return [int(n) for n in numeros]
    
    def extraer_numero_cercano(self, texto: str, palabra_clave: str) -> Optional[int]:
        """
        Busca un número de al menos 3 dígitos que aparezca después de la palabra clave,
        en cualquier parte del texto (útil cuando no hay 'Total general').
        """
        patron = re.compile(rf'{re.escape(palabra_clave)}.*?(\d{{3,}})', re.IGNORECASE)
        match = patron.search(texto)
        if match:
            return int(match.group(1))
        return None
