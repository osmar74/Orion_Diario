# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
from pathlib import Path
from time import perf_counter
from typing import Any

from app.services.integral_v2_common_service import construir_contexto_integral_v2, fecha_tokens, original_dir, ruta_busqueda, step, enumerate_steps, now_ms

VALID_EXT = {".xlsx", ".xlsm", ".csv", ".txt"}


def _buscar_archivos(base: Path, tokens: dict[str, str]) -> list[Path]:
    if not base.exists():
        return []
    needles = {tokens["yyyymmdd"].lower(), tokens["ddmmyyyy"].lower(), tokens["dd-mm-yyyy"].lower(), tokens["yyyy-mm-dd"].lower()}
    found: list[Path] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in VALID_EXT:
            if any(token in path.name.lower() for token in needles):
                found.append(path)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def gestionar_archivo_integral_v2(form) -> dict[str, Any]:
    total_t0 = perf_counter()
    inicio_total = now_ms()
    tiempos: list[dict[str, Any]] = []
    advertencias: list[str] = []
    contexto = construir_contexto_integral_v2(form)
    fecha = fecha_tokens(contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
    conexion = contexto.get("conexion") or form.get("conexion") or "local"
    base = ruta_busqueda(conexion)
    destino_dir = original_dir(fecha["yyyymmdd"])
    archivos: list[Path] = []
    archivo_copiado: Path | None = None

    def paso_buscar():
        nonlocal archivos
        archivos = _buscar_archivos(base, fecha)
        if not base.exists():
            return "Sin conexión", f"Ruta de búsqueda sin conexión o no disponible: {base}"
        return len(archivos), "Búsqueda finalizada."

    fila, warn = step("INT-ARC-BUS", "Buscar archivos", str(base), paso_buscar)
    tiempos.append(fila)
    if warn:
        advertencias.append(warn)

    raw_selected = str(form.get("archivo_candidato") or form.get("archivo") or form.get("archivo_seleccionado") or "").strip()
    selected_path = Path(raw_selected) if raw_selected else None
    if selected_path and selected_path.exists():
        archivos = [selected_path] + [p for p in archivos if p != selected_path]
    if len(archivos) > 1 and not raw_selected:
        advertencias.append(f"Se encontraron {len(archivos)} archivos. Se copiará automáticamente el más reciente; revise si corresponde.")

    def paso_copiar():
        nonlocal archivo_copiado
        if not archivos:
            raise FileNotFoundError("No se encontró archivo para la fecha de proceso.")
        source = archivos[0]
        destino = destino_dir / source.name
        if source.resolve() != destino.resolve():
            shutil.copy2(source, destino)
        archivo_copiado = destino
        return destino.name, f"Archivo copiado a {destino}"

    fila, warn = step("INT-ARC-COP", "Copiar archivo seleccionado", str(destino_dir), paso_copiar)
    tiempos.append(fila)
    if warn:
        advertencias.append(warn)

    fin_total = now_ms()
    total_seg = round(perf_counter() - total_t0, 2)
    estado = "Correcto" if archivo_copiado else "Revisar"
    mensaje = "Archivo gestionado." if archivo_copiado else "No se pudo gestionar el archivo."
    tiempos.append({"#": None, "Código": "INT-ARC-TOTAL", "Paso": "Total fase C", "Estado": estado, "Inicio": inicio_total, "Fin": fin_total, "Seg.": f"{total_seg:.2f}", "Entrada": fecha["yyyymmdd"], "Salida": str(archivo_copiado or "-"), "Mensaje": mensaje})

    candidatos = []
    for p in archivos[:10]:
        candidatos.append({"nombre": p.name, "ruta": str(p), "tamano_kb": round(p.stat().st_size / 1024, 2) if p.exists() else 0, "seleccionado": bool(archivo_copiado and p.name == archivo_copiado.name)})

    return {"codigo": "C", "titulo": "Gestionar archivo", "estado": estado, "mensaje": mensaje, "inicio": inicio_total, "fin": fin_total, "duracion_segundos": total_seg, "tiempos": enumerate_steps(tiempos), "advertencias": advertencias, "archivo": str(archivo_copiado or ""), "archivo_nombre": archivo_copiado.name if archivo_copiado else "", "candidatos": candidatos, "detalle": {"conexion": str(conexion).upper(), "ruta_busqueda": str(base), "carpeta_destino": str(destino_dir), "fecha_proceso": fecha["yyyymmdd"], "archivo_copiado": str(archivo_copiado or ""), "cantidad_archivos": len(archivos)}}
