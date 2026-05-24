"""
Blueprint para las fases A-B y D:
- Crear estructura diaria
- Verificar red y carpetas
- Distribuir archivos
"""

import os

from flask import Blueprint, request, session

from app.config import DATA_DIR
from app.services.file_manager import FileManager
from app.controllers.helpers import obtener_log_service
from app.services.daily_paths import ruta_orion
from app.services.orion_fases_renderer import (
    render_crear_estructura_orion,
    render_distribucion_seleccionados_orion,
    render_log_error,
    render_preparar_distribucion_orion,
    render_verificar_red_orion,
)


fases_ab_bp = Blueprint("fases_ab", __name__)

def _normalizar_fecha_orion(fecha_raw: str) -> str:
    """
    Normaliza fecha ORION a formato YYYYMM_DD.

    Acepta:
    - 202604_29
    - 20260429
    - 2026-04-29
    """
    fecha = str(fecha_raw or "").strip()

    if "_" in fecha and len(fecha.replace("_", "")) == 8:
        return fecha

    digitos = "".join(ch for ch in fecha if ch.isdigit())

    if len(digitos) == 8:
        return f"{digitos[:6]}_{digitos[6:8]}"

    return fecha

@fases_ab_bp.route("/accion/crear-carpetas")
def accion_crear_carpetas():
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_12"))

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    resultado = fm.crear_estructura_diaria(fecha)

    return render_crear_estructura_orion(
        fecha=fecha,
        data_dir=DATA_DIR,
        resultado=resultado,
    )

@fases_ab_bp.route("/accion/verificar-red")
def accion_verificar_red():
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_06"))

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    resultado = fm.verificar_red_y_carpetas(fecha)

    if resultado.get("success"):
        session["red_base_activa"] = resultado.get("red_base_usada")

    return render_verificar_red_orion(resultado)



@fases_ab_bp.route("/accion/distribuir")
def accion_distribuir():
    """
    Fase D - Preparar distribución.

    Ya no copia inmediatamente.
    Primero muestra los archivos encontrados para que el usuario seleccione cuáles copiar.
    """
    fecha = _normalizar_fecha_orion(request.args.get("fecha", "202605_12"))

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    red_base = session.get("red_base_activa")

    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)

    if not res_verif["success"]:
        return render_log_error(f"No se puede copiar: {res_verif['error']}")
    
    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    os.makedirs(carpeta_diaria, exist_ok=True)

    session["orion_distribucion_fecha"] = fecha

    return render_preparar_distribucion_orion(
        fecha=fecha,
        rutas_validadas=res_verif["rutas_validadas"],
        archivos_encontrados=res_verif["archivos_encontrados"],
        carpeta_diaria=carpeta_diaria,
    )
    
@fases_ab_bp.route("/accion/distribuir-seleccionados", methods=["POST"])
def accion_distribuir_seleccionados():
    """
    Copia solo los archivos seleccionados por el usuario en Fase D.
    """
    data = request.get_json(silent=True) or {}

    fecha = _normalizar_fecha_orion(
        data.get("fecha") or session.get("orion_distribucion_fecha") or "202605_12"
    )

    seleccionados = data.get("seleccionados", [])

    if not seleccionados:
        return "<div class='log-line error'>❌ No seleccionó archivos para copiar.</div>"

    fm = FileManager(DATA_DIR, log_service=obtener_log_service())
    red_base = session.get("red_base_activa")

    if not red_base:
        return "<div class='log-line error'>❌ Primero debe verificar la red correctamente.</div>"

    res_verif = fm.verificar_red_y_carpetas(fecha, red_base_path=red_base)

    if not res_verif["success"]:
        return render_log_error(
            f"No se puede preparar distribución: {res_verif['error']}"
                )

    categorias_validas = {"Causales", "Lotes", "Discador"}

    archivos_filtrados = {
        "Causales": [],
        "Lotes": [],
        "Discador": [],
    }

    archivos_disponibles = res_verif.get("archivos_encontrados", {})

    for item in seleccionados:
        categoria = str(item.get("categoria", "")).strip()
        archivo = str(item.get("archivo", "")).strip()

        if categoria not in categorias_validas or not archivo:
            continue

        disponibles_categoria = archivos_disponibles.get(categoria, []) or []

        if archivo not in disponibles_categoria:
            continue

        archivos_filtrados[categoria].append(archivo)

    if not any(archivos_filtrados.values()):
        return """
        <div class='log-line error'>
            ❌ Ninguno de los archivos seleccionados está disponible en la ruta origen.
        </div>
        """

    carpeta_diaria = ruta_orion(DATA_DIR, fecha)
    os.makedirs(carpeta_diaria, exist_ok=True)

    res_dist = fm.distribuir_archivos(
        res_verif["rutas_validadas"],
        carpeta_diaria,
        archivos_filtrados,
    )

    return render_distribucion_seleccionados_orion(res_dist)

