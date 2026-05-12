import os
from flask import Blueprint, render_template
from app.services.file_manager import FileManager
from app.config import DATA_DIR, TESSERACT_PATH

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html", titulo="Orion Procesos")


@main_bp.route("/test-fase2")
def test_fase2():
    """Ruta temporal para probar la creación de carpetas diarias."""
    fm = FileManager(DATA_DIR)
    # Usamos una fecha de ejemplo: 2026-05-12 -> 202605_12
    resultado = fm.crear_estructura_diaria("202605_12")

    if resultado["success"]:
        rutas = resultado["rutas"]
        html = "<h2>Carpetas creadas correctamente ✅</h2><ul>"
        for key, ruta in rutas.items():
            html += f"<li><strong>{key}:</strong> {ruta}</li>"
        html += "</ul>"
        return html
    else:
        return f"<h2>Error ❌</h2><p>{resultado['error']}</p>"


@main_bp.route("/test-red")
def test_red():
    """Ruta temporal para probar la verificación de red (simula fallo si no hay red)."""
    fm = FileManager(DATA_DIR)
    # Usamos fecha de ejemplo 202605_06 -> archivos con 06052026
    resultado = fm.verificar_red_y_carpetas("202605_06")

    if resultado["success"]:
        html = "<h2>Verificación de red y carpetas ✅</h2>"
        html += "<ul>"
        for msg in resultado["mensajes"]:
            html += f"<li>{msg}</li>"
        html += "</ul>"
        html += "<h3>Archivos encontrados</h3>"
        for sub, archivos in resultado["archivos_encontrados"].items():
            html += f"<p><strong>{sub}:</strong> {', '.join(archivos) if archivos else 'Ninguno'}</p>"
        return html
    else:
        return f"<h2>Error ❌</h2><p>{resultado['error']}</p>"


@main_bp.route("/test-distribuir")
def test_distribuir():
    """Ruta temporal para probar la distribución de archivos."""
    fm = FileManager(DATA_DIR)
    # Usamos la misma fecha de ejemplo
    fecha = "202605_06"
    resultado_verif = fm.verificar_red_y_carpetas(fecha)

    if not resultado_verif["success"]:
        return f"<h2>Error previo ❌</h2><p>{resultado_verif['error']}</p>"

    # Si la verificación hubiera tenido éxito, procederíamos
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    resultado_dist = fm.distribuir_archivos(
        resultado_verif["rutas_validadas"],
        carpeta_diaria,
        resultado_verif["archivos_encontrados"],
    )

    if resultado_dist["success"]:
        html = "<h2>Distribución completada ✅</h2><ul>"
        for f in resultado_dist["copiados"]:
            html += f"<li>{f}</li>"
        html += "</ul>"
        return html
    else:
        html = f"<h2>Distribución con errores ⚠️</h2><ul>"
        for e in resultado_dist["errores"]:
            html += f"<li>{e}</li>"
        html += "</ul>"
        return html


@main_bp.route("/test-ocr")
def test_ocr():
    """Ruta temporal para probar Tesseract OCR con una imagen generada."""
    from PIL import Image, ImageDraw
    import pytesseract

    # Configurar la ruta de Tesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    # Crear carpeta de prueba si no existe
    test_dir = os.path.join(DATA_DIR, "test_images")
    os.makedirs(test_dir, exist_ok=True)

    # Generar una imagen simple con texto
    img = Image.new("RGB", (600, 200), color="black")
    d = ImageDraw.Draw(img)
    # Usar una fuente básica (por defecto no se especifica, Pillow usará la interna)
    d.text((20, 80), "Totales Generales Orion: 1500", fill="white")
    ruta_img = os.path.join(test_dir, "test_totales.png")
    img.save(ruta_img)

    # Ejecutar OCR
    try:
        texto_extraido = pytesseract.image_to_string(ruta_img, lang="spa")
    except Exception as e:
        texto_extraido = f"Error OCR: {e}"

    return f"""
    <h2>Prueba OCR ✅</h2>
    <p><strong>Imagen generada:</strong> {ruta_img}</p>
    <p><strong>Texto extraído:</strong> {texto_extraido.strip()}</p>
    <img src="/static/../data/test_images/test_totales.png" width="400" />
    """


@main_bp.route("/test-ocr-real")
def test_ocr_real():
    from PIL import Image, ImageDraw, ImageFont
    import os
    from app.services.ocr_processor import OCRProcessor
    from app.config import TESSERACT_PATH

    ocr = OCRProcessor(TESSERACT_PATH)
    test_dir = os.path.join(DATA_DIR, "test_images")
    os.makedirs(test_dir, exist_ok=True)

    # Intentar cargar Arial, si no, fuente por defecto
    try:
        fuente = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        fuente = ImageFont.load_default()

    # Imagen 1: solo Orion (fondo blanco, texto negro)
    img1 = Image.new("RGB", (700, 120), color="white")
    d1 = ImageDraw.Draw(img1)
    d1.text((30, 40), "Total general Orion: 1500", fill="black", font=fuente)
    ruta1 = os.path.join(test_dir, "img_orion.png")
    img1.save(ruta1)

    # Imagen 2: ambos totales (dos líneas)
    img2 = Image.new("RGB", (700, 160), color="white")
    d2 = ImageDraw.Draw(img2)
    d2.text((30, 20), "Total general Orion: 1500", fill="black", font=fuente)
    d2.text((30, 80), "Total general Aister: 890", fill="black", font=fuente)
    ruta2 = os.path.join(test_dir, "img_ambos.png")
    img2.save(ruta2)

    # Procesar
    texto1 = ocr.extraer_texto(ruta1)
    totales1 = ocr.extraer_totales(texto1)

    texto2 = ocr.extraer_texto(ruta2)
    totales2 = ocr.extraer_totales(texto2)

    def render_resultado(label, totales):
        html = f"<h3>{label}</h3>"
        html += f"<p><b>Texto crudo:</b> {totales['texto_completo']}</p>"
        html += f"<p><b>Orion:</b> {totales['orion']} | <b>Aister:</b> {totales['aister']}</p>"
        return html

    return f"""
    <h2>Prueba OCRProcessor con patrones flexibles ✅</h2>
    {render_resultado('Imagen 1 (solo Orion)', totales1)}
    {render_resultado('Imagen 2 (ambos)', totales2)}
    """


@main_bp.route("/test-discador")
def test_discador():
    """Prueba del DiscadorProcessor con datos simulados."""
    import pandas as pd
    from app.services.discador_processor import DiscadorProcessor
    from app.config import DATA_DIR

    # Crear carpeta de prueba
    test_dir = os.path.join(DATA_DIR, "test_discador")
    os.makedirs(test_dir, exist_ok=True)

    # Crear un DataFrame de ejemplo
    data = {
        "Lote": ["L001", "L002", "L003", "L004", "L005", "L006"],
        "Campaña": [
            "Cobranzas Hogar 121 dias",
            "Cobranzas Hogar 121 dias",
            "Cobranzas Hogar 121 dias",
            "Otra Campaña",
            "Cobranzas Hogar 121 dias",
            "Cobranzas Hogar 121 dias",
        ],
        "EstadoActualContacto": [
            "Contactada",
            "Vencida",
            "Contactada",
            "Vencida",
            "Fallida",
            "Contactada",
        ],
        "TiempoEnCola": ["00:02:30", "-", "00:01:15", "-", "00:05:00", "-"],
        "Agente": ["Agente1", "-", "Agente2", "-", "Agente3", "-"],
        "TiempoHablado": ["00:10:00", "-", "00:05:30", "-", "-", "00:20:00"],
        "DuracionTotal": ["00:12:30", "-", "00:06:45", "-", "00:05:00", "00:25:00"],
    }
    df = pd.DataFrame(data)
    ruta_excel = os.path.join(test_dir, "discador_ejemplo.xlsx")
    df.to_excel(ruta_excel, index=False)

    # Procesar con un total esperado de 5 (para que no coincida y veamos advertencia)
    procesador = DiscadorProcessor()
    resultado = procesador.procesar(
        ruta_archivo=ruta_excel,
        total_orion_esperado=5,  # Valor esperado simulado
        carpeta_salida=test_dir,
    )

    # Mostrar resultado
    html = "<h2>Resultado del DiscadorProcessor</h2>"
    html += f"<p><b>Total esperado (OCR):</b> {resultado['total_esperado']}</p>"
    html += f"<p><b>Total válidos:</b> {resultado['total_validos']}</p>"
    html += f"<p><b>Total no válidos:</b> {resultado['total_no_validos']}</p>"
    html += f"<p><b>Cuadre:</b> {'✅' if resultado['cuadre_ok'] else '❌'}</p>"
    html += f"<p><b>Mensaje:</b> {resultado['mensaje']}</p>"
    html += f"<p><b>Archivo limpio:</b> {resultado['ruta_limpio']}</p>"
    html += f"<p><b>Archivo no válidos:</b> {resultado['ruta_no_validos']}</p>"
    return html


@main_bp.route("/test-causales")
def test_causales():
    """Prueba del CausalesProcessor con datos simulados."""
    import pandas as pd
    from app.config import DATA_DIR
    from app.services.casuales_processor import CausalesProcessor

    test_dir = os.path.join(DATA_DIR, "test_causales")
    os.makedirs(test_dir, exist_ok=True)

    # Crear archivo Excel con 2 filas sucias + encabezados + datos
    ruta_excel = os.path.join(test_dir, "causales_ejemplo.xlsx")

    # Escribimos manualmente para controlar las dos primeras filas
    with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:
        # Primera fila de basura
        pd.DataFrame([["BASURA1", "BASURA2", "BASURA3"]]).to_excel(
            writer, startrow=0, index=False, header=False
        )
        # Segunda fila de basura
        pd.DataFrame([["DESCARTAR", "DESCARTAR", "DESCARTAR"]]).to_excel(
            writer, startrow=1, index=False, header=False
        )
        # Datos reales (con encabezados)
        data = {
            "Campaña": [
                "Cobranzas Hogar 0-30 días",
                "Otra Campaña",
                "Cobranzas Hogar 0-30 días",
                "Cobranzas Hogar 0-30 días",
            ],
            "Tipo de evento": [
                "Categorización",
                "Categorización",
                "Llamada",
                "Categorización",
            ],
            "Usuario": [
                "1453-Miguel Angel",
                "0001-Juan Perez",
                "9999-Maria Lopez",
                "Carlos Ruiz",
            ],
        }
        df_data = pd.DataFrame(data)
        df_data.to_excel(writer, startrow=2, index=False)

    # Procesar
    procesador = CausalesProcessor()
    resultado = procesador.procesar(ruta_archivo=ruta_excel, carpeta_salida=test_dir)

    # Mostrar resultado
    html = "<h2>Resultado del CausalesProcessor</h2>"
    html += f"<p><b>Válidos:</b> {resultado['total_validos']}</p>"
    html += f"<p><b>No válidos:</b> {resultado['total_no_validos']}</p>"
    html += f"<p><b>Mensaje:</b> {resultado['mensaje']}</p>"
    html += f"<p><b>Ruta limpio:</b> {resultado['ruta_limpio']}</p>"
    html += f"<p><b>Ruta no válidos:</b> {resultado['ruta_no_validos']}</p>"
    html += "<h3>Previsualización del archivo limpio</h3>"
    if resultado["success"]:
        df_vista = pd.read_excel(resultado["ruta_limpio"])
        html += df_vista.to_html(index=False, classes="dataframe")
    return html

@main_bp.route('/test-lotes')
def test_lotes():
    """Prueba del LotesProcessor con CSV simulados."""
    import pandas as pd
    from app.services.lotes_processor import LotesProcessor
    from app.config import DATA_DIR

    test_dir = os.path.join(DATA_DIR, 'test_lotes')
    os.makedirs(test_dir, exist_ok=True)

    # Crear CSV de ejemplo 1: con columnas phone_number
    data1 = {
        'Cuenta': ['C001', 'C002'],
        'Cliente': ['Juan', 'Maria'],
        'phone_number_1': ['88880001', ''],
        'phone_number_2': ['', '88880003'],
        'phone_number_3': ['88880002', ''],
        'phone_number_4': ['', ''],
        'phone_number_5': ['', ''],
        'phone_number_6': ['', ''],
        'phone_number_7': ['', ''],
    }
    df1 = pd.DataFrame(data1)
    df1.to_csv(os.path.join(test_dir, 'LOTE_001.csv'), index=False)

    # Crear CSV de ejemplo 2: sin columnas phone_number
    data2 = {
        'Cuenta': ['C003'],
        'Cliente': ['Carlos'],
        'Telefono': ['88880004']
    }
    df2 = pd.DataFrame(data2)
    df2.to_csv(os.path.join(test_dir, 'LOTE_002.csv'), index=False)

    # Crear un Discador limpio simulado (solo columna Lote)
    disc_data = {'Lote': ['LOTE_001', 'LOTE_002']}
    df_disc = pd.DataFrame(disc_data)
    ruta_disc = os.path.join(test_dir, 'discador_limpio.xlsx')
    df_disc.to_excel(ruta_disc, index=False)

    # Procesar
    procesador = LotesProcessor()
    resultado = procesador.procesar_carpeta_lotes(
        ruta_carpeta=test_dir,
        fecha_str='202605_12',
        ruta_discador_limpio=ruta_disc
    )

    # Mostrar resultado
    html = "<h2>Resultado del LotesProcessor</h2>"
    html += f"<p><b>Éxito:</b> {resultado['success']}</p>"
    html += f"<p><b>Total filas consolidadas:</b> {resultado['total_filas']}</p>"
    html += "<h3>Mensajes</h3><ul>"
    for msg in resultado['mensajes']:
        html += f"<li>{msg}</li>"
    html += "</ul>"
    if resultado['validacion_cruzada']:
        html += f"<p><b>Validación cruzada:</b> {'OK' if resultado['validacion_cruzada']['ok'] else 'Fallo'}</p>"
    html += f"<p><b>Ruta consolidado:</b> {resultado['ruta_consolidado']}</p>"
    html += "<h3>Previsualización (primeras 10 filas)</h3>"
    html += resultado['preview_html']
    return html
