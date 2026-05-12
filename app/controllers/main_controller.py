import os
import pandas as pd
from flask import Blueprint, render_template, request
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
    from app.services.causales_processor import CausalesProcessor

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


@main_bp.route("/test-lotes")
def test_lotes():
    """Prueba del LotesProcessor con CSV simulados."""
    import pandas as pd
    from app.services.lotes_processor import LotesProcessor
    from app.config import DATA_DIR

    test_dir = os.path.join(DATA_DIR, "test_lotes")
    os.makedirs(test_dir, exist_ok=True)

    # Crear CSV de ejemplo 1: con columnas phone_number
    data1 = {
        "Cuenta": ["C001", "C002"],
        "Cliente": ["Juan", "Maria"],
        "phone_number_1": ["88880001", ""],
        "phone_number_2": ["", "88880003"],
        "phone_number_3": ["88880002", ""],
        "phone_number_4": ["", ""],
        "phone_number_5": ["", ""],
        "phone_number_6": ["", ""],
        "phone_number_7": ["", ""],
    }
    df1 = pd.DataFrame(data1)
    df1.to_csv(os.path.join(test_dir, "LOTE_001.csv"), index=False)

    # Crear CSV de ejemplo 2: sin columnas phone_number
    data2 = {"Cuenta": ["C003"], "Cliente": ["Carlos"], "Telefono": ["88880004"]}
    df2 = pd.DataFrame(data2)
    df2.to_csv(os.path.join(test_dir, "LOTE_002.csv"), index=False)

    # Crear un Discador limpio simulado (solo columna Lote)
    disc_data = {"Lote": ["LOTE_001", "LOTE_002"]}
    df_disc = pd.DataFrame(disc_data)
    ruta_disc = os.path.join(test_dir, "discador_limpio.xlsx")
    df_disc.to_excel(ruta_disc, index=False)

    # Procesar
    procesador = LotesProcessor()
    resultado = procesador.procesar_carpeta_lotes(
        ruta_carpeta=test_dir, fecha_str="202605_12", ruta_discador_limpio=ruta_disc
    )

    # Mostrar resultado
    html = "<h2>Resultado del LotesProcessor</h2>"
    html += f"<p><b>Éxito:</b> {resultado['success']}</p>"
    html += f"<p><b>Total filas consolidadas:</b> {resultado['total_filas']}</p>"
    html += "<h3>Mensajes</h3><ul>"
    for msg in resultado["mensajes"]:
        html += f"<li>{msg}</li>"
    html += "</ul>"
    if resultado["validacion_cruzada"]:
        html += f"<p><b>Validación cruzada:</b> {'OK' if resultado['validacion_cruzada']['ok'] else 'Fallo'}</p>"
    html += f"<p><b>Ruta consolidado:</b> {resultado['ruta_consolidado']}</p>"
    html += "<h3>Previsualización (primeras 10 filas)</h3>"
    html += resultado["preview_html"]
    return html


@main_bp.route("/test-logging")
def test_logging():
    """Prueba del LogService: inserta logs de ejemplo y los muestra."""
    from app.services.log_service import LogService
    from app.config import LOG_DB_PATH

    servicio_log = LogService(LOG_DB_PATH)

    # Insertar varios registros de prueba
    servicio_log.log(
        "2.1",
        "Crear estructura diaria",
        "éxito",
        "Carpetas creadas correctamente para fecha 202605_12",
    )
    servicio_log.log(
        "2.2",
        "Verificar red y carpetas",
        "error",
        "No se puede acceder a la unidad de red",
    )
    servicio_log.log("3.2", "Extraer totales OCR", "éxito", "Orion: 1500, Aister: 890")
    servicio_log.log(
        "4.1",
        "Procesar Discador",
        "advertencia",
        "Cuadre no coincidente: esperado 5, obtenido 4",
    )
    servicio_log.log(
        "4.2", "Procesar Causales", "éxito", "2 registros válidos, 2 no válidos"
    )
    servicio_log.log("4.3", "Procesar Lotes", "info", "Pivoteo aplicado a LOTE_001")

    # Obtener todos los logs para mostrar
    logs = servicio_log.obtener_logs(limite=50)

    # Construir tabla HTML
    html = "<h2>Prueba de Logging ✅</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Timestamp</th><th>Fase</th><th>Acción</th><th>Resultado</th><th>Detalle</th></tr>"
    for log in logs:
        html += (
            f"<tr><td>{log['id']}</td><td>{log['timestamp']}</td><td>{log['fase']}</td>"
        )
        html += f"<td>{log['accion']}</td><td>{log['resultado']}</td><td>{log['detalle']}</td></tr>"
    html += "</table>"
    return html


@main_bp.route("/test-integracion-logging")
def test_integracion_logging():
    from app.services.log_service import LogService
    from app.services.file_manager import FileManager
    from app.services.ocr_processor import OCRProcessor
    from app.services.discador_processor import DiscadorProcessor
    from app.services.causales_processor import CausalesProcessor
    from app.services.lotes_processor import LotesProcessor
    from app.config import DATA_DIR, LOG_DB_PATH, TESSERACT_PATH
    import pandas as pd
    import os

    log_srv = LogService(LOG_DB_PATH)

    # FileManager
    fm = FileManager(DATA_DIR, log_service=log_srv)
    fm.crear_estructura_diaria("202605_12")
    fm.verificar_red_y_carpetas("202605_06")  # fallará, generará error
    fm.distribuir_archivos({}, "fake_dir", {})  # fallará por vacío

    # OCR
    ocr = OCRProcessor(TESSERACT_PATH, log_service=log_srv)
    test_dir = os.path.join(DATA_DIR, "test_images")
    os.makedirs(test_dir, exist_ok=True)
    # Crear una mini imagen para probar
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (200, 50), color="white")
    d = ImageDraw.Draw(img)
    d.text((10, 15), "Total general Orion: 100", fill="black")
    ruta_img = os.path.join(test_dir, "temp_ocr.png")
    img.save(ruta_img)
    texto = ocr.extraer_texto(ruta_img)
    ocr.extraer_totales(texto)

    # Discador
    disc = DiscadorProcessor(log_service=log_srv)
    disc_dir = os.path.join(DATA_DIR, "test_discador")
    os.makedirs(disc_dir, exist_ok=True)
    df = pd.DataFrame(
        {
            "Lote": ["L1"],
            "Campaña": ["Cobranzas Hogar 121 dias"],
            "EstadoActualContacto": ["Contactada"],
            "TiempoEnCola": ["-"],
            "Agente": ["-"],
            "TiempoHablado": ["-"],
            "DuracionTotal": ["-"],
        }
    )
    ruta_disc = os.path.join(disc_dir, "disc_test.xlsx")
    df.to_excel(ruta_disc, index=False)
    disc.procesar(ruta_disc, 1, disc_dir)

    # Causales
    caus = CausalesProcessor(log_service=log_srv)
    caus_dir = os.path.join(DATA_DIR, "test_causales")
    os.makedirs(caus_dir, exist_ok=True)
    # creamos archivo simple
    df_caus = pd.DataFrame(
        {
            "Campaña": ["Cobranzas Hogar 0-30 días"],
            "Tipo de evento": ["Categorización"],
            "Usuario": ["1453-Juan"],
        }
    )
    ruta_caus = os.path.join(caus_dir, "caus_test.xlsx")
    df_caus.to_excel(ruta_caus, index=False)
    caus.procesar(ruta_caus, caus_dir)

    # Lotes
    lotes = LotesProcessor(log_service=log_srv)
    lotes_dir = os.path.join(DATA_DIR, "test_lotes")
    os.makedirs(lotes_dir, exist_ok=True)
    df_lote = pd.DataFrame(
        {"Cuenta": ["C1"], "Cliente": ["Test"], "phone_number_1": ["9999"]}
    )
    ruta_lote = os.path.join(lotes_dir, "lote_test.csv")
    df_lote.to_csv(ruta_lote, index=False)
    lotes.procesar_carpeta_lotes(lotes_dir, "202605_12")

    # Obtener logs finales
    logs = log_srv.obtener_logs(limite=50)

    html = "<h2>Integración de Logging - Resultados</h2>"
    html += f"<p><b>Total logs generados:</b> {len(logs)}</p>"
    html += "<table border='1' cellpadding='3'>"
    html += "<tr><th>ID</th><th>Timestamp</th><th>Fase</th><th>Acción</th><th>Resultado</th><th>Detalle</th></tr>"
    for log in logs:
        html += f"<tr><td>{log['id']}</td><td>{log['timestamp']}</td><td>{log['fase']}</td><td>{log['accion']}</td><td>{log['resultado']}</td><td>{log['detalle']}</td></tr>"
    html += "</table>"
    return html


# ---------- Rutas de acción real ----------
def _obtener_log_service():
    from app.services.log_service import LogService
    from app.config import LOG_DB_PATH

    return LogService(LOG_DB_PATH)


@main_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    res = fm.crear_estructura_diaria(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Carpetas creadas para {fecha}</div>"
        html += "<ul>"
        for k, v in res["rutas"].items():
            html += f"<li><b>{k}:</b> {v}</li>"
        html += "</ul>"
    else:
        html = f"<div class='log-line error'>❌ {res['error']}</div>"
    return html


@main_bp.route("/accion/verificar-red")
def accion_verificar_red():
    fecha = request.args.get("fecha", "202605_06")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    res = fm.verificar_red_y_carpetas(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Red verificada</div>"
        html += "<ul>" + "".join(f"<li>{m}</li>" for m in res["mensajes"]) + "</ul>"
        html += "<p><b>Archivos encontrados:</b></p><ul>"
        for sub, archivos in res["archivos_encontrados"].items():
            html += f"<li>{sub}: {', '.join(archivos) if archivos else 'Ninguno'}</li>"
        html += "</ul>"
    else:
        html = f"<div class='log-line error'>❌ {res['error']}</div>"
    return html


@main_bp.route("/accion/ocr")
def accion_ocr():
    fecha = request.args.get("fecha", "202605_12")
    from app.services.ocr_processor import OCRProcessor

    ocr = OCRProcessor(TESSERACT_PATH, log_service=_obtener_log_service())
    # Simulamos: buscar imágenes en data/orion_fecha/Reporte_Imagen
    carpeta_img = os.path.join(DATA_DIR, f"orion_{fecha}", "Reporte_Imagen")
    if not os.path.isdir(carpeta_img):
        return "<div class='log-line error'>❌ No existe la carpeta Reporte_Imagen. Cree las carpetas primero.</div>"
    imagenes = [
        f
        for f in os.listdir(carpeta_img)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    if not imagenes:
        return "<div class='log-line error'>❌ No hay imágenes en Reporte_Imagen.</div>"
    totales_finales = {"orion": None, "aister": None}
    html = ""
    for img in imagenes:
        ruta_img = os.path.join(carpeta_img, img)
        texto = ocr.extraer_texto(ruta_img)
        totales = ocr.extraer_totales(texto)
        html += f"<p>{img}: {totales['texto_completo'][:100]}</p>"
        if totales["orion"]:
            totales_finales["orion"] = totales["orion"]
        if totales["aister"]:
            totales_finales["aister"] = totales["aister"]
    html += f"<div class='log-line success'>✅ OCR completado. Orion: {totales_finales['orion']} | Aister: {totales_finales['aister']}</div>"
    # Guardar totales en session o pasarlos al monitor (por ahora los mostramos)
    return html


@main_bp.route("/accion/distribuir")
def accion_distribuir():
    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    # Necesitamos haber verificado red antes. Por ahora simulamos error controlado.
    res_verif = fm.verificar_red_y_carpetas(fecha)
    if not res_verif["success"]:
        return f"<div class='log-line error'>❌ No se puede distribuir: {res_verif['error']}</div>"
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    res_dist = fm.distribuir_archivos(
        res_verif["rutas_validadas"], carpeta_diaria, res_verif["archivos_encontrados"]
    )
    if res_dist["success"]:
        html = "<div class='log-line success'>✅ Archivos distribuidos correctamente.</div><ul>"
        for f in res_dist["copiados"]:
            html += f"<li>{f}</li>"
        html += "</ul>"
    else:
        html = f"<div class='log-line warning'>⚠️ Distribución parcial. Errores: {res_dist['errores']}</div>"
    return html


@main_bp.route("/accion/procesar-discador")
def accion_procesar_discador():
    fecha = request.args.get("fecha", "202605_12")
    total_esperado = request.args.get("total", 0, type=int)
    from app.services.discador_processor import DiscadorProcessor

    disc = DiscadorProcessor(log_service=_obtener_log_service())
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    # Buscar archivo de discador en raíz de carpeta diaria
    archivos = [
        f
        for f in os.listdir(carpeta_diaria)
        if f.lower().endswith(".xlsx") and "discador" in f.lower()
    ]
    if not archivos:
        return "<div class='log-line error'>❌ No se encontró archivo Discador en la carpeta diaria.</div>"
    ruta_disc = os.path.join(carpeta_diaria, archivos[0])
    res = disc.procesar(ruta_disc, total_esperado, carpeta_diaria)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Discador procesado. Válidos: {res['total_validos']}, No válidos: {res['total_no_validos']}</div>"
        html += f"<p>{res['mensaje']}</p>"
        # preview tabla
        df = pd.read_excel(res["ruta_limpio"])
        html += df.head(10).to_html(index=False, classes="dataframe")
    else:
        html = f"<div class='log-line error'>❌ {res['mensaje']}</div>"
    return html


@main_bp.route("/accion/procesar-causales")
def accion_procesar_causales():
    fecha = request.args.get("fecha", "202605_12")
    from app.services.causales_processor import CausalesProcessor

    caus = CausalesProcessor(log_service=_obtener_log_service())
    carpeta_causales = os.path.join(DATA_DIR, f"orion_{fecha}", "Causales")
    if not os.path.isdir(carpeta_causales):
        return "<div class='log-line error'>❌ No existe la carpeta Causales.</div>"
    archivos = [f for f in os.listdir(carpeta_causales) if f.lower().endswith(".xlsx")]
    if not archivos:
        return "<div class='log-line error'>❌ No hay archivos en Causales.</div>"
    ruta_archivo = os.path.join(carpeta_causales, archivos[0])
    res = caus.procesar(ruta_archivo, carpeta_causales)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Causales procesados. Válidos: {res['total_validos']}, No válidos: {res['total_no_validos']}</div>"
        df = pd.read_excel(res["ruta_limpio"])
        html += df.head(10).to_html(index=False, classes="dataframe")
    else:
        html = f"<div class='log-line error'>❌ {res['mensaje']}</div>"
    return html


@main_bp.route("/accion/procesar-lotes")
def accion_procesar_lotes():
    fecha = request.args.get("fecha", "202605_12")
    from app.services.lotes_processor import LotesProcessor

    lotes = LotesProcessor(log_service=_obtener_log_service())
    carpeta_lotes = os.path.join(DATA_DIR, f"orion_{fecha}", "Lotes")
    if not os.path.isdir(carpeta_lotes):
        return "<div class='log-line error'>❌ No existe la carpeta Lotes.</div>"
    # Buscar archivo del discador limpio para validación cruzada
    ruta_disc = os.path.join(
        DATA_DIR, f"orion_{fecha}", "discador_ejemplo_limpio.xlsx"
    )  # Ajustar nombre real
    res = lotes.procesar_carpeta_lotes(
        carpeta_lotes, fecha, ruta_disc if os.path.isfile(ruta_disc) else None
    )
    if res["success"]:
        html = f"<div class='log-line success'>✅ Lotes procesados. Total filas: {res['total_filas']}</div>"
        html += res["preview_html"]
        if res["validacion_cruzada"]:
            html += f"<p>Validación cruzada: {'OK' if res['validacion_cruzada']['ok'] else 'Fallo'}</p>"
    else:
        html = f"<div class='log-line error'>❌ {res['mensajes']}</div>"
    return html


@main_bp.route("/logs")
def logs():
    """Página de visualización de logs con filtros."""
    from app.services.log_service import LogService
    from app.config import LOG_DB_PATH

    log_srv = LogService(LOG_DB_PATH)
    fase = request.args.get("fase", None)
    resultado = request.args.get("resultado", None)

    logs = log_srv.obtener_logs(fase=fase, resultado=resultado, limite=500)

    # Posibles fases y resultados para los selects
    fases_posibles = ["2.1", "2.2", "2.3", "3.2", "4.1", "4.2", "4.3"]
    resultados_posibles = ["éxito", "error", "info", "advertencia"]

    return render_template(
        "logs.html",
        logs=logs,
        fase_actual=fase,
        resultado_actual=resultado,
        fases=fases_posibles,
        resultados=resultados_posibles,
    )
