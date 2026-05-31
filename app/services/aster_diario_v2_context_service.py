from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.orion_aster_config_service import (
    get_config,
    get_data_root,
    get_module_paths,
    get_sql_config_legacy,
    probar_configuracion,
)


ASTER_FASES_V2 = [
    {
        "id": "A",
        "titulo": "Captura del total diario ASTER",
        "accion": "aster.total.actual",
        "descripcion": "Obtiene el total diario ASTER para control inicial.",
        "grupo": "Total y archivo",
    },
    {
        "id": "B",
        "titulo": "Ubicación y copia del archivo ASTER",
        "accion": "aster.buscar.archivo",
        "descripcion": "Busca el archivo After en rutas configuradas y lo copia a DATA.",
        "grupo": "Total y archivo",
    },
    {
        "id": "C",
        "titulo": "Normalización del Excel ASTER",
        "accion": "aster.normalizar.encabezados",
        "descripcion": "Normaliza encabezados y estructura del archivo ASTER.",
        "grupo": "Total y archivo",
    },
    {
        "id": "D",
        "titulo": "Validación de entidades del Excel ASTER",
        "accion": "aster.entidades.excel",
        "descripcion": "Extrae y valida entidades detectadas en el archivo.",
        "grupo": "Entidades y conciliación",
    },
    {
        "id": "E",
        "titulo": "Conexión y consulta SQL ASTER",
        "accion": "aster.consulta.sql",
        "descripcion": "Consulta datos en origen ASTER según conexión activa.",
        "grupo": "Entidades y conciliación",
    },
    {
        "id": "F",
        "titulo": "Depuración y clasificación ASTER",
        "accion": "aster.depuracion",
        "descripcion": "Prepara exclusiones, clasificaciones y ajustes previos.",
        "grupo": "Entidades y conciliación",
    },
    {
        "id": "G",
        "titulo": "Conciliación y validación ASTER",
        "accion": "aster.conciliacion",
        "descripcion": "Concilia entidades y valida consistencia previa a inserción.",
        "grupo": "Entidades y conciliación",
    },
    {
        "id": "H",
        "titulo": "Inserción de datos ASTER",
        "accion": "aster.insertar.datos",
        "descripcion": "Inserta datos normalizados en la base Aster_Api.",
        "grupo": "Inserción y gestiones",
    },
    {
        "id": "I",
        "titulo": "Traer usuarios y gestiones ASTER",
        "accion": "aster.fase.i",
        "descripcion": "Replica usuarios y comentarios desde origen hacia Aster_Api.",
        "grupo": "Inserción y gestiones",
    },
]


def _fecha_sql(fecha_proceso: str) -> str:
    raw = str(fecha_proceso or "").strip()

    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw

    return datetime.now().strftime("%Y-%m-%d")


def _fecha_yyyymmdd(fecha_proceso: str) -> str:
    return _fecha_sql(fecha_proceso).replace("-", "")


def _sql_publico(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "server": cfg.get("server", ""),
        "database": cfg.get("database", ""),
        "auth": cfg.get("auth", "sql"),
        "username": cfg.get("username") or cfg.get("user") or "",
        "conexion": cfg.get("conexion", ""),
    }


def construir_contexto_aster_v2(
    fecha_proceso: str,
    conexion: str = "local",
) -> dict[str, Any]:
    conexion = "remoto" if str(conexion).lower() == "remoto" else "local"
    fecha_sql = _fecha_sql(fecha_proceso)
    fecha = _fecha_yyyymmdd(fecha_proceso)

    config = get_config()
    data_root = get_data_root()

    rutas_aster = get_module_paths("aster", conexion)
    rutas_orion = get_module_paths("orion", conexion)

    sql_origen = (
        get_sql_config_legacy(conexion, "gestioncomercial")
        if conexion == "local"
        else get_sql_config_legacy(conexion, "aster_api")
    )

    sql_destino = get_sql_config_legacy(conexion, "aster_api")
    sql_consolidado = get_sql_config_legacy(conexion, "gestion_consolidada")

    data_fecha = str((__import__("pathlib").Path(data_root) / fecha))
    data_aster = str((__import__("pathlib").Path(data_root) / fecha / "Aster"))

    fases = []

    for fase in ASTER_FASES_V2:
        item = dict(fase)
        item["estado"] = "pendiente"
        item["http"] = None
        fases.append(item)

    return {
        "ok": True,
        "titulo": "Gestión Diaria ASTER v2",
        "fecha_proceso": fecha,
        "fecha_sql": fecha_sql,
        "conexion": conexion,
        "data": {
            "root": data_root,
            "fecha": data_fecha,
            "aster": data_aster,
        },
        "rutas": {
            "aster": rutas_aster,
            "orion": rutas_orion,
            "aster_total": len(rutas_aster),
            "orion_total": len(rutas_orion),
        },
        "sql": {
            "origen": _sql_publico(sql_origen),
            "destino_aster_api": _sql_publico(sql_destino),
            "gestion_consolidada": _sql_publico(sql_consolidado),
        },
        "config": {
            "ambiente_activo": config.get("ambiente_activo", "local"),
            "data_root": data_root,
        },
        "fases": fases,
    }


def probar_configuracion_aster_v2(conexion: str = "local") -> dict[str, Any]:
    conexion = "remoto" if str(conexion).lower() == "remoto" else "local"
    prueba = probar_configuracion(conexion)

    # Reducimos la respuesta al contexto ASTER para la vista.
    return {
        "ok": True,
        "conexion": conexion,
        "data_root": prueba.get("data_root", {}),
        "rutas": {
            "aster": prueba.get("rutas", {}).get("aster", []),
        },
        "sql": {
            "origen_local_gestioncomercial": (
                get_sql_config_legacy("local", "gestioncomercial")
                if conexion == "local"
                else {}
            ),
            "aster_api": prueba.get("sql", {}).get("aster_api", {}),
            "gestion_consolidada": prueba.get("sql", {}).get("gestion_consolidada", {}),
        },
    }
