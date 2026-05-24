"""
Servicio de depuración y clasificación de entidades ASTER.

Responsabilidad:
- Normalizar resultados SQL ASTER guardados en sesión.
- Aplicar exclusiones de entidades que no corresponden.
- Clasificar entidades como Cobranza %, Integral o No seleccionadas.
- Devolver datos estructurados al controlador.
"""

from __future__ import annotations

from typing import Any


def normalizar_resultados_sql_aster(
    resultados: list[dict[str, Any]] | Any,
) -> list[dict[str, Any]]:
    """
    Normaliza resultados SQL ASTER.

    Entrada esperada:
    [
        {"entidad": "...", "numero": 123, "SSS": "'...'"},
        ...
    ]
    """
    if not isinstance(resultados, list):
        return []

    normalizados: list[dict[str, Any]] = []

    for fila in resultados:
        if not isinstance(fila, dict):
            continue

        entidad = str(fila.get("entidad") or "").strip()

        if not entidad:
            continue

        try:
            numero = int(fila.get("numero") or 0)
        except Exception:
            numero = 0

        sss = str(fila.get("SSS") or f"'{entidad}'").strip()

        normalizados.append(
            {
                "entidad": entidad,
                "numero": numero,
                "SSS": sss,
            }
        )

    return normalizados


def preparar_depuracion_aster(
    resultados_sql: list[dict[str, Any]] | Any,
) -> dict[str, Any]:
    """
    Prepara resultados SQL ASTER para la pantalla de depuración.
    """
    resultados = normalizar_resultados_sql_aster(resultados_sql)

    if not resultados:
        return {
            "success": False,
            "error": "No hay resultados SQL ASTER en sesión. Ejecute primero la Fase E.",
            "resultados": [],
        }

    return {
        "success": True,
        "resultados": resultados,
        "total_entidades": len(resultados),
        "total_registros": sum(int(fila.get("numero") or 0) for fila in resultados),
    }


def aplicar_exclusiones_aster(
    resultados_sql: list[dict[str, Any]] | Any,
    entidades_excluir: set[str] | list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """
    Aplica exclusiones seleccionadas por el usuario.

    Retorna:
    - removidos
    - filtrados
    """
    resultados = normalizar_resultados_sql_aster(resultados_sql)

    if not resultados:
        return {
            "success": False,
            "error": "No hay resultados SQL ASTER en sesión. Ejecute primero la Fase E.",
            "removidos": [],
            "filtrados": [],
        }

    excluir = {
        str(entidad).strip()
        for entidad in entidades_excluir
        if str(entidad).strip()
    }

    removidos = [
        fila
        for fila in resultados
        if str(fila.get("entidad") or "").strip() in excluir
    ]

    filtrados = [
        fila
        for fila in resultados
        if str(fila.get("entidad") or "").strip() not in excluir
    ]

    return {
        "success": True,
        "removidos": removidos,
        "filtrados": filtrados,
        "total_removidos": len(removidos),
        "total_filtrados": len(filtrados),
    }


def guardar_clasificacion_aster(
    clasificaciones: list[dict[str, Any]] | Any,
    removidos: list[dict[str, Any]] | Any,
) -> dict[str, Any]:
    """
    Separa entidades clasificadas en:
    - cobranza
    - integral
    - no_seleccionados
    """
    if not isinstance(clasificaciones, list):
        return {
            "success": False,
            "error": "Formato inválido de clasificación ASTER.",
        }

    removidos_normalizados = normalizar_resultados_sql_aster(removidos)

    cobranza: list[dict[str, Any]] = []
    integral: list[dict[str, Any]] = []
    no_seleccionados: list[dict[str, Any]] = []

    for item in clasificaciones:
        if not isinstance(item, dict):
            continue

        entidad = str(item.get("entidad") or "").strip()

        if not entidad:
            continue

        try:
            numero = int(item.get("numero") or 0)
        except Exception:
            numero = 0

        sss = str(item.get("SSS") or f"'{entidad}'").strip()
        clasificacion = str(item.get("clasificacion") or "").strip().lower()

        fila = {
            "entidad": entidad,
            "numero": numero,
            "SSS": sss,
        }

        if clasificacion == "cobranza":
            cobranza.append(fila)
        elif clasificacion == "integral":
            integral.append(fila)
        else:
            no_seleccionados.append(fila)

    return {
        "success": True,
        "removidos": removidos_normalizados,
        "cobranza": cobranza,
        "integral": integral,
        "no_seleccionados": no_seleccionados,
        "total_removidos": len(removidos_normalizados),
        "total_cobranza": len(cobranza),
        "total_integral": len(integral),
        "total_no_seleccionados": len(no_seleccionados),
    }

