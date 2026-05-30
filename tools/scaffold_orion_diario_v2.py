from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()
BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")


FILES = {
    "app/controllers/orion_diario_v2_blueprint.py": r'''
from flask import Blueprint, jsonify, render_template, request

from app.services.orion_diario_v2_dashboard_service import (
    construir_contexto_orion_v2,
    construir_estadisticas_orion_v2,
)


orion_diario_v2_bp = Blueprint("orion_diario_v2", __name__)


@orion_diario_v2_bp.route("/orion-diario-v2")
def vista_orion_diario_v2():
    return render_template("orion_diario_v2/index.html")


@orion_diario_v2_bp.route("/api/orion-diario-v2/contexto")
def api_orion_diario_v2_contexto():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    conexion = request.args.get("conexion", "local").strip().lower()

    data = construir_contexto_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
    )

    return jsonify(data)


@orion_diario_v2_bp.route("/api/orion-diario-v2/estadisticas")
def api_orion_diario_v2_estadisticas():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    conexion = request.args.get("conexion", "local").strip().lower()

    rutas_base = request.args.getlist("rutas_base")

    data = construir_estadisticas_orion_v2(
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        conexion=conexion,
        rutas_base=rutas_base,
    )

    return jsonify(data)
''',

    "app/services/orion_diario_v2_dashboard_service.py": r'''
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import os
import re

try:
    import pyodbc
except Exception:
    pyodbc = None


ROOT = Path.cwd()


RED_BASE_PATHS = [
    r"\\10.24.90.118\Vencorp\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
    r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_orion\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Orion",
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
        "accion": "crear_carpetas",
    },
    {
        "codigo": "B",
        "nombre": "Verificar red",
        "grupo": "Preparación",
        "descripcion": "Verifica disponibilidad de rutas de red, unidad Z y espejo local.",
        "accion": "verificar_red",
    },
    {
        "codigo": "C",
        "nombre": "OCR y Totales",
        "grupo": "OCR",
        "descripcion": "Procesa OCR, extrae totales y valida archivos base.",
        "accion": "ocr_totales",
    },
    {
        "codigo": "D",
        "nombre": "Distribuir archivos",
        "grupo": "Distribución",
        "descripcion": "Distribuye archivos por carpetas de trabajo y tipo de insumo.",
        "accion": "distribuir_archivos",
    },
    {
        "codigo": "E1",
        "nombre": "Procesar Discador",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de discador para carga SQL.",
        "accion": "procesar_discador",
    },
    {
        "codigo": "E2",
        "nombre": "Procesar Causales",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de causales para carga SQL.",
        "accion": "procesar_causales",
    },
    {
        "codigo": "E3",
        "nombre": "Procesar Lotes",
        "grupo": "Procesamiento",
        "descripcion": "Normaliza información de lotes para carga SQL.",
        "accion": "procesar_lotes",
    },
    {
        "codigo": "F1",
        "nombre": "Carga Causales",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta causales en base Orion.",
        "accion": "carga_causales",
    },
    {
        "codigo": "F2",
        "nombre": "Carga Lotes",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta lotes en base Orion.",
        "accion": "carga_lotes",
    },
    {
        "codigo": "F3",
        "nombre": "Carga Discador",
        "grupo": "Carga SQL",
        "descripcion": "Verifica e inserta discador en base Orion.",
        "accion": "carga_discador",
    },
    {
        "codigo": "G",
        "nombre": "Consolidado Gestión Orion",
        "grupo": "Consolidado",
        "descripcion": "Genera resumen final de Gestión Diaria Orion.",
        "accion": "consolidado_orion",
    },
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
    _leer_env_local()

    conexion = str(conexion or "local").strip().lower()

    if conexion == "remoto":
        server = os.getenv("ORION_SQL_REMOTE_SERVER", os.getenv("ORION_REMOTE_SERVER", "VC-EIDER"))
        database = os.getenv("ORION_SQL_REMOTE_DATABASE", "Orion")
        username = os.getenv("ORION_SQL_REMOTE_USERNAME", "Admin1")
        password = os.getenv("ORION_SQL_REMOTE_PASSWORD", "")
    else:
        server = os.getenv("ORION_CARGAS_SQL_SERVER", os.getenv("ORION_SQL_LOCAL_SERVER", r"localhost\SQL2025DEV"))
        database = os.getenv("ORION_CARGAS_SQL_DATABASE", os.getenv("ORION_SQL_LOCAL_DATABASE", "Orion"))
        username = os.getenv("ORION_CARGAS_SQL_USER", os.getenv("ORION_SQL_LOCAL_USERNAME", "Admin1"))
        password = os.getenv("ORION_CARGAS_SQL_PASSWORD", os.getenv("ORION_SQL_LOCAL_PASSWORD", "1234"))

    return {
        "conexion": conexion,
        "driver": os.getenv("ORION_CARGAS_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
        "server": server,
        "database": database,
        "username": username,
        "password": password,
        "encrypt": os.getenv("ORION_CARGAS_SQL_ENCRYPT", "yes"),
        "trust": os.getenv("ORION_CARGAS_SQL_TRUST_SERVER_CERTIFICATE", "yes"),
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


def _rutas_base(rutas_base: list[str] | None = None) -> list[str]:
    if rutas_base:
        limpias = [str(r).strip() for r in rutas_base if str(r).strip()]
        if limpias:
            return limpias

    return list(RED_BASE_PATHS)


def _rutas_red(mes_gestion: str, rutas_base: list[str] | None = None) -> list[dict[str, Any]]:
    bases = _rutas_base(rutas_base)
    nombres = ["Ruta red UNC", "Unidad Z", "Espejo local"]

    salida = []

    for idx, base in enumerate(bases):
        ruta_mes = str(Path(base) / mes_gestion) if not base.startswith("\\\\") else base.rstrip("\\") + "\\" + mes_gestion

        salida.append(
            {
                "id": idx + 1,
                "nombre": nombres[idx] if idx < len(nombres) else f"Ruta {idx + 1}",
                "base": base,
                "ruta_mes": ruta_mes,
                "existe_base": Path(base).exists() if not base.startswith("\\\\") else False,
                "existe_mes": Path(ruta_mes).exists() if not ruta_mes.startswith("\\\\") else False,
            }
        )

    return salida


def _rutas_locales(fecha_proceso: str) -> dict[str, str]:
    fecha = _fecha_yyyymmdd(fecha_proceso)

    base = ROOT / "data" / fecha
    orion = base / "Orion"

    return {
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
        },
    ]


def _safe_count(cfg: dict[str, str], tabla: str, fecha_sql: str) -> dict[str, Any]:
    if pyodbc is None:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": "pyodbc no disponible",
            "columna_fecha": "",
        }

    candidatos_fecha = [
        "fecha",
        "Fecha",
        "Fecha_Hora",
        "fecha_proceso",
        "FechaProceso",
        "created_at",
    ]

    try:
        with pyodbc.connect(_conn_str(cfg), timeout=8) as conn:
            cur = conn.cursor()

            exists = cur.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA='dbo'
                  AND LOWER(TABLE_NAME)=LOWER(?)
                """,
                tabla,
            ).fetchval()

            if not exists:
                return {
                    "tabla": tabla,
                    "total": 0,
                    "estado": "no_existe",
                    "detalle": "Tabla no encontrada",
                    "columna_fecha": "",
                }

            columnas = [
                r.COLUMN_NAME
                for r in cur.execute(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA='dbo'
                      AND LOWER(TABLE_NAME)=LOWER(?)
                    ORDER BY ORDINAL_POSITION
                    """,
                    tabla,
                ).fetchall()
            ]

            columna_fecha = ""

            for candidato in candidatos_fecha:
                for col in columnas:
                    if col.lower() == candidato.lower():
                        columna_fecha = col
                        break

                if columna_fecha:
                    break

            if columna_fecha:
                total = cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM dbo.[{tabla}]
                    WHERE TRY_CAST([{columna_fecha}] AS DATE)=?
                    """,
                    fecha_sql,
                ).fetchval()

                return {
                    "tabla": tabla,
                    "total": int(total or 0),
                    "estado": "ok",
                    "detalle": f"Filtrado por {columna_fecha}",
                    "columna_fecha": columna_fecha,
                }

            total = cur.execute(f"SELECT COUNT(*) FROM dbo.[{tabla}]").fetchval()

            return {
                "tabla": tabla,
                "total": int(total or 0),
                "estado": "ok",
                "detalle": "Sin columna fecha; total general",
                "columna_fecha": "",
            }

    except Exception as exc:
        return {
            "tabla": tabla,
            "total": 0,
            "estado": "error",
            "detalle": str(exc),
            "columna_fecha": "",
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
    rutas_red = _rutas_red(mes_gestion, rutas_base)
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
        },
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
                },
                {
                    "titulo": "Total Orion",
                    "valor": total_cargado,
                    "detalle": "Suma de tablas principales Orion",
                },
            ],
            "conexiones": conexiones,
            "estadisticas_ejecutadas": True,
        }
    )

    return contexto
''',

    "app/templates/orion_diario_v2/index.html": r'''
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Gestión Diaria Orion v2</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/orion_diario_v2.css') }}">
</head>
<body>
    {% include "orion_diario_v2/partials/_header.html" %}

    <main class="odv2-shell">
        {% include "orion_diario_v2/partials/_context_bar.html" %}

        <section class="odv2-layout">
            <aside class="odv2-sidebar">
                {% include "orion_diario_v2/partials/_phase_sidebar.html" %}
                {% include "orion_diario_v2/partials/_routes_panel.html" %}
            </aside>

            <section class="odv2-main">
                {% include "orion_diario_v2/partials/_title_panel.html" %}
                {% include "orion_diario_v2/partials/_metrics_panel.html" %}
                {% include "orion_diario_v2/partials/_connections_panel.html" %}
                {% include "orion_diario_v2/partials/_phase_board.html" %}
            </section>
        </section>
    </main>

    {% include "orion_diario_v2/partials/_paths_modal.html" %}

    <script src="{{ url_for('static', filename='js/orion_diario_v2.js') }}"></script>
</body>
</html>
''',

    "app/templates/orion_diario_v2/partials/_header.html": r'''
<header class="odv2-header">
    <div class="odv2-brand">
        <span class="odv2-logo">⚙️</span>
        <div>
            <h1>Orion Procesos</h1>
            <p>Gestión Diaria Orion v2 — formato visual tipo Consolidar Gestión</p>
        </div>
    </div>

    <nav class="odv2-tabs">
        <a class="odv2-tab active" href="/orion-diario-v2">Gestión Diaria Orion</a>
        <a class="odv2-tab disabled" href="#">Gestión Diaria ASTER</a>
        <a class="odv2-tab disabled" href="#">Consolidar Gestión</a>
    </nav>
</header>
''',

    "app/templates/orion_diario_v2/partials/_context_bar.html": r'''
<section class="odv2-context">
    <div class="odv2-field">
        <label>Fecha proceso</label>
        <input id="odv2-fecha-proceso" value="20260429">
    </div>

    <div class="odv2-field">
        <label>Mes gestión</label>
        <input id="odv2-mes-gestion" value="abril" placeholder="abril, mayo, junio...">
    </div>

    <div class="odv2-field">
        <label>Conexión global</label>
        <div class="odv2-buttons">
            <button class="odv2-btn active" data-conn="local">LOCAL - Pruebas</button>
            <button class="odv2-btn" data-conn="remoto">REMOTO - Producción</button>
        </div>
    </div>

    <div class="odv2-actions">
        <button id="odv2-load-context" class="odv2-secondary">Cargar contexto</button>
        <button id="odv2-load-stats" class="odv2-primary">Ejecutar panel estadístico</button>
    </div>
</section>
''',

    "app/templates/orion_diario_v2/partials/_phase_sidebar.html": r'''
<div class="odv2-card odv2-collapsible" data-collapse-key="phase-sidebar">
    <button class="odv2-card-head" type="button">
        <span>📌 Estado de fases</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-sidebar-phases" class="odv2-empty">Cargue contexto para ver fases.</div>
    </div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_routes_panel.html": r'''
<div class="odv2-card odv2-collapsible" data-collapse-key="routes-panel">
    <button class="odv2-card-head" type="button">
        <span>📁 Rutas ORION</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-routes" class="odv2-empty">Cargue contexto para ver rutas.</div>
        <button class="odv2-secondary full" id="odv2-edit-paths">Modificar rutas</button>
    </div>
</div>

<div class="odv2-card odv2-collapsible" data-collapse-key="local-servers-panel">
    <button class="odv2-card-head" type="button">
        <span>🖥️ Servidores LOCAL</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-local-servers" class="odv2-empty">Visible cuando la conexión sea LOCAL.</div>
    </div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_title_panel.html": r'''
<div class="odv2-title-row">
    <div>
        <h2>📋 Monitor de Ejecución Orion</h2>
        <p>Vista separada para validar formato visual antes de reemplazar la pantalla actual.</p>
    </div>

    <div class="odv2-status-pill" id="odv2-global-status">Sin verificar</div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_metrics_panel.html": r'''
<div class="odv2-card odv2-collapsible" data-collapse-key="metrics-panel">
    <button class="odv2-card-head" type="button">
        <span>📊 Panel estadístico</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-metrics-message" class="odv2-warning">
            El panel estadístico no se carga automáticamente. Presione “Ejecutar panel estadístico”.
        </div>
        <div class="odv2-metrics" id="odv2-metrics"></div>
        <div class="odv2-bars" id="odv2-bars"></div>
    </div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_connections_panel.html": r'''
<div class="odv2-card odv2-collapsible" data-collapse-key="connections-panel">
    <button class="odv2-card-head" type="button">
        <span>🔌 Información de origen / destino / BD / tabla</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-connections" class="odv2-empty">
            Ejecute el panel estadístico para ver información de conexión.
        </div>
    </div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_phase_board.html": r'''
<div class="odv2-card odv2-collapsible" data-collapse-key="phase-board">
    <button class="odv2-card-head" type="button">
        <span>🚦 Fases Gestión Diaria Orion</span>
        <b class="odv2-collapse-icon">▾</b>
    </button>
    <div class="odv2-card-body">
        <div id="odv2-phase-board" class="odv2-empty">Cargue contexto para ver fases.</div>
    </div>
</div>
''',

    "app/templates/orion_diario_v2/partials/_paths_modal.html": r'''
<div class="odv2-modal" id="odv2-paths-modal">
    <div class="odv2-modal-box">
        <div class="odv2-modal-head">
            <h3>Modificar rutas base ORION</h3>
            <button id="odv2-close-modal">×</button>
        </div>

        <p>
            Estas rutas se guardan en el navegador para pruebas de interfaz. 
            Luego se puede persistir en archivo de configuración si lo validamos.
        </p>

        <div id="odv2-paths-form"></div>

        <div class="odv2-modal-actions">
            <button id="odv2-save-paths" class="odv2-primary">Guardar rutas</button>
            <button id="odv2-reset-paths" class="odv2-secondary">Restaurar predeterminadas</button>
        </div>
    </div>
</div>
''',

    "app/static/css/orion_diario_v2.css": r'''
:root {
    --bg: #080b10;
    --panel: #111827;
    --panel-2: #172235;
    --border: #263752;
    --blue: #0ea5ff;
    --cyan: #00d5ff;
    --green: #22c55e;
    --yellow: #f59e0b;
    --red: #ef4444;
    --text: #eef6ff;
    --muted: #94a3b8;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Inter, Segoe UI, Arial, sans-serif;
}

.odv2-header {
    min-height: 84px;
    background: #111;
    border-bottom: 1px solid #222;
    padding: 12px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
}

.odv2-brand { display: flex; align-items: center; gap: 14px; }
.odv2-logo { font-size: 30px; }
.odv2-brand h1 { margin: 0; font-size: 26px; letter-spacing: .5px; }
.odv2-brand p { margin: 3px 0 0; color: var(--muted); font-size: 13px; }

.odv2-tabs { display: flex; gap: 8px; }
.odv2-tab {
    color: var(--text);
    text-decoration: none;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px 16px;
    background: #161616;
}
.odv2-tab.active { border-color: var(--blue); color: var(--blue); background: #071323; }
.odv2-tab.disabled { opacity: .45; cursor: not-allowed; }

.odv2-shell { padding: 18px; }

.odv2-context {
    max-width: 1680px;
    margin: 0 auto 18px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px 18px;
    display: grid;
    grid-template-columns: 1fr 1fr 2fr auto;
    gap: 16px;
    align-items: end;
}

.odv2-field label {
    display: block;
    font-size: 12px;
    color: var(--muted);
    font-weight: 800;
    margin-bottom: 7px;
}

.odv2-field input {
    width: 100%;
    background: #0b1222;
    border: 1px solid #334155;
    color: var(--text);
    border-radius: 10px;
    padding: 11px 12px;
    font-weight: 700;
}

.odv2-buttons, .odv2-actions, .odv2-modal-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.odv2-btn, .odv2-primary, .odv2-secondary {
    border-radius: 10px;
    padding: 11px 15px;
    color: white;
    font-weight: 800;
    cursor: pointer;
}

.odv2-btn {
    border: 0;
    background: #263244;
}

.odv2-btn.active { background: #2563eb; }

.odv2-primary {
    border: 0;
    background: linear-gradient(90deg, #2563eb, #0ea5e9);
}

.odv2-secondary {
    background: #1f2937;
    border: 1px solid #334155;
}

.odv2-secondary.full {
    width: 100%;
    margin-top: 10px;
}

.odv2-layout {
    max-width: 1680px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 18px;
}

.odv2-sidebar, .odv2-main {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.odv2-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 18px 40px rgba(0,0,0,.25);
}

.odv2-card-head {
    width: 100%;
    border: 0;
    background: linear-gradient(90deg, #13233c, #0f3049);
    color: var(--text);
    padding: 14px 16px;
    text-align: left;
    font-weight: 900;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.odv2-card-body {
    padding: 16px;
}

.odv2-collapsed .odv2-card-body {
    display: none;
}

.odv2-collapsed .odv2-collapse-icon {
    transform: rotate(-90deg);
}

.odv2-title-row {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px 20px;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
}

.odv2-title-row h2 {
    margin: 0;
    color: var(--blue);
    font-size: 30px;
}

.odv2-title-row p {
    margin: 8px 0 0;
    color: var(--muted);
}

.odv2-status-pill {
    border: 1px solid #334155;
    background: #0b1222;
    border-radius: 999px;
    padding: 9px 14px;
    font-weight: 900;
}

.odv2-status-pill.ok {
    color: var(--green);
    border-color: rgba(34,197,94,.5);
}

.odv2-warning {
    background: #2c2108;
    border: 1px solid rgba(245,158,11,.4);
    color: #facc15;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 14px;
}

.odv2-empty {
    color: var(--muted);
    padding: 10px;
    border: 1px dashed #334155;
    border-radius: 12px;
}

.odv2-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 16px;
}

.odv2-metric {
    background: linear-gradient(135deg, #13233c, #0c1627);
    border: 1px solid #26415e;
    border-radius: 16px;
    padding: 16px;
}

.odv2-metric small {
    color: var(--muted);
    font-weight: 800;
}

.odv2-metric strong {
    display: block;
    margin-top: 8px;
    font-size: 28px;
}

.odv2-metric span {
    display: block;
    margin-top: 6px;
    color: var(--muted);
    font-size: 12px;
}

.odv2-bars {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.odv2-bar-row label {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
    font-weight: 800;
    margin-bottom: 6px;
}

.odv2-bar-track {
    height: 13px;
    background: #020617;
    border-radius: 999px;
    overflow: hidden;
}

.odv2-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #06b6d4, #22c55e);
    min-width: 3px;
}

.odv2-phase-mini {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid #243755;
    background: #0b1222;
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 8px;
}

.odv2-phase-mini b {
    background: #1d4ed8;
    border-radius: 999px;
    padding: 5px 8px;
    margin-right: 8px;
}

.odv2-badge {
    color: var(--yellow);
    font-weight: 900;
    font-size: 12px;
}

.odv2-route {
    border: 1px solid #263752;
    border-radius: 10px;
    padding: 9px;
    margin-bottom: 7px;
    background: #0b1222;
    word-break: break-all;
}

.odv2-route small {
    color: var(--muted);
    display: block;
}

.odv2-phase {
    border: 1px solid #2b4463;
    border-radius: 14px;
    margin-bottom: 12px;
    overflow: hidden;
    background: #0b1222;
}

.odv2-phase-head {
    background: linear-gradient(90deg, #134b72, #0f778a);
    padding: 13px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 900;
}

.odv2-phase-body {
    padding: 14px 16px;
    color: var(--muted);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
    align-items: center;
}

.odv2-run {
    background: #16a34a;
    border: 0;
    border-radius: 10px;
    color: white;
    padding: 10px 14px;
    font-weight: 900;
    cursor: pointer;
}

.odv2-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.odv2-table th,
.odv2-table td {
    border-bottom: 1px solid #263752;
    padding: 10px;
    text-align: left;
    vertical-align: top;
}

.odv2-table th {
    color: var(--cyan);
    background: #0b1222;
}

.odv2-modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.65);
    align-items: center;
    justify-content: center;
    padding: 20px;
    z-index: 9999;
}

.odv2-modal.show { display: flex; }

.odv2-modal-box {
    max-width: 860px;
    width: 100%;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px;
}

.odv2-modal-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.odv2-modal-head button {
    background: var(--red);
    color: white;
    border: 0;
    border-radius: 8px;
    padding: 8px 11px;
    font-weight: 900;
    cursor: pointer;
}

@media (max-width: 1200px) {
    .odv2-context,
    .odv2-layout,
    .odv2-metrics {
        grid-template-columns: 1fr;
    }
}
''',

    "app/static/js/orion_diario_v2.js": r'''
(function () {
    "use strict";

    const DEFAULT_STATE = {
        conexion: "local",
        fechaProceso: "20260429",
        mesGestion: "abril",
        rutasBase: [],
        contexto: null,
        estadisticas: null
    };

    const state = loadState();

    const $ = (selector) => document.querySelector(selector);

    function loadState() {
        try {
            return { ...DEFAULT_STATE, ...JSON.parse(localStorage.getItem("orion_diario_v2_state") || "{}") };
        } catch {
            return { ...DEFAULT_STATE };
        }
    }

    function saveState() {
        localStorage.setItem("orion_diario_v2_state", JSON.stringify(state));
    }

    function fmt(value) {
        if (value === null || value === undefined || value === "") return "--";
        if (typeof value === "number") return value.toLocaleString("es-BO");

        const n = Number(value);
        if (!Number.isNaN(n) && String(value).trim() !== "") {
            return n.toLocaleString("es-BO");
        }

        return value;
    }

    function collectInputs() {
        state.fechaProceso = $("#odv2-fecha-proceso").value.trim();
        state.mesGestion = $("#odv2-mes-gestion").value.trim();
        saveState();
    }

    function getParams(includeRoutes) {
        collectInputs();

        const params = new URLSearchParams({
            fecha_proceso: state.fechaProceso,
            mes_gestion: state.mesGestion,
            conexion: state.conexion
        });

        if (includeRoutes && state.rutasBase.length) {
            state.rutasBase.forEach(r => params.append("rutas_base", r));
        }

        return params;
    }

    function setActiveConnection() {
        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.conn === state.conexion);
        });
    }

    function restoreInputs() {
        $("#odv2-fecha-proceso").value = state.fechaProceso;
        $("#odv2-mes-gestion").value = state.mesGestion;
        setActiveConnection();
    }

    async function loadContext() {
        const res = await fetch("/api/orion-diario-v2/contexto?" + getParams(true).toString());
        state.contexto = await res.json();
        state.estadisticas = null;
        saveState();
        renderContext();
        clearStats();
    }

    async function loadStats() {
        const res = await fetch("/api/orion-diario-v2/estadisticas?" + getParams(true).toString());
        state.estadisticas = await res.json();
        state.contexto = state.estadisticas;
        saveState();
        renderContext();
        renderStats();
    }

    function renderContext() {
        const data = state.contexto;
        if (!data) return;

        $("#odv2-global-status").textContent = data.conexion === "local" ? "Local activo" : "Remoto activo";
        $("#odv2-global-status").classList.add("ok");

        $("#odv2-fecha-proceso").value = data.fecha_proceso || state.fechaProceso;
        $("#odv2-mes-gestion").value = data.mes_gestion || state.mesGestion;

        state.fechaProceso = $("#odv2-fecha-proceso").value;
        state.mesGestion = $("#odv2-mes-gestion").value;

        if (!state.rutasBase.length && Array.isArray(data.rutas_red)) {
            state.rutasBase = data.rutas_red.map(r => r.base);
        }

        renderSidebar(data);
        renderRoutes(data);
        renderLocalServers(data);
        renderPhaseBoard(data);
    }

    function clearStats() {
        $("#odv2-metrics-message").style.display = "block";
        $("#odv2-metrics").innerHTML = "";
        $("#odv2-bars").innerHTML = "";
        $("#odv2-connections").innerHTML = '<div class="odv2-empty">Ejecute el panel estadístico para ver información de conexión.</div>';
    }

    function renderStats() {
        const data = state.estadisticas;
        if (!data) return;

        $("#odv2-metrics-message").style.display = "none";
        renderMetrics(data);
        renderBars(data);
        renderConnections(data);
    }

    function renderSidebar(data) {
        const root = $("#odv2-sidebar-phases");
        root.innerHTML = "";

        data.fases.forEach(f => {
            const div = document.createElement("div");
            div.className = "odv2-phase-mini";
            div.innerHTML = `
                <span><b>${f.codigo}</b>${f.nombre}</span>
                <span class="odv2-badge">${f.badge}</span>
            `;
            root.appendChild(div);
        });
    }

    function renderRoutes(data) {
        const root = $("#odv2-routes");
        root.innerHTML = "";

        data.rutas_red.forEach(r => {
            const div = document.createElement("div");
            div.className = "odv2-route";
            div.innerHTML = `
                <small>${r.nombre}</small>
                <strong>Base:</strong> ${r.base}<br>
                <strong>Mes gestión:</strong> ${r.ruta_mes}
            `;
            root.appendChild(div);
        });

        if (data.rutas_locales) {
            Object.entries(data.rutas_locales).forEach(([k, v]) => {
                const div = document.createElement("div");
                div.className = "odv2-route";
                div.innerHTML = `<small>${k}</small>${v}`;
                root.appendChild(div);
            });
        }

        renderPathsForm();
    }

    function renderLocalServers(data) {
        const root = $("#odv2-local-servers");

        if (!data.servidores_locales || !data.servidores_locales.length) {
            root.innerHTML = '<div class="odv2-empty">Esta información solo se muestra para conexión LOCAL.</div>';
            return;
        }

        root.innerHTML = `
            <table class="odv2-table">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Servidor</th>
                        <th>BD</th>
                        <th>Uso</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.servidores_locales.map(s => `
                        <tr>
                            <td>${s.tipo}</td>
                            <td>${s.servidor}</td>
                            <td>${s.base_datos || "--"}</td>
                            <td>${s.uso || "--"}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPhaseBoard(data) {
        const root = $("#odv2-phase-board");
        root.innerHTML = "";

        data.fases.forEach(f => {
            const item = document.createElement("div");
            item.className = "odv2-phase";
            item.innerHTML = `
                <div class="odv2-phase-head">
                    <span>${f.codigo} — ${f.nombre}</span>
                    <span>${f.badge}</span>
                </div>
                <div class="odv2-phase-body">
                    <div>
                        <strong>${f.grupo}</strong><br>
                        ${f.descripcion}
                    </div>
                    <button class="odv2-run" data-phase="${f.codigo}" data-action="${f.accion}">Ejecutar fase</button>
                </div>
            `;
            root.appendChild(item);
        });

        root.querySelectorAll(".odv2-run").forEach(btn => {
            btn.addEventListener("click", () => {
                alert("Fase " + btn.dataset.phase + " todavía no vinculada en v2. La pantalla actual sigue funcionando.");
            });
        });
    }

    function renderMetrics(data) {
        const root = $("#odv2-metrics");
        root.innerHTML = "";

        data.metricas.forEach(m => {
            const card = document.createElement("div");
            card.className = "odv2-metric";
            card.innerHTML = `
                <small>${m.titulo}</small>
                <strong>${fmt(m.valor)}</strong>
                <span>${m.detalle || ""}</span>
            `;
            root.appendChild(card);
        });
    }

    function renderBars(data) {
        const root = $("#odv2-bars");
        root.innerHTML = "";

        const values = data.metricas
            .map(x => Number(x.valor || 0))
            .filter(x => !Number.isNaN(x));

        const max = Math.max(...values, 1);

        data.metricas.forEach(m => {
            const value = Number(m.valor || 0);
            const pct = Math.max(3, Math.round((value / max) * 100));

            const row = document.createElement("div");
            row.className = "odv2-bar-row";
            row.innerHTML = `
                <label><span>${m.titulo}</span><span>${fmt(m.valor)}</span></label>
                <div class="odv2-bar-track">
                    <div class="odv2-bar-fill" style="width:${pct}%"></div>
                </div>
            `;
            root.appendChild(row);
        });
    }

    function renderConnections(data) {
        const root = $("#odv2-connections");

        root.innerHTML = `
            <table class="odv2-table">
                <thead>
                    <tr>
                        <th>Proceso</th>
                        <th>Origen</th>
                        <th>Destino</th>
                        <th>Servidor</th>
                        <th>BD</th>
                        <th>Tabla</th>
                        <th>Ruta</th>
                        <th>Total</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.conexiones.map(c => `
                        <tr>
                            <td>${c.proceso}</td>
                            <td>${c.origen}</td>
                            <td>${c.destino}</td>
                            <td>${c.servidor}</td>
                            <td>${c.base_datos}</td>
                            <td>${c.tabla}</td>
                            <td>${c.ruta}</td>
                            <td>${fmt(c.total)}</td>
                            <td>${c.estado}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPathsForm() {
        const root = $("#odv2-paths-form");
        root.innerHTML = "";

        const rutas = state.rutasBase.length ? state.rutasBase : [
            "\\\\10.24.90.118\\Vencorp\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
            "Z:\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
            "D:\\Develop\\ETL\\Nicaragua_Proceso\\unidad_red_orion\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion"
        ];

        rutas.forEach((ruta, idx) => {
            const div = document.createElement("div");
            div.className = "odv2-field";
            div.innerHTML = `
                <label>Ruta base ${idx + 1}</label>
                <input data-path-index="${idx}" value="${String(ruta).replaceAll('"', "&quot;")}">
            `;
            root.appendChild(div);
        });
    }

    function setupModal() {
        $("#odv2-edit-paths").addEventListener("click", () => {
            renderPathsForm();
            $("#odv2-paths-modal").classList.add("show");
        });

        $("#odv2-close-modal").addEventListener("click", () => {
            $("#odv2-paths-modal").classList.remove("show");
        });

        $("#odv2-save-paths").addEventListener("click", () => {
            state.rutasBase = Array.from(document.querySelectorAll("[data-path-index]"))
                .map(input => input.value.trim())
                .filter(Boolean);

            saveState();
            $("#odv2-paths-modal").classList.remove("show");
            loadContext();
        });

        $("#odv2-reset-paths").addEventListener("click", () => {
            state.rutasBase = [];
            saveState();
            renderPathsForm();
        });
    }

    function setupCollapsibles() {
        document.querySelectorAll(".odv2-collapsible").forEach(card => {
            const key = "orion_v2_collapse_" + card.dataset.collapseKey;
            const collapsed = localStorage.getItem(key) === "1";

            card.classList.toggle("odv2-collapsed", collapsed);

            const head = card.querySelector(".odv2-card-head");
            if (!head) return;

            head.addEventListener("click", () => {
                const isCollapsed = card.classList.toggle("odv2-collapsed");
                localStorage.setItem(key, isCollapsed ? "1" : "0");
            });
        });
    }

    function init() {
        restoreInputs();

        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.addEventListener("click", () => {
                state.conexion = btn.dataset.conn;
                saveState();
                setActiveConnection();
                loadContext();
            });
        });

        $("#odv2-load-context").addEventListener("click", loadContext);
        $("#odv2-load-stats").addEventListener("click", loadStats);

        setupModal();
        setupCollapsibles();

        if (state.contexto) {
            renderContext();
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
'''
}


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def backup(path: Path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def write_file(rel_path: str, content: str):
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        backup(path)

    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"OK: {rel_path}")


def patch_app_init():
    init_path = ROOT / "app" / "__init__.py"

    if not init_path.exists():
        print("AVISO: no existe app/__init__.py. Registra blueprint manualmente.")
        return

    text = init_path.read_text(encoding="utf-8", errors="ignore")

    if "orion_diario_v2_bp" in text:
        print("OK: orion_diario_v2_bp ya estaba registrado.")
        return

    marker = "    return app"

    if marker not in text:
        print("AVISO: no encontré '    return app'. No modifiqué app/__init__.py.")
        print("Agrega dentro de create_app():")
        print("    from app.controllers.orion_diario_v2_blueprint import orion_diario_v2_bp")
        print("    app.register_blueprint(orion_diario_v2_bp)")
        return

    backup(init_path)

    insert = (
        "    from app.controllers.orion_diario_v2_blueprint import orion_diario_v2_bp\n"
        "    app.register_blueprint(orion_diario_v2_bp)\n\n"
    )

    text = text.replace(marker, insert + marker, 1)
    init_path.write_text(text, encoding="utf-8")
    print("OK: app/__init__.py actualizado.")


def compile_files():
    title("COMPILACION")

    py_files = [
        ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py",
        ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py",
        ROOT / "app" / "__init__.py",
    ]

    subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in py_files if p.exists()]],
        check=True,
    )

    print("OK: archivos Python compilan.")


def main():
    title("SCAFFOLD GESTION DIARIA ORION V2")

    for rel, content in FILES.items():
        write_file(rel, content)

    patch_app_init()
    compile_files()

    title("FINALIZADO")
    print("Ejecuta:")
    print("  python run.py")
    print("")
    print("Abre:")
    print("  http://127.0.0.1:5000/orion-diario-v2")
    print("")
    print("Notas:")
    print("  - No reemplaza la pantalla actual.")
    print("  - El panel estadístico no carga automático.")
    print("  - Rutas y colapsables se guardan en localStorage.")


if __name__ == "__main__":
    main()