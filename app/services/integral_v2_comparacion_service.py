# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from time import perf_counter
from typing import Any
from app.services.integral_v2_common_service import construir_contexto_integral_v2, fecha_tokens, fetch_sql_entities, resolve_file_from_form, count_file_entities, compare_entities, step, enumerate_steps, now_ms


def comparar_entidades_integral_v2(form) -> dict[str, Any]:
    total_t0 = perf_counter()
    inicio_total = now_ms()
    tiempos: list[dict[str, Any]] = []
    advertencias: list[str] = []
    contexto = construir_contexto_integral_v2(form)
    fecha = fecha_tokens(contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
    conexion = contexto.get("conexion") or form.get("conexion") or "local"
    sql_data: list[dict[str, Any]] = []
    file_data: list[dict[str, Any]] = []
    comparison: list[dict[str, Any]] = []
    file_path: Path | None = None
    total_file_rows = 0
    entity_col = "-"

    def paso_sql():
        nonlocal sql_data
        sql_data = fetch_sql_entities(conexion, fecha["sql"])
        return len(sql_data), "Entidades SQL consultadas."

    fila, warn = step("INT-CMP-SQL", "Consulta SQL entidades", fecha["sql"], paso_sql)
    tiempos.append(fila)
    if warn:
        advertencias.append(warn)

    def paso_archivo_resolver():
        nonlocal file_path
        file_path = resolve_file_from_form(form, fecha["yyyymmdd"])
        return file_path.name, str(file_path)

    fila, warn = step("INT-CMP-FILE", "Localizar archivo copiado", fecha["yyyymmdd"], paso_archivo_resolver)
    tiempos.append(fila)
    if warn:
        advertencias.append(warn)

    if not advertencias:
        def paso_archivo_leer():
            nonlocal file_data, total_file_rows, entity_col
            assert file_path is not None
            file_data, total_file_rows, entity_col = count_file_entities(file_path)
            return total_file_rows, f"Columna Entidad: {entity_col}. Entidades archivo: {len(file_data)}"
        fila, warn = step("INT-CMP-READ", "Leer archivo y agrupar entidades", str(file_path), paso_archivo_leer)
        tiempos.append(fila)
        if warn:
            advertencias.append(warn)

    if not advertencias:
        def paso_comparar():
            nonlocal comparison
            comparison = compare_entities(sql_data, file_data)
            return len(comparison), "Comparación SQL vs archivo finalizada."
        fila, warn = step("INT-CMP-DIFF", "Ordenar y comparar", f"SQL {len(sql_data)} / Archivo {len(file_data)}", paso_comparar)
        tiempos.append(fila)
        if warn:
            advertencias.append(warn)

    selected_count = sum(1 for x in comparison if x.get("seleccionar"))
    diff_count = sum(1 for x in comparison if x.get("estado") != "OK")
    fin_total = now_ms()
    total_seg = round(perf_counter() - total_t0, 2)
    estado = "Revisar"
    if advertencias:
        mensaje = "Comparación finalizada con observaciones."
    elif selected_count > 0:
        mensaje = "Comparación lista. Seleccione/aplique entidades para continuar."
    else:
        mensaje = "No hay entidades OK seleccionables; revise diferencias."
    tiempos.append({"#": None, "Código": "INT-CMP-TOTAL", "Paso": "Total fase D", "Estado": estado, "Inicio": inicio_total, "Fin": fin_total, "Seg.": f"{total_seg:.2f}", "Entrada": f"SQL {len(sql_data)} / Archivo {len(file_data)}", "Salida": f"Seleccionables {selected_count} / Diferencias {diff_count}", "Mensaje": mensaje})
    return {"codigo": "D", "titulo": "Obtener y comparar entidades", "estado": estado, "mensaje": mensaje, "inicio": inicio_total, "fin": fin_total, "duracion_segundos": total_seg, "tiempos": enumerate_steps(tiempos), "advertencias": advertencias, "comparacion": comparison, "fecha_sql": fecha["sql"], "archivo": str(file_path or ""), "resumen": {"entidades_sql": len(sql_data), "entidades_archivo": len(file_data), "registros_archivo": total_file_rows, "diferencias": diff_count, "seleccionables": selected_count, "archivo": str(file_path.name if file_path else "-"), "columna_entidad": entity_col}}
