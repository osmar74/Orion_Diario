# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import Any


def _to_int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", "").strip()))
    except Exception:
        return 0


def aplicar_entidades_comparadas_integral_v2(form) -> dict[str, Any]:
    raw = form.get("entidades_json") or "[]"
    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []
    entidades = []
    total_sql = 0
    total_archivo = 0
    total_diferencia = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        entidad = str(item.get("entidad") or "").strip()
        if not entidad:
            continue
        reg_sql = _to_int(item.get("reg_sql"))
        reg_archivo = _to_int(item.get("reg_archivo"))
        diferencia = _to_int(item.get("diferencia"))
        entidades.append({"entidad": entidad, "reg_sql": reg_sql, "reg_archivo": reg_archivo, "diferencia": diferencia})
        total_sql += reg_sql
        total_archivo += reg_archivo
        total_diferencia += diferencia
    entidades.sort(key=lambda x: x["entidad"].lower())
    return {"estado": "Correcto" if entidades else "Revisar", "entidades": entidades, "totales": {"reg_sql": total_sql, "reg_archivo": total_archivo, "diferencia": total_diferencia}, "entidades_csv": ",".join(x["entidad"] for x in entidades)}
