from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
INSTANCE_DIR = ROOT / "instance"
CONFIG_PATH = INSTANCE_DIR / "orion_aster_config.json"


def _default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "ambiente_activo": "local",
        "data_root": str(ROOT / "data"),
        "rutas": {
            "local": {
                "orion": [
                    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_orion\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion"
                ],
                "aster": [
                    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_aster\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO"
                ],
            },
            "remoto": {
                "orion": [
                    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
                    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
                ],
                "aster": [
                    r"\\10.24.90.118\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
                    r"Z:\COBRANZA %\2024\0. Avance Masivo y Llamadas Efectivas\2024\MAYO\AFTER_MAYO_CONSOLIDADO",
                ],
            },
        },
        "sql": {
            "local": {
                "orion": {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "Orion",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },
                "aster_api": {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "Aster_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },
                "gestioncomercial": {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "gestioncomercial_dev",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },
                "gestion_consolidada": {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "Vencorp_V2",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },
                "integral_api": {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },
            },
            "remoto": {
                "orion": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Orion",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },
                "aster_api": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Aster_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },
                "gestion_consolidada": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Vencorp_V2",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },
                "integral_api": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },
            },
        },
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)

    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def ensure_config_file() -> Path:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(_default_config(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return CONFIG_PATH


def get_config() -> dict[str, Any]:
    ensure_config_file()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    return _deep_merge(_default_config(), data)


def save_config(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_config()
    updated = _deep_merge(current, payload or {})

    # Normalización mínima.
    updated["ambiente_activo"] = normalizar_conexion(updated.get("ambiente_activo", "local"))

    data_root = str(updated.get("data_root") or "").strip()
    if not data_root:
        data_root = str(ROOT / "data")

    updated["data_root"] = data_root

    Path(data_root).mkdir(parents=True, exist_ok=True)

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(updated, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return updated


def normalizar_conexion(conexion: str | None) -> str:
    value = str(conexion or "").strip().lower()

    if value == "remoto":
        return "remoto"

    return "local"


def get_data_root() -> str:
    data = get_config()
    root = str(data.get("data_root") or ROOT / "data").strip()
    Path(root).mkdir(parents=True, exist_ok=True)
    return root


def get_module_paths(modulo: str, conexion: str | None = None) -> list[str]:
    data = get_config()
    conexion_norm = normalizar_conexion(conexion or data.get("ambiente_activo"))

    modulo_norm = str(modulo or "").strip().lower()

    rutas = (
        data.get("rutas", {})
        .get(conexion_norm, {})
        .get(modulo_norm, [])
    )

    if isinstance(rutas, str):
        rutas = [rutas]

    return [str(r).strip() for r in rutas if str(r).strip()]


def get_sql_config(conexion: str | None = None, modulo: str = "orion") -> dict[str, Any]:
    data = get_config()
    conexion_norm = normalizar_conexion(conexion or data.get("ambiente_activo"))
    modulo_norm = str(modulo or "orion").strip().lower()

    cfg = (
        data.get("sql", {})
        .get(conexion_norm, {})
        .get(modulo_norm, {})
    )

    fallback = (
        _default_config()
        .get("sql", {})
        .get(conexion_norm, {})
        .get(modulo_norm, {})
    )

    result = _deep_merge(fallback, cfg if isinstance(cfg, dict) else {})
    result["conexion"] = conexion_norm

    return result


def get_sql_config_legacy(conexion: str | None = None, modulo: str = "orion") -> dict[str, Any]:
    cfg = get_sql_config(conexion, modulo)

    return {
        "conexion": cfg.get("conexion", normalizar_conexion(conexion)),
        "server": cfg.get("server", ""),
        "alt_server": cfg.get("alt_server", ""),
        "port": cfg.get("port", ""),
        "alt_port": cfg.get("alt_port", ""),
        "database": cfg.get("database", ""),
        "auth": cfg.get("auth", "sql"),
        "username": cfg.get("username", cfg.get("user", "")),
        "user": cfg.get("username", cfg.get("user", "")),
        "password": cfg.get("password", ""),
        "driver": cfg.get("driver", "ODBC Driver 18 for SQL Server"),
        "encrypt": cfg.get("encrypt", "yes"),
        "trust": cfg.get("trust", cfg.get("trust_server_certificate", "yes")),
        "trust_server_certificate": cfg.get("trust_server_certificate", cfg.get("trust", "yes")),
    }


def probar_ruta(path: str) -> dict[str, Any]:
    raw = str(path or "").strip()

    if not raw:
        return {
            "path": raw,
            "ok": False,
            "estado": "vacía",
            "detalle": "Ruta vacía",
        }

    p = Path(raw)

    try:
        exists = p.exists()
        is_dir = p.is_dir() if exists else False

        return {
            "path": raw,
            "ok": bool(exists and is_dir),
            "estado": "ok" if exists and is_dir else "no_existe",
            "detalle": "Accesible" if exists and is_dir else "No existe o no es carpeta",
        }
    except Exception as exc:
        return {
            "path": raw,
            "ok": False,
            "estado": "error",
            "detalle": str(exc),
        }


def probar_sql(conexion: str, modulo: str) -> dict[str, Any]:
    cfg = get_sql_config_legacy(conexion, modulo)

    try:
        from app.services.orion_connection_service import probar_conexion_sql_server

        res = probar_conexion_sql_server(cfg)

        return {
            "conexion": normalizar_conexion(conexion),
            "modulo": modulo,
            "server": cfg.get("server", ""),
            "database": cfg.get("database", ""),
            "ok": bool(res.get("success")),
            "estado": "ok" if res.get("success") else "error",
            "detalle": res.get("mensaje") or res.get("error") or "",
        }
    except Exception as exc:
        return {
            "conexion": normalizar_conexion(conexion),
            "modulo": modulo,
            "server": cfg.get("server", ""),
            "database": cfg.get("database", ""),
            "ok": False,
            "estado": "error",
            "detalle": str(exc),
        }


def probar_configuracion(conexion: str | None = None) -> dict[str, Any]:
    conexion_norm = normalizar_conexion(conexion)
    data_root = get_data_root()

    return {
        "conexion": conexion_norm,
        "data_root": probar_ruta(data_root),
        "rutas": {
            "orion": [probar_ruta(p) for p in get_module_paths("orion", conexion_norm)],
            "aster": [probar_ruta(p) for p in get_module_paths("aster", conexion_norm)],
        },
        "sql": {
            "orion": probar_sql(conexion_norm, "orion"),
            "aster_api": probar_sql(conexion_norm, "aster_api"),
            "gestion_consolidada": probar_sql(conexion_norm, "gestion_consolidada"),
        },
    }
