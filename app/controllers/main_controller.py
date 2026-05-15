import os
import unicodedata
import numpy as np
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, session
import pandas as pd
from app.services.file_manager import FileManager
from app.config import DATA_DIR, TESSERACT_PATH, LOG_DB_PATH
from app.services.log_service import LogService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # Obtener valores de sesión y convertir None a '--'
    totales_orion = session.get("totales_orion")
    totales_aister = session.get("totales_aister")
    ultima_fecha = session.get("ultima_fecha", "202605_12")

    if totales_orion is None:
        totales_orion = "--"
    if totales_aister is None:
        totales_aister = "--"

    return render_template(
        "index.html",
        titulo="Orion Procesos",
        totales_orion=totales_orion,
        totales_aister=totales_aister,
        ultima_fecha=ultima_fecha,
    )


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
    # from app.services.log_service import LogService
    # from app.config import LOG_DB_PATH

    return LogService(LOG_DB_PATH)


@main_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    res = fm.crear_estructura_diaria(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Estructura creada para {fecha}</div>"
        html += "<table class='dataframe'><tr><th>Carpeta</th><th>Ruta</th></tr>"
        for nombre in ["principal", "Reporte_Imagen", "Causales", "Lotes", "Discador"]:
            if nombre in res["rutas"]:
                ruta = res["rutas"][nombre]
                html += f"<tr><td>{nombre}</td><td style='font-size:0.75rem;'>{ruta}</td></tr>"
        html += "</table>"
    else:
        html = f"<div class='log-line error'>❌ {res['error']}</div>"
    return html

    fecha = request.args.get("fecha", "202605_12")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    res = fm.crear_estructura_diaria(fecha)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Estructura creada para {fecha}</div>"
        html += "<div class='carpetas-grid'>"
        # Orden específico para mostrar
        for nombre in ["principal", "Reporte_Imagen", "Causales", "Lotes", "Discador"]:
            if nombre in res["rutas"]:
                ruta = res["rutas"][nombre]
                icono = "📁" if nombre != "principal" else "📂"
                html += f"<div class='carpeta-card'><span class='carpeta-icon'>{icono}</span><span class='carpeta-nombre'>{nombre}</span><span class='carpeta-ruta'>{ruta}</span></div>"
        html += "</div>"
    else:
        html = f"<div class='log-line error'>❌ {res['error']}</div>"
    return html


@main_bp.route("/accion/verificar-red")
def accion_verificar_red():
    fecha = request.args.get("fecha", "202605_06")
    fm = FileManager(DATA_DIR, log_service=_obtener_log_service())
    res = fm.verificar_red_y_carpetas(fecha)

    if res["success"]:
        # Guardar ruta activa en sesión
        session["red_base_activa"] = res.get("red_base_usada")
        red_usada = res.get("red_base_usada", "No especificada")

        html = f"<div class='log-line success'>✅ Red verificada correctamente</div>"
        html += f"<p style='margin:5px 0; font-size:0.8rem;'>📍 <b>Unidad de red:</b> {red_usada}</p>"

        # Mostrar rutas de año y mes
        rutas = res.get("rutas_validadas", {})
        if "anio" in rutas:
            html += (
                f"<p style='font-size:0.7rem; color:#ccc;'>📂 Año: {rutas['anio']}</p>"
            )
        if "mes" in rutas:
            html += (
                f"<p style='font-size:0.7rem; color:#ccc;'>📅 Mes: {rutas['mes']}</p>"
            )

        # Tabla de subcarpetas y archivos encontrados
        html += "<table class='dataframe' style='width:100%;'><tr><th>Subcarpeta</th><th>Ruta</th><th>Archivos encontrados</th></tr>"
        for sub, ruta_sub in rutas.items():
            if sub in ["Causales", "Discador", "Lotes"]:
                archivos = res.get("archivos_encontrados", {}).get(sub, [])
                if archivos:
                    html += f"<tr><td>{sub}</td><td style='font-size:0.6rem;'>{ruta_sub}</td><td>{', '.join(archivos)}</td></tr>"
                else:
                    html += f"<tr><td>{sub}</td><td style='font-size:0.6rem;'>{ruta_sub}</td><td style='color:#ffc107;'>Ninguno</td></tr>"
        html += "</table>"

        # Mensajes adicionales
        for msg in res.get("mensajes", []):
            if "Advertencia" in msg or "anterior" in msg:
                html += f"<p style='color:#ffc107; font-size:0.7rem;'>{msg}</p>"
            else:
                html += f"<p style='font-size:0.7rem; color:#aaa;'>{msg}</p>"
    else:
        # Error: mostrar ruta probada y el motivo
        red_probada = res.get("red_base_usada", "No disponible")
        html = f"<div class='log-line error'>❌ {res.get('error', 'Error desconocido')}</div>"
        html += f"<p style='font-size:0.7rem;'>Ruta probada: {red_probada}</p>"

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
    red_base = session.get("red_base_activa")
    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    # Verificar nuevamente usando la ruta base activa
    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)
    if not res_verif["success"]:
        return f"<div class='log-line error'>❌ No se puede distribuir: {res_verif['error']}</div>"

    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")
    os.makedirs(carpeta_diaria, exist_ok=True)

    res_dist = fm.distribuir_archivos(
        res_verif["rutas_validadas"], carpeta_diaria, res_verif["archivos_encontrados"]
    )

    if res_dist["success"]:
        html = "<div class='log-line success'>✅ Archivos distribuidos correctamente.</div>"
        html += "<table class='dataframe'><tr><th>Origen</th><th>Archivo</th><th>Destino</th></tr>"
        for destino in res_dist["copiados"]:
            nombre = os.path.basename(destino)
            # Determinar origen aproximado desde las rutas validadas
            origen = "Red"
            for cat, ruta_red in res_verif["rutas_validadas"].items():
                if cat in ["Causales", "Lotes", "Discador"]:
                    if (
                        os.path.join(carpeta_diaria, nombre) == destino
                        or os.path.join(carpeta_diaria, cat, nombre) == destino
                    ):
                        origen = cat
                        break
            html += f"<tr><td>{origen}</td><td>{nombre}</td><td style='font-size:0.7rem;'>{destino}</td></tr>"
        html += "</table>"
    else:
        html = (
            "<div class='log-line warning'>⚠️ Distribución parcial o con errores.</div>"
        )
        if res_dist.get("errores"):
            html += "<ul style='color:#ffc107; font-size:0.7rem;'>"
            for error in res_dist["errores"]:
                html += f"<li>{error}</li>"
            html += "</ul>"
        if res_dist.get("copiados"):
            html += "<p style='font-size:0.7rem;'>Archivos copiados exitosamente:</p><ul style='font-size:0.7rem;'>"
            for f in res_dist["copiados"]:
                html += f"<li>{os.path.basename(f)}</li>"
            html += "</ul>"
    return html


@main_bp.route("/accion/procesar-discador")
def accion_procesar_discador():

    fecha = request.args.get("fecha", "202605_12")
    # Tomar total de OCR de la sesión; si no existe, usar parámetro (o 0)
    total_esperado = session.get("totales_orion")
    if total_esperado is None:
        total_esperado = request.args.get("total", 0, type=int)

    from app.services.discador_processor import DiscadorProcessor

    disc = DiscadorProcessor(log_service=_obtener_log_service())
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    archivos = [
        f
        for f in os.listdir(carpeta_diaria)
        if f.lower().endswith(".xlsx") and "discador" in f.lower()
    ]
    if not archivos:
        return "<div class='log-line error'>❌ No se encontró archivo Discador en la carpeta diaria.</div>"
    ruta_disc = os.path.join(carpeta_diaria, archivos[0])

    # DEBUG: valores únicos de Campaña (permanente, colapsable)
    debug_html = ""
    try:
        df_temp = pd.read_excel(ruta_disc, dtype=str)
        if "Campaña" in df_temp.columns:
            unicos = df_temp["Campaña"].dropna().unique()[:10]
            debug_html = "<details style='margin-bottom:8px;'><summary style='font-size:0.75rem; color:#ffc107; cursor:pointer;'>🔍 Valores únicos de Campaña</summary>"
            debug_html += f"<ul style='font-size:0.7rem; color:#ffc107;'>{''.join(f'<li>{v}</li>' for v in unicos)}</ul></details>"
        else:
            debug_html = "<p style='color:#ffc107;'>No existe columna Campaña</p>"
    except Exception as e:
        debug_html = f"<p style='color:#ffc107;'>Error al leer: {e}</p>"

    res = disc.procesar(ruta_disc, total_esperado, carpeta_diaria)

    if res["success"]:
        html = (
            debug_html
            + f"<div class='log-line success'>✅ Discador procesado correctamente.</div>"
        )

        # Tabla de pasos de filtrado
        if "pasos_filtrado" in res:
            pasos = res["pasos_filtrado"]
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Proceso de filtrado:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Paso</th><th>Cantidad</th></tr>"
            html += (
                f"<tr><td>Registros originales</td><td>{pasos['original']}</td></tr>"
            )
            html += f"<tr><td>Tras filtro Campaña</td><td>{pasos['despues_campania']}</td></tr>"
            html += f"<tr><td>Tras filtro Estado (válidos)</td><td>{pasos['valido']}</td></tr>"
            html += "</table>"

        # Tabla de reemplazos de guiones
        if "reemplazos" in res and res["reemplazos"]:
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>🔄 Reemplazos de '-' por NULL:</p>"
            html += "<table class='dataframe' style='width:100%;'><tr><th>Columna</th><th>Cantidad</th></tr>"
            for col, cantidad in res["reemplazos"].items():
                html += f"<tr><td>{col}</td><td>{cantidad}</td></tr>"
            html += "</table>"

        # Tabla resumen
        html += "<table class='dataframe' style='width:100%;'><tr><th>Indicador</th><th>Valor</th></tr>"
        html += (
            f"<tr><td>Total esperado (OCR)</td><td>{res['total_esperado']}</td></tr>"
        )
        html += f"<tr><td>Total válidos</td><td>{res['total_validos']}</td></tr>"
        html += f"<tr><td>Total no válidos</td><td>{res['total_no_validos']}</td></tr>"
        html += f"<tr><td>Cuadre</td><td>{'✅ Correcto' if res['cuadre_ok'] else '❌ No coincide'}</td></tr>"
        html += "</table>"
        html += f"<p style='font-size:0.75rem; color:#aaa;'>{res['mensaje']}</p>"

        # Previsualización
        if res["ruta_limpio"]:
            try:
                df = pd.read_excel(res["ruta_limpio"])
                html += "<details style='margin-top:8px;'><summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>📋 Vista previa (primeras 5 filas)</summary>"
                html += df.head(5).to_html(index=False, classes="dataframe")
                html += "</details>"
            except Exception:
                pass
    else:
        html = debug_html + f"<div class='log-line error'>❌ {res['mensaje']}</div>"
    return html


@main_bp.route("/accion/procesar-causales")
def accion_procesar_causales():
    fecha = request.args.get("fecha", "202605_12")
    from app.services.causales_processor import CausalesProcessor

    caus = CausalesProcessor(log_service=_obtener_log_service())
    carpeta_causales = os.path.join(DATA_DIR, f"orion_{fecha}", "Causales")
    if not os.path.isdir(carpeta_causales):
        return "<div class='log-line error'>❌ No existe la carpeta Causales.</div>"

    res = caus.procesar_carpeta_causales(carpeta_causales, carpeta_causales)
    if res["success"]:
        html = f"<div class='log-line success'>✅ Causales procesados correctamente. ({res['total_archivos']} archivos)</div>"

        # Tabla de estadísticas por archivo con pasos intermedios
        if res.get("estadisticas_archivos"):
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
            html += "<table class='dataframe' style='width:100%;'>"
            html += "<tr><th>Archivo</th><th>Original</th><th>Tras Campaña</th><th>Tras Evento</th><th>Normalizados</th></tr>"
            for est in res["estadisticas_archivos"]:
                html += f"<tr><td>{est['archivo']}</td><td>{est['original']}</td><td>{est['tras_campania']}</td><td>{est['tras_evento']}</td><td>{est['normalizaciones']}</td></tr>"
            # Fila de totales (suma de todos los archivos)
            total_orig = sum(e["original"] for e in res["estadisticas_archivos"])
            total_camp = sum(e["tras_campania"] for e in res["estadisticas_archivos"])
            total_event = sum(e["tras_evento"] for e in res["estadisticas_archivos"])
            total_norm = sum(e["normalizaciones"] for e in res["estadisticas_archivos"])
            html += f"<tr style='font-weight:bold;'><td>TOTAL</td><td>{total_orig}</td><td>{total_camp}</td><td>{total_event}</td><td>{total_norm}</td></tr>"
            html += "</table>"

        # Tabla resumen consolidado
        html += "<table class='dataframe' style='width:100%; margin-top:8px;'><tr><th>Indicador</th><th>Valor</th></tr>"
        html += f"<tr><td>Total archivos procesados</td><td>{res['total_archivos']}</td></tr>"
        html += (
            f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        )
        html += "</table>"

        # Vista previa
        if res.get("preview_html"):
            html += "<details style='margin-top:8px;'><summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>📋 Vista previa (primeras 10 filas)</summary>"
            html += res["preview_html"]
            html += "</details>"
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
    return html


@main_bp.route("/accion/procesar-lotes")
def accion_procesar_lotes():
    fecha = request.args.get("fecha", "202605_12")
    from app.services.lotes_processor import LotesProcessor

    lotes = LotesProcessor(log_service=_obtener_log_service())
    carpeta_lotes = os.path.join(DATA_DIR, f"orion_{fecha}", "Lotes")
    if not os.path.isdir(carpeta_lotes):
        return "<div class='log-line error'>❌ No existe la carpeta Lotes.</div>"

    # Buscar archivo del discador limpio para validación cruzada (opcional)
    ruta_disc = os.path.join(DATA_DIR, f"orion_{fecha}", "discador_ejemplo_limpio.xlsx")
    res = lotes.procesar_carpeta_lotes(
        carpeta_lotes, fecha, ruta_disc if os.path.isfile(ruta_disc) else None
    )

    if res["success"]:
        html = f"<div class='log-line success'>✅ Lotes procesados correctamente.</div>"

        # Tabla de estadísticas por archivo
        if res.get("estadisticas_archivos"):
            html += "<p style='font-size:0.75rem; color:#ccc; margin:5px 0;'>📊 Procesamiento por archivo:</p>"
            html += "<table class='dataframe' style='width:100%;'>"
            html += "<tr><th>Archivo</th><th>Pivoteo</th><th>Filas orig.</th><th>Filas tras piv.</th><th>Cod.Cliente texto</th><th>Filas Cuenta con dato</th></tr>"
            for est in res["estadisticas_archivos"]:
                pivoteo = "Sí" if est["pivot_aplicado"] else "No"
                cod_cliente = "Sí" if est.get("codigo_cliente_forzado") else "No"
                cuenta_dato = est.get("cuenta_filas_con_dato", 0)
                html += f"<tr><td>{est['archivo']}</td><td>{pivoteo}</td>"
                html += f"<td>{est['filas_originales']}</td><td>{est['filas_despues_pivot']}</td>"
                html += f"<td>{cod_cliente}</td><td>{cuenta_dato}</td></tr>"
            html += "</table>"

        # Tabla resumen
        html += "<table class='dataframe' style='width:100%; margin-top:8px;'><tr><th>Indicador</th><th>Valor</th></tr>"
        html += (
            f"<tr><td>Total filas consolidadas</td><td>{res['total_filas']}</td></tr>"
        )
        if res.get("validacion_cruzada"):
            estado = "✅ OK" if res["validacion_cruzada"]["ok"] else "❌ Fallo"
            html += f"<tr><td>Validación cruzada</td><td>{estado}</td></tr>"
        html += "</table>"

        # Mensajes relevantes
        for msg in res.get("mensajes", []):
            html += f"<p style='font-size:0.7rem; color:#aaa; margin:3px 0;'>{msg}</p>"

        # Vista previa
        if res.get("preview_html"):
            html += "<details style='margin-top:8px;'><summary style='font-size:0.75rem; color:#ccc; cursor:pointer;'>📋 Vista previa (primeras 10 filas)</summary>"
            html += res["preview_html"]
            html += "</details>"
    else:
        html = f"<div class='log-line error'>❌ {' '.join(res['mensajes'])}</div>"
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

    fases_posibles = ["2.1", "2.2", "2.3", "3.2", "4.1", "4.2", "4.3"]
    resultados_posibles = ["éxito", "error", "info", "advertencia"]

    # Obtener totales de la sesión (igual que en index)
    totales_orion = session.get("totales_orion")
    totales_aister = session.get("totales_aister")
    ultima_fecha = session.get("ultima_fecha", "202605_12")
    if totales_orion is None:
        totales_orion = "--"
    if totales_aister is None:
        totales_aister = "--"

    return render_template(
        "logs.html",
        logs=logs,
        fase_actual=fase,
        resultado_actual=resultado,
        fases=fases_posibles,
        resultados=resultados_posibles,
        totales_orion=totales_orion,
        totales_aister=totales_aister,
        ultima_fecha=ultima_fecha,
    )


@main_bp.route("/accion/ocr-subir", methods=["POST"])
def accion_ocr_subir():
    """Recibe imágenes, las guarda en Reporte_Imagen y ejecuta OCR."""
    from app.services.ocr_processor import OCRProcessor
    import base64

    fecha = request.form.get("fecha", "202605_12")
    archivos = request.files.getlist("imagenes")

    if not archivos or all(archivo.filename == "" for archivo in archivos):
        return "<div class='log-line error'>❌ No se seleccionó ninguna imagen.</div>"

    carpeta_destino = os.path.join(DATA_DIR, f"orion_{fecha}", "Reporte_Imagen")
    os.makedirs(carpeta_destino, exist_ok=True)

    log_srv = _obtener_log_service()
    ocr = OCRProcessor(TESSERACT_PATH, log_service=log_srv)

    totales_finales = {"orion": None, "aister": None}
    archivos_procesados = []
    preview_imagenes = []  # Lista de (nombre, base64)

    for idx, archivo in enumerate(archivos):
        if archivo.filename == "":
            continue
        nombre_base = secure_filename(archivo.filename)
        nombre_unico = f"{pd.Timestamp.now().strftime('%H%M%S')}_{idx}_{nombre_base}"
        ruta_guardada = os.path.join(carpeta_destino, nombre_unico)
        archivo.save(ruta_guardada)
        archivos_procesados.append(nombre_unico)

        # Guardar hasta 3 imágenes en base64 para mostrar
        if len(preview_imagenes) < 3:
            with open(ruta_guardada, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode("utf-8")
            preview_imagenes.append((nombre_unico, img_b64))

        texto = ocr.extraer_texto(ruta_guardada)
        nombre_lower = archivo.filename.lower()
        es_orion = "orion" in nombre_lower
        es_aister = "aister" in nombre_lower or "aster" in nombre_lower

        # 1. Método específico (Total general Orion/Aister)
        totales_especificos = ocr.extraer_totales(texto)
        if totales_finales["orion"] is None and totales_especificos["orion"]:
            totales_finales["orion"] = totales_especificos["orion"]
        if totales_finales["aister"] is None and totales_especificos["aister"]:
            totales_finales["aister"] = totales_especificos["aister"]

        # 2. Método genérico "Total general"
        if totales_finales["orion"] is None or totales_finales["aister"] is None:
            numeros_gen = ocr.extraer_totales_generico(texto)
            if numeros_gen:
                if len(numeros_gen) == 1:
                    if es_orion and totales_finales["orion"] is None:
                        totales_finales["orion"] = numeros_gen[0]
                    elif es_aister and totales_finales["aister"] is None:
                        totales_finales["aister"] = numeros_gen[0]
                elif len(numeros_gen) >= 2:
                    # Dos números: asignar el que corresponda al archivo actual
                    if es_orion and totales_finales["orion"] is None:
                        totales_finales["orion"] = numeros_gen[0]
                    elif es_aister and totales_finales["aister"] is None:
                        totales_finales["aister"] = numeros_gen[-1]
                    else:
                        # Archivo no identificado: asignar ambos si faltan
                        if totales_finales["orion"] is None:
                            totales_finales["orion"] = numeros_gen[0]
                        if totales_finales["aister"] is None:
                            totales_finales["aister"] = numeros_gen[-1]

        # 3. Respaldo: buscar número cerca de "Orion" o "Aister"
        if totales_finales["orion"] is None and es_orion:
            num = ocr.extraer_numero_cercano(texto, "Orion")
            if num:
                totales_finales["orion"] = num
        if totales_finales["aister"] is None and es_aister:
            num = ocr.extraer_numero_cercano(texto, "Aister")
            if num:
                totales_finales["aister"] = num

    # Guardar en sesión
    session["totales_orion"] = totales_finales["orion"]
    session["totales_aister"] = totales_finales["aister"]
    session["ultima_fecha"] = fecha

    # Construir HTML con diseño de dos columnas
    html = '<div class="ocr-result-container">'

    # Columna izquierda: imágenes
    html += '<div class="ocr-images">'
    if preview_imagenes:
        for nombre, img_b64 in preview_imagenes:
            html += f"<div class='ocr-thumb'><img src='data:image/png;base64,{img_b64}' alt='{nombre}'/><small>{nombre}</small></div>"
    else:
        html += "<p style='color:#888;'>No hay imágenes disponibles.</p>"
    html += "</div>"

    # Columna derecha: resultados
    # Construir HTML con diseño mejorado
    html = '<div class="ocr-result-container">'

    # Columna izquierda: imágenes (más grandes)
    html += '<div class="ocr-images">'
    if preview_imagenes:
        for nombre, img_b64 in preview_imagenes:
            html += f"<div class='ocr-thumb'><img src='data:image/png;base64,{img_b64}' alt='{nombre}'/><small>{nombre}</small></div>"
    else:
        html += "<p style='color:#888;'>No hay imágenes disponibles.</p>"
    html += "</div>"

    # Columna derecha: resultados
    html += '<div class="ocr-results">'
    if totales_finales["orion"] is not None or totales_finales["aister"] is not None:
        html += f"<div class='log-line success'>✅ OCR completado</div>"
        # Fila que agrupa totales y archivos guardados
        html += '<div class="totales-archivos-row">'
        html += '<div class="totales-grid">'
        html += f"<div class='total-card'><span class='label'>🔹 Orion</span><span class='value'>{totales_finales['orion']}</span></div>"
        html += f"<div class='total-card'><span class='label'>🔹 Aister</span><span class='value'>{totales_finales['aister']}</span></div>"
        html += "</div>"
        # Archivos guardados (colapsable) al mismo nivel
        html += f'<details class="archivos-guardados"><summary>📁 Archivos guardados ({len(archivos_procesados)})</summary><ul>'
        for nombre in archivos_procesados:
            html += f"<li>{nombre}</li>"
        html += "</ul></details>"
        html += "</div>"  # cierra totales-archivos-row
    else:
        html += "<div class='log-line warning'>⚠️ No se detectaron totales en las imágenes. ¿El reporte tiene el formato esperado? Revise los logs.</div>"

    html += "</div>"  # cierra ocr-results
    # Datos invisibles para JS: totales en formato data-*
    html += f'<div id="ocr-data" style="display:none;" data-orion="{totales_finales["orion"]}" data-aister="{totales_finales["aister"]}"></div>'
    html += "</div>"  # cierra ocr-result-container

    return html


@main_bp.route("/reset-logs", methods=["POST"])
def reset_logs():
    """Vacia la tabla de logs."""
    from app.config import LOG_DB_PATH
    import sqlite3

    try:
        with sqlite3.connect(LOG_DB_PATH) as conn:
            conn.execute("DELETE FROM action_log")
            conn.commit()
        return "<div class='log-line success'>✅ Logs eliminados correctamente.</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al resetear logs: {e}</div>"


@main_bp.route("/accion/comparar-lotes")
def accion_comparar_lotes():
    fecha = request.args.get("fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    # --- 1. Crear Carpetas ---
    rutas_creadas = {}
    for sub in ["principal", "Reporte_Imagen", "Causales", "Lotes", "Discador"]:
        if sub == "principal":
            ruta = carpeta_diaria
        else:
            ruta = os.path.join(carpeta_diaria, sub)
        rutas_creadas[sub] = ruta if os.path.isdir(ruta) else None

    # --- 2. Verificar Red (simplificado: vemos si hay archivos en Lotes/Discador) ---
    # Tomamos la ruta base activa guardada en sesión (si existe)
    red_base = session.get("red_base_activa", "No verificada")

    # --- 3. Distribuir ---
    # Contamos archivos en las subcarpetas locales (excepto Reporte_Imagen)
    archivos_distribuidos = {}
    for sub in ["Causales", "Lotes", "Discador"]:
        ruta_sub = os.path.join(carpeta_diaria, sub)
        if os.path.isdir(ruta_sub):
            archivos = os.listdir(ruta_sub)
            archivos_distribuidos[sub] = len(archivos)
        else:
            archivos_distribuidos[sub] = 0

    # --- 4. Procesar Discador ---
    disc_stats = {"original": 0, "despues_campania": 0, "valido": 0}
    ruta_disc = None
    archivos_disc = [
        f
        for f in os.listdir(carpeta_diaria)
        if f.lower().endswith("_limpio.xlsx") and "discador" in f.lower()
    ]
    if archivos_disc:
        ruta_disc = os.path.join(carpeta_diaria, archivos_disc[0])
        try:
            df_disc = pd.read_excel(ruta_disc, dtype=str)
            disc_stats["valido"] = len(df_disc)
            # Intentar cargar original desde el archivo no limpio (si existe)
            # Usamos el archivo original descargado (sin _limpio)
            original = archivos_disc[0].replace("_limpio", "")
            ruta_original = os.path.join(carpeta_diaria, original)
            if os.path.isfile(ruta_original):
                df_orig = pd.read_excel(ruta_original, dtype=str)
                disc_stats["original"] = len(df_orig)
                # Campaña contiene "Cobranzas"
                mask = df_orig["Campaña"].str.contains(
                    "Cobranzas", case=False, na=False
                )
                disc_stats["despues_campania"] = int(mask.sum())
        except:
            pass

    # --- 5. Procesar Causales ---
    causales_stats = {"original": 0, "despues_campania": 0, "valido": 0}
    ruta_caus = None
    carpeta_causales = os.path.join(carpeta_diaria, "Causales")
    if os.path.isdir(carpeta_causales):
        archivos_caus = [
            f
            for f in os.listdir(carpeta_causales)
            if f.lower().endswith("_limpio.xlsx")
        ]
        if archivos_caus:
            ruta_caus = os.path.join(carpeta_causales, archivos_caus[0])
            try:
                df_caus = pd.read_excel(ruta_caus, dtype=str)
                causales_stats["valido"] = len(df_caus)
                # Buscar original
                original_caus = archivos_caus[0].replace("_limpio", "")
                ruta_orig_caus = os.path.join(carpeta_causales, original_caus)
                if os.path.isfile(ruta_orig_caus):
                    df_orig_caus = pd.read_excel(ruta_orig_caus, skiprows=2, dtype=str)
                    causales_stats["original"] = len(df_orig_caus)
                    mask_camp = df_orig_caus["Campaña"].str.contains(
                        "Cobranzas", case=False, na=False
                    )
                    causales_stats["despues_campania"] = int(mask_camp.sum())
            except:
                pass

    # --- 6. Procesar Lotes ---
    lotes_stats_list = []
    ruta_lotes = None
    carpeta_lotes = os.path.join(carpeta_diaria, "Lotes")
    if os.path.isdir(carpeta_lotes):
        archivos_cons = [
            f
            for f in os.listdir(carpeta_lotes)
            if f.lower().startswith("lote_consolidado") and f.endswith(".xlsx")
        ]
        if archivos_cons:
            ruta_lotes = os.path.join(carpeta_lotes, archivos_cons[0])
            # Obtener estadísticas por archivo (ya no las tenemos guardadas, podemos omitir o leer del consolidado)
            try:
                df_lotes = pd.read_excel(ruta_lotes, dtype=str)
                # Agrupamos por Nombre_Lote
                if "Nombre_Lote" in df_lotes.columns:
                    for nombre, grupo in df_lotes.groupby("Nombre_Lote"):
                        lotes_stats_list.append(
                            {
                                "archivo": nombre,
                                "filas": len(grupo),
                                "pivoteo": (
                                    "Sí" if "phone_number" in nombre else "No"
                                ),  # aproximado
                            }
                        )
            except:
                pass

    # --- 7. Comparación ---
    datos_comparacion = []
    if ruta_disc and ruta_lotes:
        try:
            df_disc_comp = pd.read_excel(ruta_disc, dtype=str)
            df_lotes_comp = pd.read_excel(ruta_lotes, dtype=str)
            if (
                "Lote" in df_disc_comp.columns
                and "Nombre_Lote" in df_lotes_comp.columns
            ):
                lotes_disc = set(df_disc_comp["Lote"].dropna().unique())
                lotes_lotes = set(df_lotes_comp["Nombre_Lote"].dropna().unique())
                todos = sorted(lotes_disc.union(lotes_lotes))
                for lote in todos:
                    datos_comparacion.append(
                        {
                            "Lote": lote,
                            "En Discador": "Sí" if lote in lotes_disc else "No",
                            "En Lotes": "Sí" if lote in lotes_lotes else "No",
                        }
                    )
        except:
            pass

    # --- Construir HTML para panel ---
    html = "<div class='log-line success'>✅ Resumen general generado.</div>"
    # (Mostrar las tablas igual que antes, resumidas)
    html += "<p style='font-size:0.75rem; color:#ccc;'>📁 Archivos limpios:</p>"
    html += "<table class='dataframe' style='width:100%;'><tr><th>Tipo</th><th>Ruta</th></tr>"
    html += f"<tr><td>Discador limpio</td><td>{ruta_disc or 'No encontrado'}</td></tr>"
    html += f"<tr><td>Causales limpio</td><td>{ruta_caus or 'No encontrado'}</td></tr>"
    html += (
        f"<tr><td>Lotes consolidado</td><td>{ruta_lotes or 'No encontrado'}</td></tr>"
    )
    html += "</table>"
    if datos_comparacion:
        html += "<table class='dataframe' style='width:100%; margin-top:10px;'><tr><th>Lote</th><th>En Discador</th><th>En Lotes</th></tr>"
        for fila in datos_comparacion:
            html += f"<tr><td>{fila['Lote']}</td><td>{fila['En Discador']}</td><td>{fila['En Lotes']}</td></tr>"
        html += "</table>"

    # --- Generar Excel de resumen en una sola hoja ---
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "Resumen"

        # Estilos
        title_font = Font(bold=True, size=12, color="FFFFFF")
        title_fill = PatternFill(
            start_color="4F81BD", end_color="4F81BD", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="4F81BD", end_color="4F81BD", fill_type="solid"
        )
        normal_font = Font(size=10)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        row = 1

        def escribir_titulo(titulo):
            nonlocal row
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            cell = ws.cell(row=row, column=1, value=titulo)
            cell.font = title_font
            cell.fill = title_fill
            cell.alignment = Alignment(horizontal="center")
            row += 1

        def escribir_tabla(headers, data):
            nonlocal row
            # Encabezados
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center")
            row += 1
            # Datos
            for fila in data:
                for col, valor in enumerate(fila, 1):
                    cell = ws.cell(row=row, column=col, value=valor)
                    cell.font = normal_font
                    cell.border = thin_border
                row += 1
            row += 1  # espacio

        escribir_titulo("1. Crear Carpetas")
        escribir_tabla(
            ["Carpeta", "Ruta"],
            [[k, v or "No creada"] for k, v in rutas_creadas.items()],
        )

        escribir_titulo("2. Verificar Red")
        escribir_tabla(
            ["Unidad de Red", "Estado"],
            [
                [
                    red_base,
                    "Verificada" if red_base != "No verificada" else "No verificada",
                ]
            ],
        )

        escribir_titulo("3. Distribuir Archivos")
        escribir_tabla(
            ["Subcarpeta", "Cantidad de archivos"],
            [[k, v] for k, v in archivos_distribuidos.items()],
        )

        escribir_titulo("4. Procesar Discador")
        escribir_tabla(
            ["Paso", "Cantidad"],
            [
                ["Registros originales", disc_stats["original"]],
                ["Tras filtro Campaña", disc_stats["despues_campania"]],
                ["Válidos finales", disc_stats["valido"]],
            ],
        )

        escribir_titulo("5. Procesar Causales")
        escribir_tabla(
            ["Paso", "Cantidad"],
            [
                ["Registros originales", causales_stats["original"]],
                ["Tras filtro Campaña", causales_stats["despues_campania"]],
                ["Válidos finales", causales_stats["valido"]],
            ],
        )

        escribir_titulo("6. Procesar Lotes")
        if lotes_stats_list:
            escribir_tabla(
                ["Archivo", "Filas consolidadas", "Pivoteo aplicado"],
                [[e["archivo"], e["filas"], e["pivoteo"]] for e in lotes_stats_list],
            )
        else:
            escribir_tabla(["Estado"], [["No se encontró consolidado de Lotes"]])

        escribir_titulo("7. Comparación de Lotes")
        if datos_comparacion:
            escribir_tabla(
                ["Lote", "En Discador", "En Lotes"],
                [
                    [f["Lote"], f["En Discador"], f["En Lotes"]]
                    for f in datos_comparacion
                ],
            )
        else:
            escribir_tabla(["Estado"], [["No se pudo realizar la comparación"]])

        # Ajustar ancho de columnas
        for col in range(1, 4):
            ws.column_dimensions[get_column_letter(col)].width = 30

        # Guardar archivo
        fecha_archivo = fecha.replace("_", "")[4:]
        ruta_resumen = os.path.join(
            carpeta_diaria, f"Resumen_Orion_{fecha_archivo}.xlsx"
        )
        wb.save(ruta_resumen)

        html += f"<p style='color:#28a745; font-size:0.8rem; margin-top:10px;'>📊 Resumen Excel generado: {ruta_resumen}</p>"
    except Exception as e:
        html += f"<p style='color:#dc3545;'>❌ Error al generar Excel: {e}</p>"

    return html


@main_bp.route("/accion/consolidar-totales", methods=["POST"])
def accion_consolidar_totales():
    """Recibe totales manuales desde el frontend y los guarda en sesión."""
    try:
        orion = request.form.get("orion", type=int)
        aister = request.form.get("aister", type=int)
        session["totales_orion"] = orion
        session["totales_aister"] = aister
        return (
            "<div class='log-line success'>✅ Totales consolidados correctamente.</div>"
        )
    except Exception as e:
        return f"<div class='log-line error'>❌ Error: {e}</div>"


@main_bp.route("/reset")
def reset_proceso():
    """Limpia la sesión y registra el reinicio en los logs."""
    # Registrar en log antes de limpiar sesión
    log_srv = _obtener_log_service()
    log_srv.log(
        "Reset",
        "Reinicio del proceso",
        "info",
        "El usuario solicitó reiniciar todo el proceso.",
    )

    session.clear()
    return "<div class='log-line success'>✅ Sesión reiniciada. Redirigiendo...</div>"


@main_bp.route("/accion/probar-conexion", methods=["POST"])
def accion_probar_conexion():
    """Recibe datos de conexión y prueba conexión a SQL Server."""
    import pyodbc

    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    if not servidor or not basedatos:
        return "<div class='log-line error'>❌ Faltan datos obligatorios (servidor y base de datos).</div>"

    try:
        if "localdb" in servidor.lower():
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={servidor};"
                f"DATABASE={basedatos};"
                f"Trusted_Connection=yes;"
            )
        else:
            if autenticacion == "windows":
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={servidor},{puerto};"
                    f"DATABASE={basedatos};"
                    f"Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={servidor},{puerto};"
                    f"DATABASE={basedatos};"
                    f"UID={usuario};"
                    f"PWD={password};"
                )

        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return f"<div class='log-line success'>✅ Conexión exitosa a {servidor}/{basedatos}</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {str(e)}</div>"


@main_bp.route("/accion/probar-lectura", methods=["POST"])
def accion_probar_lectura():
    """Prueba conexión y lee los últimos 5 registros de Causales."""
    import pyodbc
    import pandas as pd

    servidor = request.form.get("servidor", "")
    puerto = request.form.get("puerto", "1433")
    basedatos = request.form.get("basedatos", "")
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    autenticacion = request.form.get("autenticacion", "sql")

    if not servidor or not basedatos:
        return "<div class='log-line error'>❌ Faltan datos obligatorios.</div>"

    try:
        if "localdb" in servidor.lower():
            conn_str = (
                r"DRIVER={ODBC Driver 17 for SQL Server};"
                rf"SERVER={servidor};"
                rf"DATABASE={basedatos};"
                r"Trusted_Connection=yes;"
            )
        else:
            if autenticacion == "windows":
                conn_str = (
                    r"DRIVER={ODBC Driver 17 for SQL Server};"
                    rf"SERVER={servidor},{puerto};"
                    rf"DATABASE={basedatos};"
                    r"Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    r"DRIVER={ODBC Driver 17 for SQL Server};"
                    rf"SERVER={servidor},{puerto};"
                    rf"DATABASE={basedatos};"
                    rf"UID={usuario};"
                    rf"PWD={password};"
                )

        conn = pyodbc.connect(conn_str, timeout=5)
        query = "SELECT TOP 5 * FROM Causales"
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return "<div class='log-line warning'>⚠️ La tabla Causales existe pero no contiene registros.</div>"

        html = f"<div class='log-line success'>✅ Lectura exitosa. {len(df)} registros encontrados.</div>"
        html += df.to_html(index=False, classes="dataframe")
        return html

    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer Causales: {str(e)}</div>"


@main_bp.route("/accion/verificar-carga", methods=["POST"])
def accion_verificar_carga():
    import pyodbc
    import pandas as pd
    from app.config import SQL_LOCAL, SQL_REMOTO

    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    if conexion == "remoto":
        cfg = SQL_REMOTO
    else:
        cfg = SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    # Rutas y tabla destino (sin cambios)
    ruta_archivo = None
    nombre_archivo = None
    if tipo == "causales":
        carpeta = os.path.join(carpeta_diaria, "Causales")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Causales_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "[dbo].[Causales]"  # para Causales
    elif tipo == "lote":
        carpeta = os.path.join(carpeta_diaria, "Lotes")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Lote_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "[dbo].[Lote]"  # para Lote
    elif tipo == "discador":
        archivos = [
            f
            for f in os.listdir(carpeta_diaria)
            if "discador" in f.lower() and f.endswith("Consolidado.xlsx")
        ]
        if archivos:
            ruta_archivo = os.path.join(carpeta_diaria, archivos[0])
            nombre_archivo = archivos[0]
        tabla_destino = "[dbo].[Discador]"  # para Discador
    else:
        return "<div class='log-line error'>❌ Tipo de carga no válido.</div>"

    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return f"<div class='log-line error'>❌ No se encontró el archivo consolidado de {tipo}.</div>"

    # Leer archivo para columnas (como string para el match)
    try:
        df_archivo_str = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer el archivo: {e}"

    # Leer archivo para inferir tipos reales (solo una fila para no cargar todo)
    try:
        df_archivo_tipos = pd.read_excel(ruta_archivo, nrows=1)
    except:
        df_archivo_tipos = df_archivo_str  # fallback

    # Función de normalización
    def normalizar(texto):
        """Normaliza el texto para comparación: minúsculas, ñ → n, sin acentos, solo alfanumérico."""
        texto = str(texto).strip().lower()
        # Reemplazar ñ por n
        texto = texto.replace("ñ", "n")
        # Eliminar acentos
        texto = (
            unicodedata.normalize("NFKD", texto)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )
        # Eliminar cualquier carácter que no sea letra o dígito
        import re

        texto = re.sub(r"[^a-z0-9]", "", texto)
        return texto

    columnas_archivo = df_archivo_str.columns.tolist()

    # Guardar nombres originales antes de cualquier mapeo

    columnas_archivo_originales = columnas_archivo.copy()

    # Aplicar mapeo manual para Discador solo para comparación
    columnas_archivo_para_match = columnas_archivo.copy()
    # Mapeo manual para Discador: codigo_cliente -> NroCliente_Contrato
    if tipo == "discador":
        mapeo_discador = {"codigo_cliente": "NroCliente_Contrato"}
        columnas_archivo_para_match = [
            mapeo_discador[col] if col in mapeo_discador else col
            for col in columnas_archivo
        ]

    # Normalizar las columnas para comparación
    columnas_archivo_norm = [normalizar(col) for col in columnas_archivo_para_match]

    # Mapa de tipo de dato de cada columna del archivo
    tipos_archivo = {}
    for col in columnas_archivo:
        if col in df_archivo_tipos.columns:
            dtype = df_archivo_tipos[col].dtype
            tipos_archivo[col] = str(dtype)
        else:
            tipos_archivo[col] = "object"

    # Conexión y metadatos de SQL Server
    try:
        if cfg["auth"] == "windows":
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']},{cfg['port']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg['username']};"
                f"PWD={cfg['password']};"
            )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Obtener columnas y tipos de la tabla
        cursor.execute(
            f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? 
            ORDER BY ORDINAL_POSITION
        """,
            tabla_destino,
        )
        info_columnas = cursor.fetchall()
        if not info_columnas:
            conn.close()
            return f"<div class='log-line error'>❌ No se encontró la tabla {tabla_destino} en la base de datos.</div>"
        columnas_servidor = [row.COLUMN_NAME for row in info_columnas]
        tipos_servidor = {row.COLUMN_NAME: row.DATA_TYPE for row in info_columnas}
        columnas_servidor_norm = [normalizar(col) for col in columnas_servidor]

        # Último ID
        ultimo_id = None
        try:
            primera_col = columnas_servidor[0]
            cursor.execute(
                f"SELECT MAX(CAST({primera_col} AS BIGINT)) FROM {tabla_destino}"
            )
            val = cursor.fetchone()[0]
            if val is not None:
                ultimo_id = val
        except:
            pass

        # Conteo de registros en la tabla
        cursor.execute(f"SELECT COUNT(*) FROM {tabla_destino}")
        total_tabla = cursor.fetchone()[0]

        conn.close()

    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión a SQL Server: {e}"

    # Construir HTML
    html = f"<div class='log-line success'>✅ Verificación de {tipo.capitalize()} (conexión {conexion})</div>"
    html += f"<p style='font-size:0.75rem;'><b>Archivo:</b> {nombre_archivo}<br><b>Ruta:</b> {ruta_archivo}</p>"
    html += f"<p style='font-size:0.75rem;'><b>Tabla destino:</b> {tabla_destino} ({len(columnas_servidor)} columnas)</p>"

    # Tabla de columnas con coincidencias normalizadas y tipos
    html += "<table class='dataframe' style='width:100%; margin-top:8px;'>"
    html += "<tr><th>Columna en SQL Server</th><th>Columna en Archivo Excel</th><th>¿Coincide?</th><th>Tipo SQL Server</th><th>Tipo Excel</th></tr>"

    # Para cada columna del servidor, buscar si hay match normalizado en el archivo
    for i, col_srv in enumerate(columnas_servidor):
        norm_srv = columnas_servidor_norm[i]
        # Buscar en el archivo el primer nombre que coincida normalizado
        match_col = None
        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break
        coinciden = "✅" if match_col else "❌"
        tipo_srv = tipos_servidor.get(col_srv, "?")
        tipo_excel = tipos_archivo.get(match_col, "") if match_col else ""
        html += f"<tr><td>{col_srv}</td><td>{match_col or '—'}</td><td>{coinciden}</td><td>{tipo_srv}</td><td>{tipo_excel}</td></tr>"

    # Columnas del archivo que no aparecieron en el servidor (opcional mostrarlas al final)
    set_norm_srv = set(columnas_servidor_norm)
    for j, col_arch in enumerate(columnas_archivo_originales):
        if columnas_archivo_norm[j] not in set_norm_srv:
            tipo_excel = tipos_archivo.get(col_arch, "")
            html += f"<tr><td>—</td><td>{col_arch}</td><td>❌</td><td>—</td><td>{tipo_excel}</td></tr>"

    html += "</table>"

    # Estadísticas
    html += "<div style='display:flex; gap:20px; margin-top:10px; font-size:0.75rem;'>"
    html += f"<div><b>Registros en archivo:</b> {len(df_archivo_str)}</div>"
    if ultimo_id is not None:
        html += f"<div><b>Último ID en tabla:</b> {ultimo_id}</div>"
    html += f"<div><b>Registros en tabla:</b> {total_tabla}</div>"
    html += "</div>"

    # Último registro (detalle colapsable)
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP 1 * FROM {tabla_destino} ORDER BY (SELECT NULL)")
        row = cursor.fetchone()
        if row:
            cols = [column[0] for column in cursor.description]
            df_ultimo = pd.DataFrame([list(row)], columns=cols)
            html += "<details style='margin-top:8px;'><summary style='font-size:0.7rem; color:#ccc; cursor:pointer;'>📋 Último registro</summary>"
            html += df_ultimo.to_html(index=False, classes="dataframe")
            html += "</details>"
        conn.close()
    except:
        pass

    return html


@main_bp.route("/accion/cargar-datos", methods=["POST"])
def accion_cargar_datos():
    import pyodbc
    import pandas as pd
    import unicodedata
    import re
    from app.config import SQL_LOCAL, SQL_REMOTO

    tipo = request.form.get("tipo", "")
    conexion = request.form.get("conexion", "local")

    if conexion == "remoto":
        cfg = SQL_REMOTO
    else:
        cfg = SQL_LOCAL

    fecha = session.get("ultima_fecha", "202605_12")
    carpeta_diaria = os.path.join(DATA_DIR, f"orion_{fecha}")

    # ---------- Rutas y tabla destino ----------
    ruta_archivo = None
    nombre_archivo = None
    tabla_destino = None
    if tipo == "causales":
        carpeta = os.path.join(carpeta_diaria, "Causales")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Causales_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Causales"  # sin corchetes para pyodbc
    elif tipo == "lote":
        carpeta = os.path.join(carpeta_diaria, "Lotes")
        if os.path.isdir(carpeta):
            archivos = [
                f
                for f in os.listdir(carpeta)
                if f.startswith("Lote_Consolidado") and f.endswith(".xlsx")
            ]
            if archivos:
                ruta_archivo = os.path.join(carpeta, archivos[0])
                nombre_archivo = archivos[0]
        tabla_destino = "Lote"
    elif tipo == "discador":
        archivos = [
            f
            for f in os.listdir(carpeta_diaria)
            if "discador" in f.lower() and f.endswith("Consolidado.xlsx")
        ]
        if archivos:
            ruta_archivo = os.path.join(carpeta_diaria, archivos[0])
            nombre_archivo = archivos[0]
        tabla_destino = "Discador"
    else:
        return "<div class='log-line error'>❌ Tipo de carga no válido.</div>"

    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        return f"<div class='log-line error'>❌ No se encontró el archivo consolidado de {tipo}.</div>"

    # Leer archivo como string
    try:
        df = pd.read_excel(ruta_archivo, dtype=str)
    except Exception as e:
        return f"<div class='log-line error'>❌ Error al leer el archivo: {e}"

    registros_archivo = len(df)

    # ---------- Normalización ----------
    def normalizar(texto):
        texto = str(texto).strip().lower()
        texto = texto.replace("ñ", "n")
        texto = (
            unicodedata.normalize("NFKD", texto)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )
        texto = re.sub(r"[^a-z0-9]", "", texto)
        return texto

    # Nombres originales del archivo
    columnas_archivo_originales = df.columns.tolist()

    # Mapeo manual para Discador
    columnas_archivo_para_match = columnas_archivo_originales.copy()
    if tipo == "discador":
        mapeo_disc = {"codigo_cliente": "NroCliente_Contrato"}
        columnas_archivo_para_match = [
            mapeo_disc[col] if col in mapeo_disc else col
            for col in columnas_archivo_originales
        ]

    columnas_archivo_norm = [normalizar(col) for col in columnas_archivo_para_match]

    # ---------- Conexión y metadatos ----------
    try:
        if cfg["auth"] == "windows":
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']},{cfg['port']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg['username']};"
                f"PWD={cfg['password']};"
            )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Columnas y tipos de la tabla destino
        cursor.execute(
            f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? 
            ORDER BY ORDINAL_POSITION
        """,
            tabla_destino,
        )
        info_columnas = cursor.fetchall()
        if not info_columnas:
            conn.close()
            return f"<div class='log-line error'>❌ La tabla {tabla_destino} no existe en la base de datos.</div>"

        columnas_servidor = [row.COLUMN_NAME for row in info_columnas]
        tipos_servidor = {row.COLUMN_NAME: row.DATA_TYPE for row in info_columnas}

        # Contar registros antes
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        registros_antes = cursor.fetchone()[0]

        # No cerramos la conexión aún, la reutilizaremos para insertar

    except Exception as e:
        return f"<div class='log-line error'>❌ Error de conexión: {e}"

    # ---------- Construir tabla de coincidencia ----------
    html_verif = "<table class='dataframe' style='width:100%;'>"
    html_verif += "<tr><th>Columna SQL Server</th><th>Columna en Archivo</th><th>Coincide</th><th>Tipo SQL</th></tr>"
    mapeo_final = {}  # columna_servidor -> columna_archivo (nombre original)
    for col_srv in columnas_servidor:
        norm_srv = normalizar(col_srv)
        match_col = None
        for j, norm_arch in enumerate(columnas_archivo_norm):
            if norm_arch == norm_srv:
                match_col = columnas_archivo_originales[j]
                break
        coincide = "✅" if match_col else "❌"
        tipo_srv = tipos_servidor.get(col_srv, "?")
        html_verif += f"<tr><td>{col_srv}</td><td>{match_col or '—'}</td><td>{coincide}</td><td>{tipo_srv}</td></tr>"
        if match_col:
            mapeo_final[col_srv] = match_col

    # Columnas del archivo sin match
    set_norm_srv = set(normalizar(c) for c in columnas_servidor)
    for j, col_arch in enumerate(columnas_archivo_originales):
        if columnas_archivo_norm[j] not in set_norm_srv:
            html_verif += f"<tr><td>—</td><td>{col_arch}</td><td>❌</td><td>—</td></tr>"
    html_verif += "</table>"

    # ---------- Preparar DataFrame para inserción ----------
    try:
        # Construir DataFrame solo con columnas que coinciden (en el orden de la tabla)
        columnas_insert = list(mapeo_final.keys())
        df_insert = pd.DataFrame()
        for col_srv in columnas_insert:
            col_arch = mapeo_final[col_srv]
            df_insert[col_srv] = df[col_arch]

        # Conversión de tipos
        for col_srv, tipo_srv in tipos_servidor.items():
            if col_srv not in df_insert.columns:
                continue
            if tipo_srv in ("nvarchar", "varchar", "char", "text", "ntext"):
                df_insert[col_srv] = df_insert[col_srv].astype(str)
            elif tipo_srv in ("int", "smallint", "tinyint", "bigint"):
                df_insert[col_srv] = pd.to_numeric(
                    df_insert[col_srv], errors="coerce"
                ).astype("Int64")
            elif tipo_srv in ("float", "real", "decimal", "numeric", "money"):
                df_insert[col_srv] = pd.to_numeric(df_insert[col_srv], errors="coerce")
            elif tipo_srv in ("datetime", "datetime2", "smalldatetime", "date"):
                # Convertir a datetime, si falla dejar NaT
                df_insert[col_srv] = pd.to_datetime(
                    df_insert[col_srv], errors="coerce", dayfirst=True
                )
            elif tipo_srv == "bit":
                df_insert[col_srv] = (
                    df_insert[col_srv]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map(
                        {
                            "1": True,
                            "true": True,
                            "yes": True,
                            "0": False,
                            "false": False,
                            "no": False,
                        }
                    )
                )

        # Limpiar fechas fuera del rango permitido por SQL Server datetime
        for col_srv, tipo_srv in tipos_servidor.items():
            if tipo_srv in ('datetime', 'datetime2', 'smalldatetime', 'date'):
                if col_srv in df_insert.columns:
                    mask = df_insert[col_srv].notna()
                    if mask.any():
                        years = df_insert.loc[mask, col_srv].dt.year
                        invalid = (years < 1753) | (years > 9999)
                        df_insert.loc[mask & invalid, col_srv] = None

        # ---------- Inserción directa con pyodbc ----------
        # Construir INSERT SQL
        columnas_sql = ", ".join([f"[{col}]" for col in columnas_insert])
        placeholders = ", ".join(["?" for _ in columnas_insert])
        sql = f"INSERT INTO [{tabla_destino}] ({columnas_sql}) VALUES ({placeholders})"

        # Convertir DataFrame a lista de tuplas, manejando NaT/NaN como None
        datos = []
        for _, row in df_insert.iterrows():
            tupla = []
            for col in columnas_insert:
                val = row[col]
                if pd.isna(val):
                    tupla.append(None)
                elif isinstance(val, pd.Timestamp):
                    tupla.append(val.to_pydatetime())
                elif isinstance(val, pd.Int64Dtype) or isinstance(val, np.int64):
                    tupla.append(int(val))
                else:
                    tupla.append(val)
            datos.append(tuple(tupla))

        # Ejecutar inserción
        cursor.executemany(sql, datos)
        conn.commit()

        # Contar después de insertar
        cursor.execute(f"SELECT COUNT(*) FROM [{tabla_destino}]")
        registros_despues = cursor.fetchone()[0]

        insertados = registros_despues - registros_antes
        exito = insertados == registros_archivo

        conn.close()

        # Construir HTML final
        html = f"<div class='log-line {'success' if exito else 'warning'}'>"
        html += (
            f"{'✅' if exito else '⚠️'} Carga de {tipo.capitalize()} completada.</div>"
        )
        html += f"<p style='font-size:0.8rem;'><b>Servidor:</b> {cfg['server']} / {cfg['database']}</p>"
        html += (
            f"<p style='font-size:0.8rem;'><b>Tabla destino:</b> {tabla_destino}</p>"
        )
        html += f"<p style='font-size:0.8rem;'><b>Archivo:</b> {nombre_archivo}<br><b>Ruta:</b> {ruta_archivo}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros en archivo:</b> {registros_archivo}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros antes:</b> {registros_antes}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Registros después:</b> {registros_despues}</p>"
        html += f"<p style='font-size:0.8rem;'><b>Insertados:</b> {insertados} {'(coincide)' if exito else '(diferencia con archivo: ' + str(registros_archivo - insertados) + ')'}</p>"
        html += html_verif

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        import traceback

        error_completo = traceback.format_exc()
        print(error_completo)
        html = f"<div class='log-line error'>❌ Error en la carga: {str(e)}</div>"

    return html


@main_bp.route("/accion/probar-conexion-activa")
def accion_probar_conexion_activa():
    conexion = request.args.get("conexion", "local")
    from app.config import SQL_LOCAL, SQL_REMOTO

    cfg = SQL_REMOTO if conexion == "remoto" else SQL_LOCAL
    import pyodbc

    try:
        if cfg["auth"] == "windows":
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']},{cfg['port']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg['username']};"
                f"PWD={cfg['password']};"
            )
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return "<span class='badge-conexion badge-verde'>✅ Conectado</span>"
    except Exception as e:
        return "<span class='badge-conexion badge-rojo'>❌ Desconectado</span>"


@main_bp.route("/test-insert")
def test_insert():
    import pyodbc
    from app.config import SQL_LOCAL

    cfg = SQL_LOCAL  # o SQL_REMOTO si prefieres
    try:
        if cfg["auth"] == "windows":
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={cfg['server']},{cfg['port']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg['username']};"
                f"PWD={cfg['password']};"
            )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Intentar insertar una fila de prueba en Causales (ajusta las columnas obligatorias)
        sql = """
            INSERT INTO [dbo].[Causales] (FechayHora, Campana, Usuario)
            VALUES (?, ?, ?)
        """
        cursor.execute(sql, "2026-05-14 10:00:00", "Test Campaña", "Test Usuario")
        conn.commit()
        conn.close()
        return "<div class='log-line success'>✅ Inserción de prueba exitosa</div>"
    except Exception as e:
        return f"<div class='log-line error'>❌ Error: {str(e)}</div>"
