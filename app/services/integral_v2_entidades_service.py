# -*- coding: utf-8 -*-
from __future__ import annotations
from time import perf_counter
from typing import Any
from app.services.integral_v2_common_service import construir_contexto_integral_v2, fecha_tokens, fetch_sql_entities, step, enumerate_steps, now_ms


def obtener_entidades_integral_v2(form) -> dict[str, Any]:
    total_t0 = perf_counter()
    inicio_total = now_ms()
    tiempos: list[dict[str, Any]] = []
    advertencias: list[str] = []
    contexto = construir_contexto_integral_v2(form)
    fecha = fecha_tokens(contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
    conexion = contexto.get("conexion") or form.get("conexion") or "local"
    entidades: list[dict[str, Any]] = []

    def paso_sql():
        nonlocal entidades
        entidades = fetch_sql_entities(conexion, fecha["sql"])
        return len(entidades), "Entidades SQL obtenidas."

    fila, warn = step("INT-ENT-SQL", "Consultar entidades SQL", fecha["sql"], paso_sql)
    tiempos.append(fila)
    if warn:
        advertencias.append(warn)
    fin_total = now_ms()
    total_seg = round(perf_counter() - total_t0, 2)
    estado = "Correcto" if not advertencias else "Revisar"
    tiempos.append({"#": None, "Código": "INT-ENT-TOTAL", "Paso": "Total entidades", "Estado": estado, "Inicio": inicio_total, "Fin": fin_total, "Seg.": f"{total_seg:.2f}", "Entrada": fecha["sql"], "Salida": len(entidades), "Mensaje": "Consulta de entidades finalizada."})
    return {"ok": estado == "Correcto", "codigo": "D", "titulo": "Obtener entidades", "estado": estado, "mensaje": "Entidades obtenidas." if entidades else "No se encontraron entidades.", "inicio": inicio_total, "fin": fin_total, "duracion_segundos": total_seg, "tiempos": enumerate_steps(tiempos), "advertencias": advertencias, "entidades": entidades, "detalle": {"conexion": str(conexion).upper(), "fecha_sql": fecha["sql"], "cantidad": len(entidades)}}
