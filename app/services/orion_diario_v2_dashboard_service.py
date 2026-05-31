from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import os
import re

from app.services.orion_aster_config_service import get_data_root, get_module_paths, get_sql_config_legacy

try:
    import pyodbc
except Exception:
    pyodbc = None


ROOT = Path.cwd()


RED_BASE_PATHS = [
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_orion\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion"
            ]


MESES = {
    "01": "enero",
    "02": "febrero",
    "03": "marzo",
    "04": "abril",
    "05": "mayo",
    "06": "junio",
    "07": "julio",
    "08": "agosto",
    "09": "septiembre",
    "10": "octubre",
    "11": "noviembre",
    "12": "diciembre",
}


FASES_ORION = [
    {
        "codigo": "A",
        "nombre": "Crear carpetas",
        "grupo": "Preparación",
        "descripcion": "Crea estructura local y carpetas de proceso diario Orion.",
        "accion": "crear.carpetas",
    },
    {
        "codigo": "B",
        "nombre": "Verificar red",
        "grupo": "Preparación",
        "descripcion": "Verifica disponibilidad de rutas de red, unidad Z y espejo local.",
        "accion": "verificar.red",
    },
    {
        "codigo": "C",
        "nombre": "OCR y Totales",
        "grupo": "OCR",
        "descripcion": "Procesa OCR, extrae totales y valida archivos base.",
        "accion": "ocr.procesar",
    },
    {
        "codigo": "D",
        "nombre": "Distribuir archivos",
        "grupo": "Distribución",
        "descripcion": "Distribuye archivos por carpetas de trabajo y tipo de insumo.",
        "accion": "distribuir.preparar",
    },
    {
        "codigo": "E1",
        "nombre": "Procesar Discador",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de discador para carga SQL.",
        "accion": "procesar.discador",
    },
    {
        "codigo": "E2",
        "nombre": "Procesar Causales",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de causales para carga SQL.",
        "accion": "procesar.causales",
    },
    {
        "codigo": "E3",
        "nombre": "Procesar Lotes",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de lotes para carga SQL.",
        "accion": "procesar.lotes",
    },
    {
        "codigo": "F1",
        "nombre": "Carga Causales",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta causales en base Orion.",
        "accion": "carga.causales.verificar",
    },
    {
        "codigo": "F2",
        "nombre": "Carga Lotes",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta lotes en base Orion.",
        "accion": "carga.lotes.verificar",
    },
    {
        "codigo": "F3",
        "nombre": "Carga Discador",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta discador en base Orion.",
        "accion": "carga.discador.verificar",
    },
    {
        "codigo": "G",
        "nombre": "Consolidado Gestión Orion",
        "grupo": "Consolidado",
        "descripcion": "Genera resumen final de Gestión Diaria Orion.",
        "accion": "consolidado.gestion.consultar",
    }
            ]


def _leer_env_local() -> None:
    env_path = ROOT / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')

        if key not in os.environ:
            os.environ[key] = value


def _fecha_yyyymmdd(fecha_proceso: str) -> str:
    fecha = str(fecha_proceso or "").strip()

    if re.fullmatch(r"\d{8}", fecha):
        return fecha

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        return fecha.replace("-", "")

    return datetime.now().strftime("%Y%m%d")


def _fecha_sql(fecha_proceso: str) -> str:
    fecha = _fecha_yyyymmdd(fecha_proceso)
    return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"


def _mes_por_fecha(fecha_proceso: str) -> str:
    fecha = _fecha_yyyymmdd(fecha_proceso)
    return MESES.get(fecha[4:6], "")


def _normalizar_mes(mes_gestion: str, fecha_proceso: str) -> str:
    mes = str(mes_gestion or "").strip().lower()

    if mes:
        return mes

    return _mes_por_fecha(fecha_proceso)


def _orion_config(conexion: str) -> dict[str, str]:
    cfg = get_sql_config_legacy(conexion, "orion")

    return {
        "conexion": cfg.get("conexion", str(conexion or "local").strip().lower()),
        "driver": cfg.get("driver", "ODBC Driver 18 for SQL Server"),
        "server": cfg.get("server", ""),
        "database": cfg.get("database", "Orion"),
        "username": cfg.get("username", cfg.get("user", "")),
        "password": cfg.get("password", ""),
        "encrypt": cfg.get("encrypt", "yes"),
        "trust": cfg.get("trust", cfg.get("trust_server_certificate", "yes")),
    }

def _conn_str(cfg: dict[str, str]) -> str:
    return (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"Encrypt={cfg['encrypt']};"
        f"TrustServerCertificate={cfg['trust']};"
    )


def _rutas_base(
    rutas_base: list[str] | None = None,
    conexion: str = "local",
) -> list[str]:
    if rutas_base:
        limpias = [str(r).strip() for r in rutas_base if str(r).strip()]
        if limpias:
            return limpias

    rutas_config = get_module_paths("orion", conexion)

    if rutas_config:
        return rutas_config

    return list(RED_BASE_PATHS)

def _rutas_red(
    mes_gestion: str,
    rutas_base: list[str] | None = None,
    conexion: str = "local",
) -> list[dict[str, Any]]:
    bases = _rutas_base(rutas_base, conexion)
    nombres = ["Ruta ORION 1", "Ruta ORION 2", "Ruta ORION 3"]

    salida = []

    for idx, base in enumerate(bases):
        ruta_mes = str(Path(base) / mes_gestion) if not base.startswith("\\\\") else base.rstrip("\\") + "\\" + mes_gestion

        salida.append(
            {
                "id": idx + 1,
                "nombre": nombres[idx] if idx < len(nombres) else f"Ruta {idx + 1}",
                "base": base,
                "ruta_mes": ruta_mes,
                "existe_base": Path(base).exists() if not base.startswith("\\\\") else Path(base).exists(),
                "existe_mes": Path(ruta_mes).exists() if not ruta_mes.startswith("\\\\") else Path(ruta_mes).exists(),
                "conexion": str(conexion or "local").lower(),
            }
        )

    return salida

def _rutas_locales(fecha_proceso: str, data_dir: str | None = None) -> dict[str, str]:
    fecha = _fecha_yyyymmdd(fecha_proceso)

    base_root = Path(data_dir or get_data_root())
    base = base_root / fecha
    orion = base / "Orion"

    return {
        "data_root": str(base_root),
        "data_fecha": str(base),
        "orion": str(orion),
        "consolidados": str(orion / "Consolidados"),
        "logs": str(base / "logs"),
    }

def _servidores_locales(cfg: dict[str, str], rutas_red: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tipo": "SQL Server local Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "usuario": cfg["username"],
            "uso": "Carga Causales / Lotes / Discador",
            "visible_solo_local": True,
        },
        {
            "tipo": "Ruta red principal",
            "servidor": r"\\10.24.90.118",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[0]["base"] if len(rutas_red) > 0 else "",
            "visible_solo_local": True,
        },
        {
            "tipo": "Unidad mapeada",
            "servidor": "Z:",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[1]["base"] if len(rutas_red) > 1 else "",
            "visible_solo_local": True,
        },
        {
            "tipo": "Espejo local desarrollo",
            "servidor": "D:",
            "base_datos": "",
            "usuario": "",
            "uso": rutas_red[2]["base"] if len(rutas_red) > 2 else "",
            "visible_solo_local": True,
        }
            ]


def _fecha_estadistica_orion(fecha_sql: str) -> str:
    """
    Para el panel estadístico ORION se usa el día anterior a la fecha de proceso.
    Si el día anterior cae domingo, se retrocede hasta sábado.
    """
    try:
        base = datetime.strptime(str(fecha_sql), "%Y-%m-%d").date()
    except Exception:
        base = datetime.now().date()

    ref = base - timedelta(days=1)

    # Python: lunes=0 ... domingo=6
    while ref.weekday() == 6:
        ref = ref - timedelta(days=1)

    return ref.strftime("%Y-%m-%d")


def _norm_col_orion_v2(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
        .replace(".", "")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )

def _safe_count(cfg: dict[str, str], tabla: str, fecha_sql: str) -> dict[str, Any]:
    """
    Conteo seguro para panel estadístico ORION.

    Regla:
    - No cuenta la fecha del proceso directamente.
    - Cuenta la fecha estadística: fecha proceso - 1 día.
    - Si el día anterior es domingo, retrocede otro día.
    - Busca columnas de fecha de forma amplia: FechayHora, Fecha, Fecha_Hora, etc.
    """
    fecha_ref = _fecha_estadistica_orion(fecha_sql)

    if pyodbc is None:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": "pyodbc no disponible",
            "columna_fecha": "",
            "fecha_referencia": fecha_ref,
        }

    candidatos_fecha = [
        "FechayHora",
        "Fecha y Hora",
        "Fecha_Hora",
        "Fecha Hora",
        "Fecha",
        "fecha",
        "fecha_gestion",
        "FechaGestion",
        "Fecha_Gestion",
        "Fecha de Gestion",
        "Fecha de Gestión",
        "FechaProceso",
        "fecha_proceso",
        "created_at",
        "updated_at",
    ]

    try:
        with pyodbc.connect(_conn_str(cfg), timeout=8) as conn:
            cur = conn.cursor()

            table_row = cur.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA='dbo'
                  AND LOWER(TABLE_NAME)=LOWER(?)
                """,
                tabla,
            ).fetchone()

            if not table_row:
                return {
                    "tabla": tabla,
                    "total": 0,
                    "estado": "no_existe",
                    "detalle": "Tabla no encontrada",
                    "columna_fecha": "",
                    "fecha_referencia": fecha_ref,
                }

            schema = str(table_row.TABLE_SCHEMA)
            table_name = str(table_row.TABLE_NAME)

            columnas_rows = cur.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA=?
                  AND TABLE_NAME=?
                ORDER BY ORDINAL_POSITION
                """,
                schema,
                table_name,
            ).fetchall()

            columnas = [
                {
                    "name": str(r.COLUMN_NAME),
                    "type": str(r.DATA_TYPE).lower(),
                    "norm": _norm_col_orion_v2(str(r.COLUMN_NAME)),
                }
                for r in columnas_rows
            ]

            columna_fecha = ""
            tipo_fecha = ""

            # 1) Coincidencia por candidatos conocidos.
            for candidato in candidatos_fecha:
                nc = _norm_col_orion_v2(candidato)

                for col in columnas:
                    if col["norm"] == nc:
                        columna_fecha = col["name"]
                        tipo_fecha = col["type"]
                        break

                if columna_fecha:
                    break

            # 2) Fallback: cualquier columna que contenga "fecha".
            if not columna_fecha:
                for col in columnas:
                    if "fecha" in col["norm"]:
                        columna_fecha = col["name"]
                        tipo_fecha = col["type"]
                        break

            # 3) Fallback: cualquier columna tipo datetime/date.
            if not columna_fecha:
                for col in columnas:
                    if col["type"] in ("date", "datetime", "datetime2", "smalldatetime", "datetimeoffset"):
                        columna_fecha = col["name"]
                        tipo_fecha = col["type"]
                        break

            if columna_fecha:
                total = cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM [{schema}].[{table_name}]
                    WHERE TRY_CAST([{columna_fecha}] AS DATE)=?
                    """,
                    fecha_ref,
                ).fetchval()

                return {
                    "tabla": table_name,
                    "total": int(total or 0),
                    "estado": "ok",
                    "detalle": f"Fecha referencia {fecha_ref}; filtrado por {columna_fecha}",
                    "columna_fecha": columna_fecha,
                    "fecha_referencia": fecha_ref,
                }

            total = cur.execute(f"SELECT COUNT(*) FROM [{schema}].[{table_name}]").fetchval()

            return {
                "tabla": table_name,
                "total": int(total or 0),
                "estado": "ok",
                "detalle": f"Sin columna fecha; total general. Fecha referencia sugerida {fecha_ref}",
                "columna_fecha": "",
                "fecha_referencia": fecha_ref,
            }

    except Exception as exc:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": str(exc),
            "columna_fecha": "",
            "fecha_referencia": fecha_ref,
        }

def construir_contexto_orion_v2(
    fecha_proceso: str,
    mes_gestion: str,
    conexion: str,
    rutas_base: list[str] | None = None,
) -> dict[str, Any]:
    fecha_proceso = _fecha_yyyymmdd(fecha_proceso)
    mes_gestion = _normalizar_mes(mes_gestion, fecha_proceso)

    cfg = _orion_config(conexion)
    rutas_red = _rutas_red(mes_gestion, rutas_base, cfg["conexion"])
    rutas_locales = _rutas_locales(fecha_proceso)

    return {
        "modulo": "orion",
        "titulo": "Gestión Diaria Orion",
        "fecha_proceso": fecha_proceso,
        "fecha_sql": _fecha_sql(fecha_proceso),
        "mes_gestion": mes_gestion,
        "conexion": cfg["conexion"],
        "rutas_red": rutas_red,
        "rutas_locales": rutas_locales,
        "servidores_locales": _servidores_locales(cfg, rutas_red) if cfg["conexion"] == "local" else [],
        "fases": [
            {
                **fase,
                "estado": "pendiente",
                "badge": "Pendiente",
            }
            for fase in FASES_ORION
        ],
    }


def construir_estadisticas_orion_v2(
    fecha_proceso: str,
    mes_gestion: str,
    conexion: str,
    rutas_base: list[str] | None = None,
) -> dict[str, Any]:
    contexto = construir_contexto_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
        rutas_base=rutas_base,
    )

    cfg = _orion_config(conexion)
    fecha_sql = contexto["fecha_sql"]

    conteos = {
        "causales": _safe_count(cfg, "causales", fecha_sql),
        "lote": _safe_count(cfg, "lote", fecha_sql),
        "discador": _safe_count(cfg, "discador", fecha_sql),
    }

    conexiones = [
        {
            "proceso": "Carga Causales",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.causales",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["causales"]["estado"],
            "total": conteos["causales"]["total"],
            "detalle": conteos["causales"]["detalle"],
        },
        {
            "proceso": "Carga Lotes",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.lote",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["lote"]["estado"],
            "total": conteos["lote"]["total"],
            "detalle": conteos["lote"]["detalle"],
        },
        {
            "proceso": "Carga Discador",
            "origen": "Excel consolidado Orion",
            "destino": "SQL Server Orion",
            "servidor": cfg["server"],
            "base_datos": cfg["database"],
            "tabla": "dbo.discador",
            "ruta": contexto["rutas_locales"]["consolidados"],
            "estado": conteos["discador"]["estado"],
            "total": conteos["discador"]["total"],
            "detalle": conteos["discador"]["detalle"],
        }
            ]

    total_cargado = sum(int(item.get("total") or 0) for item in conteos.values())

    contexto.update(
        {
            "metricas": [
                {
                    "titulo": "Causales",
                    "valor": conteos["causales"]["total"],
                    "detalle": conteos["causales"]["detalle"],
                },
                {
                    "titulo": "Lotes",
                    "valor": conteos["lote"]["total"],
                    "detalle": conteos["lote"]["detalle"],
                },
                {
                    "titulo": "Discador",
                    "valor": conteos["discador"]["total"],
                    "detalle": conteos["discador"]["detalle"],
                }
            ],
            "conexiones": conexiones,
            "estadisticas_ejecutadas": True,
        }
    )

    return contexto

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN ===

def _orion_v2_destino_categoria(carpeta_diaria: str, categoria: str) -> str:
    destinos = {
        "Causales": os.path.join(carpeta_diaria, "Causales"),
        "Lotes": os.path.join(carpeta_diaria, "Lotes"),
        "Discador": os.path.join(carpeta_diaria, "Discador"),
    }

    return destinos.get(categoria, carpeta_diaria)


def _orion_v2_resolver_distribucion(
    data_dir: str,
    fecha_proceso: str,
    rutas_base: list[str] | None = None,
    conexion: str = "local",
) -> dict[str, Any]:
    from app.services.orion_fases_service import preparar_distribucion_archivos_orion

    fecha = _fecha_yyyymmdd(fecha_proceso)
    candidatos = _rutas_base(rutas_base, conexion)
    errores = []

    for red_base in candidatos:
        respuesta = preparar_distribucion_archivos_orion(
            data_dir=data_dir,
            fecha_raw=fecha,
            red_base=red_base,
            log_service=None,
        )

        if respuesta.get("success"):
            respuesta["red_base_usada"] = red_base
            return respuesta

        errores.append(
            {
                "red_base": red_base,
                "error": respuesta.get("error", "No disponible"),
                "status": respuesta.get("status", "error"),
            }
        )

    return {
        "success": False,
        "fecha": fecha,
        "error": "No se pudo preparar distribución con ninguna ruta base.",
        "errores": errores,
    }


def preparar_distribucion_orion_v2(
    data_dir: str,
    fecha_proceso: str,
    mes_gestion: str,
    rutas_base: list[str] | None = None,
    conexion: str = "local",
) -> dict[str, Any]:
    respuesta = _orion_v2_resolver_distribucion(
        data_dir=data_dir,
        fecha_proceso=fecha_proceso,
        rutas_base=rutas_base,
        conexion=conexion,
    )

    fecha = _fecha_yyyymmdd(fecha_proceso)

    if not respuesta.get("success"):
        return {
            "success": False,
            "fecha_proceso": fecha,
            "error": respuesta.get("error", "Error preparando distribución."),
            "errores": respuesta.get("errores", []),
        }

    carpeta_diaria = respuesta["carpeta_diaria"]
    rutas_validadas = respuesta.get("rutas_validadas", {})
    archivos_encontrados = respuesta.get("archivos_encontrados", {})

    grupos = []
    total_archivos = 0

    for categoria in ["Causales", "Lotes", "Discador"]:
        ruta_origen = str(rutas_validadas.get(categoria, "") or "")
        destino_dir = _orion_v2_destino_categoria(carpeta_diaria, categoria)
        archivos = []

        for archivo in archivos_encontrados.get(categoria, []) or []:
            total_archivos += 1

            archivo = str(archivo)
            ruta_destino = os.path.join(destino_dir, archivo)
            existe_destino = os.path.isfile(ruta_destino)

            archivos.append(
                {
                    "categoria": categoria,
                    "archivo": archivo,
                    "ruta_origen": ruta_origen,
                    "ruta_destino": ruta_destino,
                    "existe_destino": existe_destino,
                    "estado_destino": "Ya existe, se reemplazará" if existe_destino else "Nuevo",
                    "checked": True,
                }
            )

        grupos.append(
            {
                "categoria": categoria,
                "ruta_origen": ruta_origen,
                "ruta_destino": destino_dir,
                "total": len(archivos),
                "archivos": archivos,
            }
        )

    return {
        "success": True,
        "fecha_proceso": fecha,
        "mes_gestion": _normalizar_mes(mes_gestion, fecha),
        "red_base_usada": respuesta.get("red_base_usada", ""),
        "carpeta_diaria": carpeta_diaria,
        "grupos": grupos,
        "total_archivos": total_archivos,
    }


def copiar_distribucion_orion_v2(
    data_dir: str,
    fecha_proceso: str,
    mes_gestion: str,
    seleccionados: list[dict[str, Any]],
    rutas_base: list[str] | None = None,
    conexion: str = "local",
) -> dict[str, Any]:
    from app.services.orion_fases_service import distribuir_archivos_seleccionados_orion
    from app.services.orion_fases_renderer import render_distribucion_seleccionados_orion

    fecha = _fecha_yyyymmdd(fecha_proceso)
    candidatos = _rutas_base(rutas_base, conexion)
    errores = []

    if not isinstance(seleccionados, list) or not seleccionados:
        return {
            "success": False,
            "fecha_proceso": fecha,
            "error": "No seleccionó archivos para copiar.",
            "result_html": "<div class='log-line error'>❌ No seleccionó archivos para copiar.</div>",
            "copiados_detalle": [],
            "errores": [],
        }

    for red_base in candidatos:
        respuesta = distribuir_archivos_seleccionados_orion(
            data_dir=data_dir,
            fecha_raw=fecha,
            seleccionados=seleccionados,
            red_base=red_base,
            log_service=None,
        )

        if respuesta.get("success"):
            return {
                "success": True,
                "fecha_proceso": fecha,
                "mes_gestion": _normalizar_mes(mes_gestion, fecha),
                "red_base_usada": red_base,
                "result_html": render_distribucion_seleccionados_orion(respuesta),
                "copiados_detalle": respuesta.get("copiados_detalle", []),
                "errores": respuesta.get("errores", []),
            }

        errores.append(
            {
                "red_base": red_base,
                "error": respuesta.get("error", "No se pudo copiar con esta ruta."),
                "status": respuesta.get("status", "error"),
            }
        )

    error = errores[-1]["error"] if errores else "No se pudo copiar archivos."

    return {
        "success": False,
        "fecha_proceso": fecha,
        "error": error,
        "result_html": f"<div class='log-line error'>❌ {error}</div>",
        "copiados_detalle": [],
        "errores": errores,
    }

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_END ===

# === ORION_DIARIO_V2_COMPARAR_LOTES_BEGIN ===

def _odv2_accion_item(item):
    if not isinstance(item, dict):
        return ""

    return (
        item.get("accion")
        or item.get("action")
        or item.get("id")
        or item.get("codigo_accion")
        or ""
    )


def _odv2_crear_comparar_lotes_item():
    return {
        "codigo": "F4",
        "letra": "F4",
        "fase": "F",
        "titulo": "Comparar Lotes",
        "nombre": "Comparar Lotes",
        "descripcion": "Compara lotes procesados contra Discador para validar consistencia.",
        "detalle": "Validación cruzada Lotes vs Discador.",
        "accion": "comparar.lotes",
        "action": "comparar.lotes",
        "icono": "⚖️",
        "orden": 8.5,
    }


def _odv2_insertar_comparar_lotes_en_lista(lista):
    if not isinstance(lista, list):
        return False

    if any(_odv2_accion_item(item) == "comparar.lotes" for item in lista):
        return False

    idx_lotes = -1

    for idx, item in enumerate(lista):
        if _odv2_accion_item(item) == "procesar.lotes":
            idx_lotes = idx
            break

    if idx_lotes < 0:
        return False

    lista.insert(idx_lotes + 1, _odv2_crear_comparar_lotes_item())
    return True


def _odv2_asegurar_comparar_lotes(contexto):
    visitados = set()

    def walk(obj):
        oid = id(obj)

        if oid in visitados:
            return

        visitados.add(oid)

        if isinstance(obj, list):
            _odv2_insertar_comparar_lotes_en_lista(obj)

            for item in obj:
                walk(item)

            return

        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    walk(value)

    if isinstance(contexto, dict):
        walk(contexto)

    return contexto


try:
    _odv2_construir_contexto_original = construir_contexto_orion_v2

    def construir_contexto_orion_v2(*args, **kwargs):
        contexto = _odv2_construir_contexto_original(*args, **kwargs)
        return _odv2_asegurar_comparar_lotes(contexto)

except NameError:
    pass

# === ORION_DIARIO_V2_COMPARAR_LOTES_END ===

# === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_BEGIN ===

def _odv2_carga_fecha_yyyymmdd(fecha):
    from datetime import datetime

    raw = str(fecha or "").strip().replace("-", "").replace("_", "").replace("/", "")

    if len(raw) == 8 and raw.isdigit():
        return raw

    try:
        return datetime.now().strftime("%Y%m%d")
    except Exception:
        return "20260429"


def _odv2_carga_fecha_sql(fecha):
    raw = _odv2_carga_fecha_yyyymmdd(fecha)
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def _odv2_carga_tipo_normalizado(tipo):
    t = str(tipo or "").strip().lower()

    if t in ("causal", "causales"):
        return "causales"

    if t in ("lote", "lotes"):
        return "lote"

    if t in ("discador", "discadores"):
        return "discador"

    return t


def _odv2_carga_tabla_destino(tipo):
    tipo = _odv2_carga_tipo_normalizado(tipo)

    if tipo == "causales":
        return ["causales"]

    if tipo == "lote":
        return ["lote", "lotes"]

    if tipo == "discador":
        return ["discador"]

    return [tipo]


def _odv2_carga_label(tipo):
    tipo = _odv2_carga_tipo_normalizado(tipo)

    if tipo == "causales":
        return "Causales"

    if tipo == "lote":
        return "Lotes"

    if tipo == "discador":
        return "Discador"

    return tipo.title()


def _odv2_carga_qname(name):
    return "[" + str(name).replace("]", "]]") + "]"


def _odv2_carga_env_first(*names, default=""):
    import os

    for name in names:
        value = os.getenv(name)

        if value:
            return value

    return default


def _odv2_carga_load_env():
    try:
        from dotenv import load_dotenv
        from pathlib import Path

        load_dotenv(Path.cwd() / ".env")
    except Exception:
        pass


def _odv2_carga_conn_info(conexion):
    _odv2_carga_load_env()

    conexion = str(conexion or "local").strip().lower()

    driver = _odv2_carga_env_first(
        "ORION_SQL_DRIVER",
        "GESTION_SQL_DRIVER",
        "SQLSERVER_DRIVER",
        default="ODBC Driver 18 for SQL Server",
    )

    database = _odv2_carga_env_first(
        "ORION_SQL_ORION_DATABASE",
        "ORION_SQL_DATABASE",
        "ORION_DATABASE",
        "SQLSERVER_ORION_DATABASE",
        default="Orion",
    )

    if conexion == "remoto":
        server = _odv2_carga_env_first(
            "ORION_SQL_REMOTE_SERVER",
            "GESTION_SQL_REMOTE_SERVER",
            "SQLSERVER_REMOTE_SERVER",
            default="VC-EIDER",
        )

        user = _odv2_carga_env_first(
            "ORION_SQL_REMOTE_USERNAME",
            "ORION_SQL_REMOTE_USER",
            "GESTION_SQL_REMOTE_USER",
            "SQLSERVER_REMOTE_USER",
            "SQLSERVER_USER",
            default="Admin1",
        )

        password = _odv2_carga_env_first(
            "ORION_SQL_REMOTE_PASSWORD",
            "GESTION_SQL_REMOTE_PASSWORD",
            "SQLSERVER_REMOTE_PASSWORD",
            "SQLSERVER_PASSWORD",
            default="",
        )
    else:
        server = _odv2_carga_env_first(
            "ORION_SQL_LOCAL_SERVER",
            "GESTION_SQL_LOCAL_SERVER",
            "SQLSERVER_SERVER",
            default=r"localhost\SQL2025DEV",
        )

        user = _odv2_carga_env_first(
            "ORION_SQL_LOCAL_USERNAME",
            "ORION_SQL_LOCAL_USER",
            "GESTION_SQL_USER",
            "SQLSERVER_USER",
            default="Admin1",
        )

        password = _odv2_carga_env_first(
            "ORION_SQL_LOCAL_PASSWORD",
            "GESTION_SQL_PASSWORD",
            "SQLSERVER_PASSWORD",
            default="",
        )

    return {
        "conexion": conexion,
        "driver": driver,
        "server": server,
        "database": database,
        "user": user,
        "password": password,
    }


def _odv2_carga_connection_string(info):
    return (
        f"DRIVER={{{info['driver']}}};"
        f"SERVER={info['server']};"
        f"DATABASE={info['database']};"
        f"UID={info['user']};"
        f"PWD={info['password']};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


def _odv2_carga_buscar_archivo_origen(data_dir, fecha, tipo):
    from pathlib import Path

    fecha = _odv2_carga_fecha_yyyymmdd(fecha)
    tipo = _odv2_carga_tipo_normalizado(tipo)

    base = Path(data_dir) / fecha / "Orion"

    patrones = {
        "causales": ["**/*Causal*Consolid*.xlsx", "**/*Causales*Consolid*.xlsx"],
        "lote": ["**/*Lote*Consolid*.xlsx", "**/*Lotes*Consolid*.xlsx", "**/*lote*consolid*.xlsx"],
        "discador": ["**/*Discador*Consolid*.xlsx", "**/*discador*consolid*.xlsx"],
    }

    encontrados = []

    for patron in patrones.get(tipo, ["**/*Consolid*.xlsx"]):
        encontrados.extend([p for p in base.glob(patron) if p.is_file()])

    # Evitar duplicados conservando orden
    vistos = set()
    unicos = []

    for item in encontrados:
        key = str(item).lower()

        if key in vistos:
            continue

        vistos.add(key)
        unicos.append(item)

    return {
        "base_orion": str(base),
        "archivo_principal": str(unicos[0]) if unicos else "",
        "archivos_encontrados": [str(p) for p in unicos],
        "total_archivos": len(unicos),
    }


def precheck_carga_orion_v2(data_dir, fecha_proceso, tipo, conexion="local"):
    import pyodbc

    fecha_yyyymmdd = _odv2_carga_fecha_yyyymmdd(fecha_proceso)
    fecha_sql = _odv2_carga_fecha_sql(fecha_proceso)
    tipo_norm = _odv2_carga_tipo_normalizado(tipo)
    tipo_label = _odv2_carga_label(tipo_norm)
    tablas_candidatas = _odv2_carga_tabla_destino(tipo_norm)
    conn_info = _odv2_carga_conn_info(conexion)
    origen = _odv2_carga_buscar_archivo_origen(data_dir, fecha_yyyymmdd, tipo_norm)

    data = {
        "ok": False,
        "bloqueado": True,
        "duplicado": False,
        "tipo": tipo_norm,
        "tipo_label": tipo_label,
        "fecha_proceso": fecha_yyyymmdd,
        "fecha_sql": fecha_sql,
        "conexion": conn_info["conexion"],
        "servidor_destino": conn_info["server"],
        "bd_destino": conn_info["database"],
        "tabla_destino": "",
        "tabla_schema": "",
        "fecha_columna": "",
        "registros_existentes": 0,
        "mensaje": "",
        "origen": origen,
        "tablas_candidatas": tablas_candidatas,
        "columnas_fecha_evaluadas": [],
    }

    date_preference = [
        # Preferencias explícitas por fecha de proceso/carga
        "fecha_proceso",
        "fechaproceso",
        "fecha proceso",
        "fecha_de_proceso",
        "fecha de proceso",

        "fecha_carga",
        "fechacarga",
        "fecha carga",
        "fecha_de_carga",
        "fecha de carga",

        # Fechas propias de gestión/llamada
        "fecha",
        "fecha_gestion",
        "fechagestion",
        "fecha gestion",
        "fecha_de_gestion",
        "fecha de gestion",
        "fecha_de_la_gestion",
        "fecha de la gestion",
        "fecha_de_gestión",
        "fecha de gestión",
        "fecha_gestión",
        "fechagestión",

        "fecha_llamada",
        "fechallamada",
        "fecha llamada",
        "fecha_de_llamada",
        "fecha de llamada",

        "fecha_hora",
        "fechahora",
        "fecha hora",
        "fecha_hora_gestion",
        "fecha hora gestion",
        "fecha_y_hora",
        "fecha y hora",

        # Fechas técnicas
        "created_at",
        "updated_at",
        "fecha_creacion",
        "fecha_modificacion",
    ]

    try:
        conn = pyodbc.connect(_odv2_carga_connection_string(conn_info), timeout=10)
        cur = conn.cursor()

        tables = cur.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE'
            """
        ).fetchall()

        table_match = None

        lower_candidates = [x.lower() for x in tablas_candidatas]

        for row in tables:
            name = str(row.TABLE_NAME).lower()

            if name in lower_candidates:
                table_match = row
                break

        if not table_match:
            data["mensaje"] = f"No se encontró tabla destino para {tipo_label}. Candidatas: {', '.join(tablas_candidatas)}."
            return data

        schema = str(table_match.TABLE_SCHEMA)
        table = str(table_match.TABLE_NAME)

        data["tabla_schema"] = schema
        data["tabla_destino"] = f"{schema}.{table}"

        columns = cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA=? AND TABLE_NAME=?
            ORDER BY ORDINAL_POSITION
            """,
            schema,
            table,
        ).fetchall()

        def _norm_col(value):
            return (
                str(value or "")
                .strip()
                .lower()
                .replace(" ", "")
                .replace("_", "")
                .replace("-", "")
                .replace("/", "")
                .replace(".", "")
                .replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
            )

        colmap = {
            _norm_col(c.COLUMN_NAME): (str(c.COLUMN_NAME), str(c.DATA_TYPE).lower())
            for c in columns
        }

        selected_col = None

        # 1) Override manual desde .env si se necesita forzar columna por tabla/tipo.
        #    Ejemplos:
        #    ORION_CARGA_FECHA_CAUSALES=Fecha De Gestion
        #    ORION_CARGA_FECHA_LOTE=fecha
        #    ORION_CARGA_FECHA_DISCADOR=Fecha_Hora
        override_env = {
            "causales": "ORION_CARGA_FECHA_CAUSALES",
            "lote": "ORION_CARGA_FECHA_LOTE",
            "discador": "ORION_CARGA_FECHA_DISCADOR",
        }.get(tipo_norm)

        override_col = _odv2_carga_env_first(override_env, default="") if override_env else ""

        if override_col:
            override_key = _norm_col(override_col)

            if override_key in colmap:
                selected_col = colmap[override_key]
            else:
                data["mensaje"] = (
                    f"La columna definida en .env {override_env}={override_col} no existe en {schema}.{table}."
                )
                return data

        # 2) Búsqueda exacta por preferencias conocidas.
        if not selected_col:
            for candidate in date_preference:
                key = _norm_col(candidate)

                if key in colmap:
                    selected_col = colmap[key]
                    break

        # 3) Fallback: cualquier columna que contenga fecha.
        if not selected_col:
            for key, value in colmap.items():
                if "fecha" in key:
                    selected_col = value
                    break

        # 4) Fallback adicional: columnas datetime aunque no se llamen fecha.
        if not selected_col:
            for key, value in colmap.items():
                col_name, col_type = value

                if col_type in ("date", "datetime", "datetime2", "smalldatetime", "datetimeoffset"):
                    selected_col = value
                    break

        if not selected_col:
            columnas_disponibles = ", ".join([str(c.COLUMN_NAME) for c in columns])

            data["mensaje"] = (
                f"No se encontró columna de fecha en {schema}.{table}. "
                f"Columnas disponibles: {columnas_disponibles}. "
                "No se permite insertar hasta definir la columna de control de fecha."
            )
            return data

        col_name, col_type = selected_col
        data["fecha_columna"] = col_name
        data["columnas_fecha_evaluadas"] = [col_name]

        qschema = _odv2_carga_qname(schema)
        qtable = _odv2_carga_qname(table)
        qcol = _odv2_carga_qname(col_name)

        fecha_ddmmyyyy = f"{fecha_yyyymmdd[6:8]}{fecha_yyyymmdd[4:6]}{fecha_yyyymmdd[0:4]}"

        if col_type in ("date", "datetime", "datetime2", "smalldatetime", "datetimeoffset"):
            sql = f"SELECT COUNT(1) FROM {qschema}.{qtable} WHERE CAST({qcol} AS date)=?"
            count = int(cur.execute(sql, fecha_sql).fetchone()[0] or 0)
        else:
            sql = (
                f"SELECT COUNT(1) FROM {qschema}.{qtable} "
                f"WHERE TRY_CONVERT(date, {qcol})=? "
                f"OR REPLACE(REPLACE(REPLACE(CONVERT(varchar(64), {qcol}), '-', ''), '/', ''), ' ', '')=? "
                f"OR REPLACE(REPLACE(REPLACE(CONVERT(varchar(64), {qcol}), '-', ''), '/', ''), ' ', '')=?"
            )
            count = int(cur.execute(sql, fecha_sql, fecha_yyyymmdd, fecha_ddmmyyyy).fetchone()[0] or 0)

        data["registros_existentes"] = count
        data["duplicado"] = count > 0
        data["bloqueado"] = count > 0
        data["ok"] = True

        if count > 0:
            data["mensaje"] = (
                f"Ya existen {count} registros en {schema}.{table} para la fecha {fecha_sql}. "
                "La inserción fue bloqueada para evitar duplicados."
            )
        else:
            data["mensaje"] = (
                f"No existen registros previos en {schema}.{table} para la fecha {fecha_sql}. "
                "Puede continuar con la inserción."
            )

        return data

    except Exception as exc:
        data["mensaje"] = f"Error validando duplicados en SQL Server: {exc}"
        return data

# === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_END ===
