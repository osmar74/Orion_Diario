import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import DATA_DIR, TESSERACT_PATH
from app.services.ocr_processor import OCRProcessor


def obtener_fuente():
    ruta_fuente = r"C:\Windows\Fonts\arial.ttf"

    if os.path.exists(ruta_fuente):
        return ImageFont.truetype(ruta_fuente, 48)

    return ImageFont.load_default()


def crear_imagen_prueba(ruta_imagen):
    ruta_imagen.parent.mkdir(parents=True, exist_ok=True)

    imagen = Image.new("RGB", (1200, 420), "white")
    dibujo = ImageDraw.Draw(imagen)
    fuente = obtener_fuente()

    lineas = [
        "Prueba OCR Orion Diario",
        "Totales Generales Orion: 1234",
        "Totales Generales Aister: 5678",
    ]

    y = 60
    for linea in lineas:
        dibujo.text((80, y), linea, fill="black", font=fuente)
        y += 90

    imagen.save(ruta_imagen)


def main():
    print("==============================================")
    print("PRUEBA OCR - ORION DIARIO")
    print("==============================================")

    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"TESSERACT_PATH: {TESSERACT_PATH}")
    print(f"Existe Tesseract: {os.path.exists(TESSERACT_PATH)}")

    if not os.path.exists(TESSERACT_PATH):
        raise FileNotFoundError(
            f"No se encontró tesseract.exe en la ruta configurada: {TESSERACT_PATH}"
        )

    ruta_imagen = Path(DATA_DIR) / "ocr_smoke" / "ocr_test.png"
    crear_imagen_prueba(ruta_imagen)

    print(f"Imagen de prueba creada en: {ruta_imagen}")

    ocr = OCRProcessor(TESSERACT_PATH)
    texto = ocr.extraer_texto(str(ruta_imagen))
    totales = ocr.extraer_totales(texto)

    print("----------------------------------------------")
    print("TEXTO DETECTADO POR OCR:")
    print("----------------------------------------------")
    print(texto)

    print("----------------------------------------------")
    print("TOTALES EXTRAÍDOS:")
    print("----------------------------------------------")
    print(f"Orion: {totales['orion']}")
    print(f"Aister: {totales['aister']}")

    if totales["orion"] == 1234 and totales["aister"] == 5678:
        print("----------------------------------------------")
        print("✅ PRUEBA OCR EXITOSA")
        print("----------------------------------------------")
    else:
        print("----------------------------------------------")
        print("⚠️ OCR ejecutó, pero los totales no coincidieron exactamente.")
        print("Esto puede deberse a idioma, calidad de imagen o lectura parcial.")
        print("----------------------------------------------")


if __name__ == "__main__":
    main()