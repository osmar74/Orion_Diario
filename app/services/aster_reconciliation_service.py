"""
Servicio de conciliación ASTER.

Responsabilidad:
- Normalizar entidades del Excel ASTER.
- Normalizar entidades SQL clasificadas.
- Comparar Excel vs SQL.
- Aplicar entidades SQL no tomadas en cuenta.
- Devolver resultado estructurado para el controlador/render HTML.
"""

from __future__ import annotations

from typing import Any


def normalizar_entidades_excel_aster(
    entidades: list[str] | Any,
) -> list[str]:
    """
    Normaliza entidades del Excel ASTER desde sesión.
    """
    if not isinstance(entidades, list):
        return []

    return sorted(
        {
            str(entidad).strip()
            for entidad in entidades
            if str(entidad).strip()
        }
    )


def _normalizar_fila_entidad_sql(fila: dict[str, Any]) -> dict[str, Any] | None:
    """
    Normaliza una fila de entidad SQL ASTER.
    """
    entidad = str(fila.get("entidad") or "").strip()

    if not entidad:
        return None

    try:
        numero = int(fila.get("numero") or 0)
    except Exception:
        numero = 0

    return {
        "entidad": entidad,
        "numero": numero,
        "SSS": str(fila.get("SSS") or f"'{entidad}'"),
    }


def obtener_entidades_sql_validables_aster(
    cobranza: list[dict[str, Any]] | Any,
    integral: list[dict[str, Any]] | Any,
    no_seleccionadas: list[dict[str, Any]] | Any,
) -> list[dict[str, Any]]:
    """
    Obtiene entidades SQL disponibles para conciliación.

    Se toman:
    - Bases Cobranza %
    - Bases Integral
    - No seleccionadas

    No se toman las removidas.
    """
    combinadas = []

    if isinstance(cobranza, list):
        combinadas.extend(cobranza)

    if isinstance(integral, list):
        combinadas.extend(integral)

    if isinstance(no_seleccionadas, list):
        combinadas.extend(no_seleccionadas)

    entidades: dict[str, dict[str, Any]] = {}

    for fila in combinadas:
        if not isinstance(fila, dict):
            continue

        normalizada = _normalizar_fila_entidad_sql(fila)

        if not normalizada:
            continue

        entidades[normalizada["entidad"]] = normalizada

    return [
        entidades[entidad]
        for entidad in sorted(entidades.keys())
    ]


def conciliar_entidades_aster(
    entidades_excel: list[str] | Any,
    entidades_sql: list[dict[str, Any]] | Any,
    entidades_no_tomar: set[str] | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """
    Compara entidades Excel vs SQL ASTER.

    Retorna:
    - match_ok
    - faltan_en_sql
    - sobran_en_sql
    - comparacion
    - entidades_sql_ajustadas
    """
    excel_normalizadas = normalizar_entidades_excel_aster(entidades_excel)

    if not isinstance(entidades_sql, list):
        entidades_sql = []

    no_tomar = {
        str(entidad).strip()
        for entidad in (entidades_no_tomar or set())
        if str(entidad).strip()
    }

    entidades_sql_normalizadas: list[dict[str, Any]] = []

    for fila in entidades_sql:
        if not isinstance(fila, dict):
            continue

        normalizada = _normalizar_fila_entidad_sql(fila)

        if not normalizada:
            continue

        entidades_sql_normalizadas.append(normalizada)

    entidades_sql_ajustadas = [
        fila
        for fila in entidades_sql_normalizadas
        if str(fila.get("entidad") or "").strip() not in no_tomar
    ]

    set_excel = set(excel_normalizadas)
    set_sql = {
        str(fila.get("entidad") or "").strip()
        for fila in entidades_sql_ajustadas
        if str(fila.get("entidad") or "").strip()
    }

    faltan_en_sql = sorted(set_excel - set_sql)
    sobran_en_sql = sorted(set_sql - set_excel)

    match_ok = (
        not faltan_en_sql
        and not sobran_en_sql
        and len(set_excel) == len(set_sql)
    )

    todas = sorted(set_excel | set_sql)

    comparacion = []

    for entidad in todas:
        en_excel = entidad in set_excel
        en_sql = entidad in set_sql

        if en_excel and en_sql:
            estado = "MATCH"
        elif en_excel and not en_sql:
            estado = "FALTA_EN_SQL"
        else:
            estado = "SOBRA_EN_SQL"

        comparacion.append(
            {
                "entidad": entidad,
                "en_excel": en_excel,
                "en_sql": en_sql,
                "estado": estado,
            }
        )

    sql_por_entidad = {
        str(fila.get("entidad") or "").strip(): fila
        for fila in entidades_sql_normalizadas
        if str(fila.get("entidad") or "").strip()
    }

    sobrantes_detalle = [
        sql_por_entidad.get(
            entidad,
            {
                "entidad": entidad,
                "numero": 0,
                "SSS": f"'{entidad}'",
            },
        )
        for entidad in sobran_en_sql
    ]

    return {
        "success": True,
        "entidades_excel": excel_normalizadas,
        "entidades_sql": entidades_sql_normalizadas,
        "entidades_sql_ajustadas": entidades_sql_ajustadas,
        "entidades_no_tomar": sorted(no_tomar),
        "comparacion": comparacion,
        "faltan_en_sql": faltan_en_sql,
        "sobran_en_sql": sobran_en_sql,
        "sobrantes_detalle": sobrantes_detalle,
        "total_excel": len(set_excel),
        "total_sql": len(set_sql),
        "total_no_tomar": len(no_tomar),
        "match_ok": match_ok,
    }

