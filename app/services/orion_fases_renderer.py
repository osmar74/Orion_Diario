"""
Renderers HTML para fases iniciales ORION.

Responsabilidad:
- Generar HTML para crear estructura diaria.
- Verificar red y carpetas.
- Preparar distribución de archivos.
- Mostrar resultado de distribución.
"""

from __future__ import annotations

import os
from html import escape
from typing import Any


def render_log_error(mensaje: str) -> str:
    return f"<div class='log-line error'>❌ {escape(str(mensaje))}</div>"


def render_crear_estructura_orion(
    fecha: str,
    data_dir: str,
    resultado: dict[str, Any],
) -> str:
    """
    Renderiza resultado de creación de estructura diaria ORION.
    """
    if not resultado.get("success"):
        return render_log_error(resultado.get("error", "Error creando estructura diaria."))

    html = f"<div class='log-line success'>✅ Estructura creada para {escape(str(fecha))}</div>"

    html += f"""
    <div class='log-line info'>
        📌 DATA_DIR activo: {escape(str(data_dir))}
    </div>
    """

    html += "<table class='dataframe'><tr><th>Carpeta</th><th>Ruta</th></tr>"

    rutas = resultado.get("rutas", {})

    for nombre in ["principal", "Reporte_Imagen", "Causales", "Lotes", "Discador"]:
        if nombre in rutas:
            ruta = rutas[nombre]
            html += f"""
            <tr>
                <td>{escape(str(nombre))}</td>
                <td style='font-size:0.75rem;'>{escape(str(ruta))}</td>
            </tr>
            """

    html += "</table>"

    return html


def render_verificar_red_orion(
    resultado: dict[str, Any],
) -> str:
    """
    Renderiza resultado de verificación de red ORION.
    """
    if not resultado.get("success"):
        red_probada = resultado.get("red_base_usada", "No disponible")

        return f"""
        <div class='log-line error'>
            ❌ {escape(str(resultado.get("error", "Error desconocido")))}
        </div>
        <p style='font-size:0.7rem;'>
            Ruta probada: {escape(str(red_probada))}
        </p>
        """

    red_usada = resultado.get("red_base_usada", "No especificada")
    rutas = resultado.get("rutas_validadas", {})
    archivos_encontrados = resultado.get("archivos_encontrados", {})

    html = "<div class='log-line success'>✅ Red verificada correctamente</div>"
    html += f"""
    <p style='margin:5px 0; font-size:0.8rem;'>
        📍 <b>Unidad de red:</b> {escape(str(red_usada))}
    </p>
    """

    if "anio" in rutas:
        html += f"""
        <p style='font-size:0.7rem; color:#ccc;'>
            📂 Año: {escape(str(rutas["anio"]))}
        </p>
        """

    if "mes" in rutas:
        html += f"""
        <p style='font-size:0.7rem; color:#ccc;'>
            📅 Mes: {escape(str(rutas["mes"]))}
        </p>
        """

    html += """
    <table class='dataframe' style='width:100%;'>
        <tr>
            <th>Subcarpeta</th>
            <th>Ruta</th>
            <th>Archivos encontrados</th>
        </tr>
    """

    for sub, ruta_sub in rutas.items():
        if sub not in ["Causales", "Discador", "Lotes"]:
            continue

        archivos = archivos_encontrados.get(sub, [])

        if archivos:
            archivos_txt = ", ".join(str(archivo) for archivo in archivos)

            html += f"""
            <tr>
                <td>{escape(str(sub))}</td>
                <td style='font-size:0.6rem;'>{escape(str(ruta_sub))}</td>
                <td>{escape(archivos_txt)}</td>
            </tr>
            """
        else:
            html += f"""
            <tr>
                <td>{escape(str(sub))}</td>
                <td style='font-size:0.6rem;'>{escape(str(ruta_sub))}</td>
                <td style='color:#ffc107;'>Ninguno</td>
            </tr>
            """

    html += "</table>"

    for msg in resultado.get("mensajes", []):
        msg_txt = str(msg)

        if "Advertencia" in msg_txt or "anterior" in msg_txt:
            html += f"<p style='color:#ffc107; font-size:0.7rem;'>{escape(msg_txt)}</p>"
        else:
            html += f"<p style='font-size:0.7rem; color:#aaa;'>{escape(msg_txt)}</p>"

    return html


def _destino_categoria_orion(carpeta_diaria: str, categoria: str) -> str:
    """
    Devuelve carpeta destino por categoría ORION.
    """
    destinos = {
        "Causales": os.path.join(carpeta_diaria, "Causales"),
        "Lotes": os.path.join(carpeta_diaria, "Lotes"),
        "Discador": os.path.join(carpeta_diaria, "Discador"),
    }

    return destinos.get(categoria, carpeta_diaria)


def render_preparar_distribucion_orion(
    fecha: str,
    rutas_validadas: dict[str, Any],
    archivos_encontrados: dict[str, Any],
    carpeta_diaria: str,
) -> str:
    """
    Muestra archivos encontrados para que el usuario seleccione cuáles copiar.
    """
    html = f"""
    <div class='log-line success'>
        ✅ Archivos ubicados correctamente para {escape(str(fecha))}.
    </div>
    <div class='log-line info'>
        Seleccione qué archivos desea copiar hacia la carpeta diaria ORION.
    </div>
    <div class='log-line info'>
        📁 Carpeta diaria destino: <code>{escape(str(carpeta_diaria))}</code>
    </div>
    """

    categorias = ["Causales", "Lotes", "Discador"]
    total_archivos = 0

    for categoria in categorias:
        ruta_origen = rutas_validadas.get(categoria, "")
        archivos = archivos_encontrados.get(categoria, []) or []
        destino_dir = _destino_categoria_orion(carpeta_diaria, categoria)

        html += f"""
        <details class='panel-monitor' open style='margin-top:10px;'>
            <summary>
                <span class='panel-icon'>📁</span>
                {escape(str(categoria))} - {len(archivos)} archivo(s)
            </summary>
            <div class='panel-body'>
                <div class='log-line info'>
                    <b>Ruta origen:</b> <code>{escape(str(ruta_origen))}</code>
                </div>
                <div class='log-line info'>
                    <b>Ruta destino:</b> <code>{escape(str(destino_dir))}</code>
                </div>
        """

        if not archivos:
            html += """
                <div class='log-line warning'>
                    ⚠️ No se encontraron archivos para esta categoría.
                </div>
            </div>
        </details>
            """
            continue

        html += """
                <table class='dataframe' style='width:100%; margin-top:8px;'>
                    <tr>
                        <th>Copiar</th>
                        <th>Archivo</th>
                        <th>Ruta origen</th>
                        <th>Ruta destino</th>
                        <th>Estado destino</th>
                    </tr>
        """

        for archivo in archivos:
            total_archivos += 1

            ruta_destino = os.path.join(destino_dir, str(archivo))
            existe_destino = os.path.isfile(ruta_destino)

            if existe_destino:
                estado_destino = "⚠️ Ya existe, se reemplazará"
                color_estado = "#ffc107"
            else:
                estado_destino = "✅ Nuevo"
                color_estado = "#28a745"

            html += f"""
                    <tr>
                        <td style='text-align:center;'>
                            <input
                                type='checkbox'
                                class='chk-distribucion-orion'
                                checked
                                data-categoria='{escape(str(categoria), quote=True)}'
                                data-archivo='{escape(str(archivo), quote=True)}'
                            >
                        </td>
                        <td><b>{escape(str(archivo))}</b></td>
                        <td style='font-size:0.7rem; word-break:break-all;'>
                            {escape(str(ruta_origen))}
                        </td>
                        <td style='font-size:0.7rem; word-break:break-all;'>
                            {escape(str(ruta_destino))}
                        </td>
                        <td style='font-weight:bold; color:{color_estado};'>
                            {estado_destino}
                        </td>
                    </tr>
            """

        html += """
                </table>
            </div>
        </details>
        """

    if total_archivos == 0:
        html += """
        <div class='log-line error'>
            ❌ No hay archivos disponibles para copiar.
        </div>
        """
    else:
        html += """
        <div style='margin-top:12px;'>
            <button type='button' onclick='copiarDistribucionSeleccionada(this)'>
                Copiar seleccionados
            </button>
        </div>
        <div class='log-line warning' style='margin-top:8px;'>
            ⚠️ No se copiará nada hasta presionar <b>Copiar seleccionados</b>.
        </div>
        """

    return html


def render_distribucion_seleccionados_orion(
    resultado: dict[str, Any],
) -> str:
    """
    Renderiza resultado de copiar archivos seleccionados.
    """
    if resultado.get("success"):
        html = "<div class='log-line success'>✅ Archivos seleccionados copiados correctamente.</div>"
    else:
        html = "<div class='log-line warning'>⚠️ Distribución parcial o con errores.</div>"

    html += """
    <table class='dataframe' style='width:100%; margin-top:10px;'>
        <tr>
            <th>Categoría</th>
            <th>Archivo</th>
            <th>Destino</th>
        </tr>
    """

    for item in resultado.get("copiados_detalle", []):
        html += f"""
        <tr>
            <td>{escape(str(item.get("categoria", "")))}</td>
            <td><b>{escape(str(item.get("archivo", "")))}</b></td>
            <td style='font-size:0.7rem; word-break:break-all;'>
                {escape(str(item.get("destino", "")))}
            </td>
        </tr>
        """

    html += "</table>"

    if resultado.get("errores"):
        html += "<ul style='color:#ffc107; font-size:0.75rem;'>"

        for error in resultado["errores"]:
            html += f"<li>{escape(str(error))}</li>"

        html += "</ul>"

    return html