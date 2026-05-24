"""
Renderers HTML para Gestión Diaria ASTER.

Responsabilidad:
- Generar HTML de respuesta para fases ASTER.
- Mantener aster_blueprint.py más limpio.
- No ejecutar lógica de negocio.
"""

from __future__ import annotations

from html import escape
from typing import Any


def render_total_aster(
    total: int | None,
    origen: str,
    previews: list[tuple[str, str]],
) -> str:
    """
    Genera respuesta HTML para mostrar el total ASTER detectado o ingresado.
    """
    html = "<div class='ocr-result-container'>"

    html += "<div class='ocr-images'>"

    if previews:
        for nombre, img_b64 in previews:
            html += (
                "<div class='ocr-thumb'>"
                f"<img src='data:image/png;base64,{img_b64}' alt='{escape(str(nombre), quote=True)}'/>"
                f"<small>{escape(str(nombre))}</small>"
                "</div>"
            )
    else:
        html += "<p style='color:#888;'>Sin vista previa de imagen.</p>"

    html += "</div>"

    html += "<div class='ocr-results'>"

    if total is not None:
        html += "<div class='log-line success'>✅ Total ASTER capturado correctamente.</div>"
        html += "<div class='totales-grid' style='margin-top:10px;'>"
        html += (
            "<div class='total-card'>"
            "<span class='label'>🔹 Total ASTER</span>"
            f"<span class='value'>{escape(str(total))}</span>"
            "</div>"
        )
        html += "</div>"
        html += (
            "<table class='dataframe' style='width:100%; margin-top:10px;'>"
            "<tr><th colspan='2' style='background:#1e3a5f; color:#fff;'>Detalle de captura</th></tr>"
            f"<tr><td><b>Origen</b></td><td>{escape(str(origen))}</td></tr>"
            f"<tr><td><b>Total general</b></td><td>{escape(str(total))}</td></tr>"
            "</table>"
        )
    else:
        html += (
            "<div class='log-line warning'>"
            "⚠️ No se pudo detectar automáticamente el total ASTER. "
            "Ingrese el total manualmente."
            "</div>"
        )

    html += "</div>"
    html += "</div>"

    html += (
        "<div id='aster-total-data' style='display:none;' "
        f"data-total='{escape(str(total if total is not None else ''), quote=True)}'>"
        "</div>"
    )

    return html


def render_archivo_aster(
    fecha_yyyymmdd: str,
    ruta_origen: str,
    ruta_destino: str,
    nombre_archivo: str,
) -> str:
    """
    Genera HTML de resultado para la copia del archivo ASTER.
    """
    html = "<div class='log-line success'>✅ Archivo ASTER localizado y copiado correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Información del archivo ASTER
            </th>
        </tr>
    """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Archivo encontrado", nombre_archivo),
        ("Ruta origen", ruta_origen),
        ("Ruta destino", ruta_destino),
    ]

    for etiqueta, valor in filas:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-archivo-data' style='display:none;' "
        f"data-fecha='{escape(str(fecha_yyyymmdd), quote=True)}' "
        f"data-ruta='{escape(str(ruta_destino), quote=True)}' "
        f"data-archivo='{escape(str(nombre_archivo), quote=True)}'>"
        "</div>"
    )

    return html


def render_normalizacion_aster(
    ruta_archivo: str,
    columnas_originales: list[Any],
    columnas_normalizadas: list[str],
) -> str:
    """
    Genera HTML con tabla comparativa de encabezados originales y normalizados.
    """
    html = "<div class='log-line success'>✅ Encabezados ASTER normalizados correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='3' style='background:#1e3a5f; color:#fff;'>
                Comparación de encabezados ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Encabezado original</th>
            <th>Encabezado normalizado</th>
        </tr>
    """

    for idx, (original, normalizado) in enumerate(
        zip(columnas_originales, columnas_normalizadas),
        start=1,
    ):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(original))}</td>
            <td><b>{escape(str(normalizado))}</b></td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Archivo actualizado
            </th>
        </tr>
        <tr>
            <td><b>Ruta</b></td>
            <td style='font-size:0.75rem; word-break:break-all;'>{escape(str(ruta_archivo))}</td>
        </tr>
    </table>
    """

    return html


def render_entidades_excel_aster(
    ruta_archivo: str,
    total_registros: int,
    conteo_entidades: list[tuple[str, int]],
) -> str:
    """
    Genera HTML con entidades únicas del Excel ASTER.
    """
    total_entidades = len(conteo_entidades)
    total_registros_con_entidad = sum(cantidad for _, cantidad in conteo_entidades)
    total_registros_sin_entidad = total_registros - total_registros_con_entidad

    html = "<div class='log-line success'>✅ Entidades ASTER analizadas correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen de entidades del Excel ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Archivo analizado", ruta_archivo),
        ("Registros totales del Excel", total_registros),
        ("Registros con Entidad", total_registros_con_entidad),
        ("Registros sin Entidad", total_registros_sin_entidad),
        ("Entidades únicas encontradas", total_entidades),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Cantidad de registros</th>
        </tr>
    """

    for idx, (entidad, cantidad) in enumerate(conteo_entidades, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(entidad))}</b></td>
            <td style='font-weight:bold;'>{escape(str(cantidad))}</td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-entidades-excel-data' style='display:none;' "
        f"data-total-entidades='{escape(str(total_entidades), quote=True)}' "
        f"data-total-registros='{escape(str(total_registros), quote=True)}'>"
        "</div>"
    )

    return html


def render_consulta_sql_aster(
    fecha_sql: str,
    resultados: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de la consulta SQL ASTER.
    """
    total_entidades = len(resultados)
    total_registros = sum(int(fila["numero"]) for fila in resultados)

    if not resultados:
        return f"""
        <div class='log-line warning'>
            ⚠️ La consulta ASTER no devolvió resultados para la fecha {escape(str(fecha_sql))}.
        </div>
        """

    html = "<div class='log-line success'>✅ Consulta SQL ASTER ejecutada correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen consulta SQL ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Fecha consultada", fecha_sql),
        ("Entidades devueltas por SQL", total_entidades),
        ("Total registros SQL", total_registros),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.9rem; font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    for idx, fila in enumerate(resultados, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila["entidad"]))}</b></td>
            <td style='font-weight:bold;'>{escape(str(fila["numero"]))}</td>
            <td><code>{escape(str(fila["SSS"]))}</code></td>
        </tr>
        """

    html += "</table>"

    html += (
        "<div id='aster-sql-data' style='display:none;' "
        f"data-fecha='{escape(str(fecha_sql), quote=True)}' "
        f"data-total-entidades='{escape(str(total_entidades), quote=True)}' "
        f"data-total-registros='{escape(str(total_registros), quote=True)}'>"
        "</div>"
    )

    return html

def render_tabla_entidades_aster(
    titulo: str,
    filas: list[dict[str, Any]],
) -> str:
    """
    Genera tabla simple de entidades ASTER.
    """
    html = f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='4' style='background:#1e3a5f; color:#fff;'>
                {escape(str(titulo))} ({len(filas)})
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    if not filas:
        html += """
        <tr>
            <td colspan='4' style='text-align:center; color:#888;'>
                Sin registros.
            </td>
        </tr>
        """

    for idx, fila in enumerate(filas, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{escape(str(numero))}</td>
            <td><code>{escape(sss)}</code></td>
        </tr>
        """

    html += "</table>"

    return html


def render_preparar_depuracion_aster(
    resultados: list[dict[str, Any]],
) -> str:
    """
    Genera primera tabla para seleccionar registros que no corresponden a cobranzas %.
    """
    total_entidades = len(resultados)
    total_registros = sum(int(fila.get("numero") or 0) for fila in resultados)

    html = """
    <div class='log-line info'>
        Seleccione las entidades que NO corresponden a cobranzas %. Luego presione Aplicar exclusiones.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                Depuración inicial ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Entidades SQL disponibles", total_entidades),
        ("Total registros SQL", total_registros),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td colspan='2'><b>{escape(str(etiqueta))}</b></td>
            <td colspan='3' style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += """
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>Excluir</th>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
        </tr>
    """

    for idx, fila in enumerate(resultados, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        entidad_value = escape(entidad, quote=True)

        html += f"""
        <tr>
            <td style='text-align:center;'>
                <input
                    type='checkbox'
                    class='aster-excluir-checkbox'
                    value="{entidad_value}"
                >
            </td>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{escape(str(numero))}</td>
            <td><code>{escape(sss)}</code></td>
        </tr>
        """

    html += "</table>"

    html += """
    <div style='margin-top:10px;'>
        <button type='button' onclick='aplicarExclusionesAster(this)'>
            Aplicar exclusiones ASTER
        </button>
    </div>
    """

    return html


def render_exclusiones_aplicadas_aster(
    removidos: list[dict[str, Any]],
    filtrados: list[dict[str, Any]],
) -> str:
    """
    Muestra removidos y tabla filtrada para clasificar Cobranza % / Integral.
    """
    html = "<div class='log-line success'>✅ Exclusiones ASTER aplicadas correctamente.</div>"

    html += render_tabla_entidades_aster(
        "Registros removidos por no corresponder a cobranzas %",
        removidos,
    )

    html += """
    <div class='log-line info' style='margin-top:10px;'>
        Clasifique las entidades restantes como Cobranza % o Integral. Las que deje sin seleccionar quedarán como no seleccionadas.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                Clasificación de entidades ASTER filtradas
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>Número</th>
            <th>SSS</th>
            <th>Clasificación</th>
        </tr>
    """

    if not filtrados:
        html += """
        <tr>
            <td colspan='5' style='text-align:center; color:#888;'>
                Sin entidades disponibles para clasificar.
            </td>
        </tr>
        """

    for idx, fila in enumerate(filtrados, start=1):
        entidad = str(fila.get("entidad") or "")
        numero = int(fila.get("numero") or 0)
        sss = str(fila.get("SSS") or f"'{entidad}'")

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td style='font-weight:bold;'>{escape(str(numero))}</td>
            <td><code>{escape(sss)}</code></td>
            <td>
                <select
                    class='aster-clasificacion-select'
                    data-entidad="{escape(entidad, quote=True)}"
                    data-numero="{escape(str(numero), quote=True)}"
                    data-sss="{escape(sss, quote=True)}"
                    style='padding:4px 8px; background:#222; color:#fff; border:1px solid #444; border-radius:4px;'
                >
                    <option value=''>No seleccionado</option>
                    <option value='cobranza'>Cobranza %</option>
                    <option value='integral'>Integral</option>
                </select>
            </td>
        </tr>
        """

    html += "</table>"

    html += """
    <div style='margin-top:10px;'>
        <button type='button' onclick='guardarClasificacionAster(this)'>
            Guardar clasificación ASTER
        </button>
    </div>
    """

    return html


def render_clasificacion_final_aster(
    removidos: list[dict[str, Any]],
    cobranza: list[dict[str, Any]],
    integral: list[dict[str, Any]],
    no_seleccionados: list[dict[str, Any]],
) -> str:
    """
    Muestra resultado final de la depuración y clasificación ASTER.
    """
    total_validado = len(cobranza) + len(integral) + len(no_seleccionados)

    html = "<div class='log-line success'>✅ Clasificación ASTER guardada correctamente.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen clasificación ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Registros removidos", len(removidos)),
        ("Bases Cobranza %", len(cobranza)),
        ("Bases Integral", len(integral)),
        ("No seleccionadas", len(no_seleccionados)),
        ("Entidades revisadas después de exclusiones", total_validado),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += render_tabla_entidades_aster("Registros removidos", removidos)
    html += render_tabla_entidades_aster("Seleccionadas como Cobranza %", cobranza)
    html += render_tabla_entidades_aster("Seleccionadas como Integral", integral)
    html += render_tabla_entidades_aster("No seleccionadas", no_seleccionados)

    html += (
        "<div id='aster-clasificacion-data' style='display:none;' "
        f"data-removidos='{escape(str(len(removidos)), quote=True)}' "
        f"data-cobranza='{escape(str(len(cobranza)), quote=True)}' "
        f"data-integral='{escape(str(len(integral)), quote=True)}' "
        f"data-no-seleccionados='{escape(str(len(no_seleccionados)), quote=True)}'>"
        "</div>"
    )

    return html


def render_tabla_comparativa_aster(
    comparacion: list[dict[str, Any]],
    titulo: str = "Comparación Excel vs SQL ASTER",
) -> str:
    """
    Genera tabla comparativa Excel vs SQL desde resultado estructurado.
    """
    html = f"""
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='5' style='background:#1e3a5f; color:#fff;'>
                {escape(str(titulo))}
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Entidad</th>
            <th>En Excel</th>
            <th>En SQL</th>
            <th>Estado</th>
        </tr>
    """

    if not comparacion:
        html += """
        <tr>
            <td colspan='5' style='text-align:center; color:#888;'>
                Sin entidades para comparar.
            </td>
        </tr>
        """

    for idx, fila in enumerate(comparacion, start=1):
        entidad = str(fila.get("entidad") or "")
        en_excel = bool(fila.get("en_excel"))
        en_sql = bool(fila.get("en_sql"))
        estado_raw = str(fila.get("estado") or "")

        if estado_raw == "MATCH":
            estado = "✅ Match"
            color = "#28a745"
        elif estado_raw == "FALTA_EN_SQL":
            estado = "⚠️ Está en Excel, falta en SQL"
            color = "#ffc107"
        else:
            estado = "⚠️ Está en SQL, falta en Excel"
            color = "#dc3545"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(entidad)}</b></td>
            <td>{'Sí' if en_excel else 'No'}</td>
            <td>{'Sí' if en_sql else 'No'}</td>
            <td style='font-weight:bold; color:{color};'>{estado}</td>
        </tr>
        """

    html += "</table>"

    return html


def render_conciliacion_aster(
    resultado: dict[str, Any],
) -> str:
    """
    Genera HTML de conciliación ASTER desde resultado estructurado.
    """
    faltan_en_sql = resultado.get("faltan_en_sql", [])
    sobran_en_sql = resultado.get("sobran_en_sql", [])
    entidades_no_tomar = set(resultado.get("entidades_no_tomar", []))
    comparacion = resultado.get("comparacion", [])
    match_ok = bool(resultado.get("match_ok"))

    html = """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen conciliación ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Entidades únicas en Excel", resultado.get("total_excel", 0)),
        ("Entidades SQL consideradas", resultado.get("total_sql", 0)),
        ("Entidades no tomadas en cuenta", resultado.get("total_no_tomar", 0)),
        ("Entidades en Excel que faltan en SQL", len(faltan_en_sql)),
        ("Entidades en SQL que faltan en Excel", len(sobran_en_sql)),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-weight:bold;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += render_tabla_comparativa_aster(
        comparacion=comparacion,
        titulo="Comparación Excel vs SQL ASTER",
    )

    if match_ok:
        html = "<div class='log-line success'>✅ Información Verificada.</div>" + html
        html += """
        <div id='aster-conciliacion-data' style='display:none;' data-validado='1'></div>
        """
        return html

    html = """
    <div class='log-line warning'>
        ⚠️ La conciliación ASTER tiene diferencias. Revise las entidades antes de continuar.
    </div>
    """ + html

    if faltan_en_sql:
        html += """
        <div class='log-line warning' style='margin-top:10px;'>
            ⚠️ Hay entidades en el Excel que no aparecen en la consulta SQL ASTER.
            Esto puede indicar que falta completar información en ASTER o revisar la fecha consultada.
        </div>
        """

        html += render_tabla_entidades_aster(
            "Entidades en Excel que faltan en SQL",
            [
                {
                    "entidad": entidad,
                    "numero": 0,
                    "SSS": f"'{entidad}'",
                }
                for entidad in faltan_en_sql
            ],
        )

    if sobran_en_sql:
        html += """
        <div class='log-line warning' style='margin-top:10px;'>
            ⚠️ Hay entidades en SQL que no aparecen en el Excel. Seleccione cuáles no se tomarán en cuenta y vuelva a validar.
        </div>
        """

        html += """
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr>
                <th colspan='4' style='background:#1e3a5f; color:#fff;'>
                    Entidades SQL sobrantes
                </th>
            </tr>
            <tr style='background:#1e3a5f; color:#fff;'>
                <th>No tomar en cuenta</th>
                <th>#</th>
                <th>Entidad</th>
                <th>SSS</th>
            </tr>
        """

        for idx, fila in enumerate(resultado.get("sobrantes_detalle", []), start=1):
            entidad = str(fila.get("entidad") or "")
            sss = str(fila.get("SSS") or f"'{entidad}'")
            checked = "checked" if entidad in entidades_no_tomar else ""

            html += f"""
            <tr>
                <td style='text-align:center;'>
                    <input
                        type='checkbox'
                        class='aster-no-tomar-checkbox'
                        value="{escape(entidad, quote=True)}"
                        {checked}
                    >
                </td>
                <td>{idx}</td>
                <td><b>{escape(entidad)}</b></td>
                <td><code>{escape(sss)}</code></td>
            </tr>
            """

        html += "</table>"

        html += """
        <div style='margin-top:10px;'>
            <button type='button' onclick='ajustarConciliacionAster(this)'>
                Aplicar entidades no tomadas en cuenta
            </button>
        </div>
        """

    html += """
    <div id='aster-conciliacion-data' style='display:none;' data-validado='0'></div>
    """

    return html

def render_preparacion_insercion_aster(
    conexion: str,
    tabla_destino: str,
    ruta_archivo: str,
    total_registros: int,
    comparacion: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de comparación previa a inserción ASTER.
    """
    conexion_normalizada = (conexion or "local").strip().lower()
    es_remoto = conexion_normalizada == "remoto"

    html = ""

    if es_remoto:
        html += """
        <div class='log-line warning'>
            ⚠️ Atención: seleccionó conexión REMOTA. Esta conexión es producción.
            No se debe usar para pruebas.
        </div>
        """
    else:
        html += """
        <div class='log-line success'>
            ✅ Conexión LOCAL seleccionada para pruebas.
        </div>
        """

    total_ok = sum(1 for fila in comparacion if fila["estado"] == "OK")
    total_no_sql = sum(1 for fila in comparacion if fila["estado"] == "NO_EXISTE_EN_SQL")
    total_no_excel = sum(1 for fila in comparacion if fila["estado"] == "NO_EXISTE_EN_EXCEL")

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen preparación inserción ASTER
            </th>
        </tr>
    """

    filas_resumen = [
        ("Conexión seleccionada", conexion_normalizada.upper()),
        ("Tabla destino", tabla_destino),
        ("Archivo Excel", ruta_archivo),
        ("Registros en Excel", total_registros),
        ("Columnas coincidentes", total_ok),
        ("Columnas Excel sin campo SQL", total_no_sql),
        ("Campos SQL sin columna Excel", total_no_excel),
    ]

    for etiqueta, valor in filas_resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.8rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Columna Excel</th>
            <th>Tipo Excel</th>
            <th>Campo SQL</th>
            <th>Tipo SQL</th>
            <th>Nullable</th>
            <th>Longitud</th>
            <th>Estado</th>
        </tr>
    """

    for idx, fila in enumerate(comparacion, start=1):
        estado = str(fila["estado"])

        if estado == "OK":
            color = "#28a745"
            texto_estado = "✅ OK"
        elif estado == "NO_EXISTE_EN_SQL":
            color = "#dc3545"
            texto_estado = "❌ No existe en SQL"
        else:
            color = "#ffc107"
            texto_estado = "⚠️ No existe en Excel"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td><b>{escape(str(fila["columna_excel"]))}</b></td>
            <td>{escape(str(fila["tipo_excel"]))}</td>
            <td><b>{escape(str(fila["columna_sql"]))}</b></td>
            <td>{escape(str(fila["tipo_sql"]))}</td>
            <td>{escape(str(fila["nullable"]))}</td>
            <td>{escape(str(fila["longitud"]))}</td>
            <td style='font-weight:bold; color:{color};'>{texto_estado}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <div id='aster-preparacion-insercion-data' style='display:none;' data-preparado='1'></div>
    """

    return html


def render_duplicados_aster(
    total_duplicados: int,
    columnas_clave: list[str],
    ejemplos: list[dict[str, Any]],
) -> str:
    """
    Genera HTML de bloqueo por duplicados.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Inserción ASTER bloqueada. Se detectaron {total_duplicados} registros posiblemente duplicados.
    </div>
    <div class='log-line warning'>
        No se insertó ningún registro. Revise los datos o limpie la carga previa si corresponde.
    </div>
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Validación anti-duplicados ASTER
            </th>
        </tr>
        <tr>
            <td><b>Columnas usadas como clave</b></td>
            <td>{escape(", ".join(columnas_clave))}</td>
        </tr>
        <tr>
            <td><b>Duplicados detectados</b></td>
            <td>{escape(str(total_duplicados))}</td>
        </tr>
    </table>
    """

    if ejemplos:
        html += """
        <table class='dataframe' style='width:100%; margin-top:10px;'>
            <tr style='background:#1e3a5f; color:#fff;'>
                <th>#</th>
        """

        for columna in columnas_clave:
            html += f"<th>{escape(str(columna))}</th>"

        html += "</tr>"

        for idx, ejemplo in enumerate(ejemplos, start=1):
            html += f"<tr><td>{idx}</td>"

            for columna in columnas_clave:
                html += f"<td>{escape(str(ejemplo.get(columna, '')))}</td>"

            html += "</tr>"

        html += "</table>"

    return html


def render_errores_validacion_insert_aster(
    errores: list[dict[str, Any]],
) -> str:
    """
    Genera HTML con errores de validación previa.
    """
    html = f"""
    <div class='log-line error'>
        ❌ Preparación de inserción ASTER bloqueada. Se detectaron {len(errores)} errores de datos.
    </div>
    <div class='log-line warning'>
        No se debe insertar hasta corregir estos valores o ajustar los tipos/longitudes de la tabla SQL.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Fila Excel</th>
            <th>Columna</th>
            <th>Tipo SQL</th>
            <th>Valor</th>
            <th>Problema</th>
        </tr>
    """

    for idx, error in enumerate(errores, start=1):
        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(error.get("fila", "")))}</td>
            <td><b>{escape(str(error.get("columna", "")))}</b></td>
            <td>{escape(str(error.get("tipo_sql", "")))}</td>
            <td style='word-break:break-all;'>{escape(str(error.get("valor", "")))}</td>
            <td style='color:#dc3545; font-weight:bold;'>{escape(str(error.get("problema", "")))}</td>
        </tr>
        """

    html += "</table>"

    html += """
    <div id='aster-preparacion-insercion-data' style='display:none;' data-preparado='0'></div>
    """

    return html


def render_historial_cargas_aster(
    registros: list[dict[str, Any]],
    ruta_db: str,
) -> str:
    """
    Genera HTML del historial de cargas ASTER.
    """
    html = """
    <div class='log-line info'>
        📜 Historial local de cargas ASTER.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='12' style='background:#1e3a5f; color:#fff;'>
                Últimas cargas ASTER
            </th>
        </tr>
        <tr style='background:#1e3a5f; color:#fff;'>
            <th>#</th>
            <th>Fecha registro</th>
            <th>Fecha proceso</th>
            <th>Conexión</th>
            <th>Total ASTER</th>
            <th>Filas Excel</th>
            <th>Insertados</th>
            <th>Estado</th>
            <th>Archivo Excel</th>
            <th>Reporte entidades</th>
            <th>Ruta reporte</th>
            <th>Mensaje</th>
        </tr>
    """

    if not registros:
        html += """
        <tr>
            <td colspan='12' style='text-align:center; color:#888;'>
                Todavía no hay cargas ASTER registradas.
            </td>
        </tr>
        """

    for idx, registro in enumerate(registros, start=1):
        estado = str(registro.get("estado") or "")

        if estado == "CORRECTO":
            color = "#28a745"
        elif estado in {"FALLÓ_CUADRE", "ERROR_DATOS"}:
            color = "#dc3545"
        else:
            color = "#ffc107"

        html += f"""
        <tr>
            <td>{idx}</td>
            <td>{escape(str(registro.get("fecha_hora_registro") or ""))}</td>
            <td>{escape(str(registro.get("fecha_proceso") or ""))}</td>
            <td>{escape(str(registro.get("conexion") or ""))}</td>
            <td>{escape(str(registro.get("total_general_aster") or ""))}</td>
            <td>{escape(str(registro.get("filas_excel") or ""))}</td>
            <td>{escape(str(registro.get("registros_insertados") or ""))}</td>
            <td style='font-weight:bold; color:{color};'>{escape(estado)}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("archivo_excel") or ""))}</td>
            <td>{escape(str(registro.get("archivo_reporte_entidades") or ""))}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("ruta_reporte_entidades") or ""))}</td>
            <td style='word-break:break-all;'>{escape(str(registro.get("mensaje") or ""))}</td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <div class='log-line info' style='margin-top:10px;'>
        Base local historial: <code>{escape(str(ruta_db))}</code>
    </div>
    """

    return html


def render_reporte_final_aster(
    fecha_yyyymmdd: str,
    detalle_cuadre: dict[str, Any],
    ruta_entidades: str,
    nombre_entidades: str,
    total_entidades: int,
) -> str:
    """
    Genera reporte visual final de Fase H ASTER.
    """
    cumple = bool(detalle_cuadre.get("cumple"))

    if cumple:
        html = """
        <div class='log-line success'>
            ✅ Proceso ASTER correcto. La cantidad insertada coincide con el Excel y con el Total general ASTER.
        </div>
        """
    else:
        html = """
        <div class='log-line error'>
            ❌ Proceso ASTER falló. La cantidad insertada no coincide con el Excel o con el Total general ASTER.
        </div>
        """

    filas = [
        ("Fecha proceso", fecha_yyyymmdd),
        ("Filas del archivo Excel", detalle_cuadre.get("filas_excel")),
        ("Registros insertados", detalle_cuadre.get("registros_insertados")),
        ("Total general ASTER", detalle_cuadre.get("total_general_aster")),
        ("Resultado de comparación", "CORRECTO" if cumple else "FALLÓ"),
        ("Archivo de entidades creado", nombre_entidades),
        ("Ruta archivo entidades", ruta_entidades),
        ("Entidades filtradas exportadas", total_entidades),
    ]

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Reporte final Fase H ASTER
            </th>
        </tr>
    """

    for etiqueta, valor in filas:
        color = ""

        if etiqueta == "Resultado de comparación":
            color = "color:#28a745;" if cumple else "color:#dc3545;"

        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.85rem; word-break:break-all; font-weight:bold; {color}'>
                {escape(str(valor))}
            </td>
        </tr>
        """

    html += "</table>"

    return html


def render_insert_ok_aster(
    fecha_yyyymmdd: str,
    conexion: str,
    tabla_destino: str,
    ruta_archivo: str,
    total_leidos: int,
    total_insertados: int,
    columnas_insertadas: list[str],
    columnas_clave: list[str],
    detalle_cuadre: dict[str, Any],
    ruta_entidades: str,
    nombre_entidades: str,
    total_entidades: int,
) -> str:
    """
    Genera HTML de inserción exitosa ASTER con validación final.
    """
    conexion_txt = "REMOTO - PRODUCCIÓN" if conexion == "remoto" else "LOCAL - PRUEBAS"

    html = """
    <div class='log-line success'>
        ✅ Inserción ASTER completada correctamente.
    </div>
    """

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th colspan='2' style='background:#1e3a5f; color:#fff;'>
                Resumen inserción ASTER
            </th>
        </tr>
    """

    resumen = [
        ("Conexión usada", conexion_txt),
        ("Tabla destino", tabla_destino),
        ("Archivo", ruta_archivo),
        ("Registros leídos del Excel", total_leidos),
        ("Registros duplicados detectados", 0),
        ("Registros insertados", total_insertados),
        ("Columnas insertadas", ", ".join(columnas_insertadas)),
        ("Clave anti-duplicados", ", ".join(columnas_clave)),
    ]

    for etiqueta, valor in resumen:
        html += f"""
        <tr>
            <td><b>{escape(str(etiqueta))}</b></td>
            <td style='font-size:0.8rem; word-break:break-all;'>{escape(str(valor))}</td>
        </tr>
        """

    html += "</table>"

    html += render_reporte_final_aster(
        fecha_yyyymmdd=fecha_yyyymmdd,
        detalle_cuadre=detalle_cuadre,
        ruta_entidades=ruta_entidades,
        nombre_entidades=nombre_entidades,
        total_entidades=total_entidades,
    )

    return html

