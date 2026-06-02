from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "app"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    if path.exists() and path.is_file():
        backup_path = path.with_suffix(path.suffix + f".bak_integral_v2_{STAMP}")
        shutil.copy2(path, backup_path)


def write_file(relative: str, content: str, make_backup: bool = True) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.strip("\n") + "\n"
    if path.exists() and path.read_text(encoding="utf-8", errors="ignore") == normalized:
        print(f"SIN CAMBIOS  {relative}")
        return
    if make_backup:
        backup(path)
    path.write_text(normalized, encoding="utf-8")
    print(f"ESCRITO      {relative}")


def patch_text_file(relative: str, patcher) -> None:
    path = ROOT / relative
    if not path.exists():
        print(f"OMITIDO      {relative} no existe")
        return
    old = path.read_text(encoding="utf-8", errors="ignore")
    new = patcher(old)
    if new == old:
        print(f"SIN CAMBIOS  {relative}")
        return
    backup(path)
    path.write_text(new, encoding="utf-8")
    print(f"MODIFICADO   {relative}")


def ensure_blueprint_registered() -> None:
    def patch(text: str) -> str:
        if "integral_diario_v2_blueprint" in text:
            return text

        marker = "    from app.controllers.aster_diario_v2_blueprint import aster_diario_v2_bp\n    app.register_blueprint(aster_diario_v2_bp)"
        addition = marker + "\n\n    from app.controllers.integral_diario_v2_blueprint import integral_diario_v2_bp\n    app.register_blueprint(integral_diario_v2_bp)"

        if marker in text:
            return text.replace(marker, addition)

        fallback = "    return app"
        if fallback in text:
            return text.replace(
                fallback,
                "    from app.controllers.integral_diario_v2_blueprint import integral_diario_v2_bp\n"
                "    app.register_blueprint(integral_diario_v2_bp)\n\n"
                "    return app"
            )

        return text + "\nfrom app.controllers.integral_diario_v2_blueprint import integral_diario_v2_bp\napp.register_blueprint(integral_diario_v2_bp)\n"

    patch_text_file("app/__init__.py", patch)


def patch_navs() -> None:
    def patch_orion_header(text: str) -> str:
        if "/integral-v2" in text:
            return text
        target = '<a class="odv2-tab" href="/consolidar-gestion-v2">Consolidar Gestión</a>'
        return text.replace(target, target + '\n        <a class="odv2-tab" href="/integral-v2">Integral</a>')

    patch_text_file("app/templates/orion_diario_v2/partials/_header.html", patch_orion_header)

    def patch_aster_index(text: str) -> str:
        if "/integral-v2" in text:
            return text
        target = '<a href="/consolidar-gestion-v2">Consolidar Gestión</a>'
        return text.replace(target, target + '\n            <a href="/integral-v2">Integral</a>')

    patch_text_file("app/templates/aster_diario_v2/index.html", patch_aster_index)

    def patch_consolidar(text: str) -> str:
        if "/integral-v2" in text:
            return text
        target = '<a class="gc-module-tab active" href="/consolidar-gestion-v2">Consolidar Gestión</a>'
        return text.replace(target, target + '\n                <a class="gc-module-tab" href="/integral-v2">Integral</a>')

    patch_text_file("app/templates/gestion_consolidada.html", patch_consolidar)


def patch_config_default() -> None:
    """Agrega integral_api al default central. Si instance/orion_aster_config.json existe, también lo completa."""
    def patch_service(text: str) -> str:
        if '"integral_api"' in text:
            return text

        local_target = '''                "gestion_consolidada": {
                    "server": r"localhost\\SQL2025DEV",
                    "port": "",
                    "database": "Vencorp_V2",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },'''
        local_add = local_target + '''
                "integral_api": {
                    "server": r"localhost\\SQL2025DEV",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                },'''

        remote_target = '''                "gestion_consolidada": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Vencorp_V2",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },'''
        remote_add = remote_target + '''
                "integral_api": {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                },'''

        text = text.replace(local_target, local_add)
        text = text.replace(remote_target, remote_add)
        return text

    patch_text_file("app/services/orion_aster_config_service.py", patch_service)

    cfg_path = ROOT / "instance" / "orion_aster_config.json"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            changed = False
            sql = data.setdefault("sql", {})
            local = sql.setdefault("local", {})
            remoto = sql.setdefault("remoto", {})

            if "integral_api" not in local:
                local["integral_api"] = {
                    "server": r"localhost\SQL2025DEV",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "1234",
                }
                changed = True

            if "integral_api" not in remoto:
                remoto["integral_api"] = {
                    "server": "VC-EIDER",
                    "alt_server": "172.24.80.32",
                    "port": "",
                    "database": "Aster_Integral_Api",
                    "auth": "sql",
                    "username": "Admin1",
                    "password": "",
                }
                changed = True

            if changed:
                backup(cfg_path)
                cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                print("MODIFICADO   instance/orion_aster_config.json")
            else:
                print("SIN CAMBIOS  instance/orion_aster_config.json")
        except Exception as exc:
            print(f"ADVERTENCIA  no se pudo actualizar instance/orion_aster_config.json: {exc}")


# ---------------------------------------------------------------------
# Archivos Python MVC/OOP
# ---------------------------------------------------------------------

write_file("app/models/integral_v2_models.py", r'''
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IntegralV2Params:
    conexion: str
    fecha: str
    entidad: str

    def validar(self) -> None:
        if self.conexion not in {"local", "remoto"}:
            raise ValueError("La conexión debe ser 'local' o 'remoto'.")

        if not str(self.fecha or "").strip():
            raise ValueError("Debe indicar la fecha del proceso Integral.")

        if not str(self.entidad or "").strip():
            raise ValueError("Debe indicar la entidad del proceso Integral.")

        self.fecha_sql()

    def fecha_sql(self) -> str:
        raw = str(self.fecha or "").strip()
        limpio = re.sub(r"[^0-9]", "", raw)

        if len(limpio) == 8:
            return datetime.strptime(limpio, "%Y%m%d").strftime("%Y-%m-%d")

        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")

        raise ValueError("Fecha inválida. Use formato YYYYMMDD o YYYY-MM-DD.")
''')

write_file("app/services/integral_v2_connection_service.py", r'''
from __future__ import annotations

import os
from typing import Any

import pyodbc

from app.controllers.helpers import construir_cadena_conexion
from app.services.aster_phase_i_prepare_service import conectar_mysql_fase_i
from app.services.orion_aster_config_service import get_sql_config_legacy, normalizar_conexion


class IntegralV2ConnectionFactory:
    """
    Fábrica de conexiones para Integral v2.

    LOCAL:
    - Origen: SQL Server gestioncomercial_dev.
    - Destino: SQL Server Aster_Integral_Api.

    REMOTO:
    - Origen: MySQL usuarios / gestioncomercial usando variables ASTER_DB_*.
    - Destino: SQL Server Aster_Integral_Api.
    """

    def __init__(self, conexion: str):
        self.conexion = normalizar_conexion(conexion)

    def cfg_origen_sqlserver_local(self) -> dict[str, Any]:
        return get_sql_config_legacy("local", "gestioncomercial")

    def cfg_destino_sqlserver(self) -> dict[str, Any]:
        cfg = get_sql_config_legacy(self.conexion, "integral_api")

        if not cfg.get("database"):
            cfg = get_sql_config_legacy(self.conexion, "aster_api")

        cfg = dict(cfg)
        default_database = os.getenv(
            "INTEGRAL_SQL_LOCAL_DATABASE" if self.conexion == "local" else "INTEGRAL_SQL_REMOTO_DATABASE",
            "Aster_Integral_Api",
        )
        cfg["database"] = cfg.get("database") or default_database

        return cfg

    def abrir_origen_usuarios(self):
        if self.conexion == "remoto":
            return conectar_mysql_fase_i(os.getenv("INTEGRAL_MYSQL_DB_USUARIOS", "usuarios"))

        cfg = self.cfg_origen_sqlserver_local()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def abrir_origen_comentarios(self):
        if self.conexion == "remoto":
            return conectar_mysql_fase_i(os.getenv("INTEGRAL_MYSQL_DB_GESTION", "gestioncomercial"))

        cfg = self.cfg_origen_sqlserver_local()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def abrir_destino(self):
        cfg = self.cfg_destino_sqlserver()
        return pyodbc.connect(construir_cadena_conexion(cfg), timeout=8)

    def modo_origen(self) -> str:
        return "remoto_mysql" if self.conexion == "remoto" else "local_sqlserver"
''')

write_file("app/repositories/integral_v2_source_repository.py", r'''
from __future__ import annotations

from typing import Any

from app.services.sql_loader import cargar_sql


class IntegralV2SourceRepository:
    """
    Repositorio de origen para Integral v2.
    No contiene SQL duro: todo se carga desde app/sql/integral/v2.
    """

    def __init__(self, conexion: str, usuarios_conn, comentarios_conn):
        self.conexion = str(conexion or "local").strip().lower()
        self.usuarios_conn = usuarios_conn
        self.comentarios_conn = comentarios_conn

    @property
    def es_remoto_mysql(self) -> bool:
        return self.conexion == "remoto"

    def _total_from_row(self, row: Any) -> int:
        if row is None:
            return 0

        if isinstance(row, dict):
            return int(row.get("total") or 0)

        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        ruta = (
            "integral/v2/mysql/count_usuarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/count_usuarios.sql"
        )
        sql = cargar_sql(ruta)

        with self.usuarios_conn.cursor() as cursor:
            cursor.execute(sql)
            return self._total_from_row(cursor.fetchone())

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        ruta = (
            "integral/v2/mysql/count_comentarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/count_comentarios.sql"
        )
        sql = cargar_sql(ruta)

        with self.comentarios_conn.cursor() as cursor:
            cursor.execute(sql, (fecha_sql, entidad))
            return self._total_from_row(cursor.fetchone())
''')

write_file("app/repositories/integral_v2_destination_repository.py", r'''
from __future__ import annotations

from typing import Any

from app.services.sql_loader import cargar_sql


class IntegralV2DestinationRepository:
    """
    Repositorio de destino para Integral v2.
    Destino esperado: Aster_Integral_Api.Integral.usuarios / comentarios.
    """

    def __init__(self, sqlserver_conn):
        self.sqlserver_conn = sqlserver_conn

    def _total_from_row(self, row: Any) -> int:
        if row is None:
            return 0
        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_usuarios.sql")

        with self.sqlserver_conn.cursor() as cursor:
            cursor.execute(sql)
            return self._total_from_row(cursor.fetchone())

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_comentarios.sql")

        with self.sqlserver_conn.cursor() as cursor:
            cursor.execute(sql, (fecha_sql, entidad))
            return self._total_from_row(cursor.fetchone())
''')

write_file("app/services/integral_v2_validation_service.py", r'''
from __future__ import annotations

from app.models.integral_v2_models import IntegralV2Params
from app.repositories.integral_v2_destination_repository import IntegralV2DestinationRepository
from app.repositories.integral_v2_source_repository import IntegralV2SourceRepository
from app.services.integral_v2_connection_service import IntegralV2ConnectionFactory


class IntegralV2ValidationService:
    """
    Servicio de validación Integral v2.
    No conoce Flask y no renderiza HTML.
    """

    def validar_conteos(self, params: IntegralV2Params) -> dict:
        params.validar()
        fecha_sql = params.fecha_sql()

        factory = IntegralV2ConnectionFactory(params.conexion)

        usuarios_conn = None
        comentarios_conn = None
        destino_conn = None

        try:
            usuarios_conn = factory.abrir_origen_usuarios()
            comentarios_conn = factory.abrir_origen_comentarios()
            destino_conn = factory.abrir_destino()

            source_repo = IntegralV2SourceRepository(
                conexion=params.conexion,
                usuarios_conn=usuarios_conn,
                comentarios_conn=comentarios_conn,
            )
            destination_repo = IntegralV2DestinationRepository(destino_conn)

            usuarios_origen = source_repo.contar_usuarios()
            comentarios_origen = source_repo.contar_comentarios(fecha_sql, params.entidad)
            usuarios_destino = destination_repo.contar_usuarios()
            comentarios_destino = destination_repo.contar_comentarios(fecha_sql, params.entidad)

            return {
                "ok": True,
                "conexion": params.conexion,
                "modo_origen": factory.modo_origen(),
                "fecha": params.fecha,
                "fecha_sql": fecha_sql,
                "entidad": params.entidad,
                "usuarios": {
                    "origen": usuarios_origen,
                    "destino": usuarios_destino,
                    "coincide": usuarios_origen == usuarios_destino,
                },
                "comentarios": {
                    "origen": comentarios_origen,
                    "destino": comentarios_destino,
                    "coincide": comentarios_origen == comentarios_destino,
                },
                "destino_database": factory.cfg_destino_sqlserver().get("database", ""),
            }

        finally:
            for conn in (usuarios_conn, comentarios_conn, destino_conn):
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
''')

write_file("app/controllers/integral_diario_v2_controller.py", r'''
from __future__ import annotations

from flask import render_template, request

from app.models.integral_v2_models import IntegralV2Params
from app.services.integral_v2_validation_service import IntegralV2ValidationService


class IntegralDiarioV2Controller:
    """
    Controller del módulo Integral v2.
    Recibe request, llama servicios y devuelve HTML renderizado por Jinja.
    """

    @staticmethod
    def index():
        return render_template("integral_v2/index.html")

    @staticmethod
    def validar():
        try:
            params = IntegralV2Params(
                conexion=(request.form.get("conexion") or "local").strip().lower(),
                fecha=(request.form.get("fecha") or "").strip(),
                entidad=(request.form.get("entidad") or "").strip(),
            )

            resultado = IntegralV2ValidationService().validar_conteos(params)

            return render_template(
                "integral_v2/partials/_resultado_validacion.html",
                resultado=resultado,
            )

        except Exception as exc:
            return render_template(
                "integral_v2/partials/_error.html",
                mensaje=str(exc),
            ), 500
''')

write_file("app/controllers/integral_diario_v2_blueprint.py", r'''
from __future__ import annotations

from flask import Blueprint

from app.controllers.integral_diario_v2_controller import IntegralDiarioV2Controller


integral_diario_v2_bp = Blueprint("integral_diario_v2", __name__)


@integral_diario_v2_bp.get("/integral-v2")
@integral_diario_v2_bp.get("/integral-diario-v2")
def vista_integral_v2():
    return IntegralDiarioV2Controller.index()


@integral_diario_v2_bp.post("/accion/integral-v2/validar")
def accion_integral_v2_validar():
    return IntegralDiarioV2Controller.validar()
''')

# Compatibilidad: neutraliza el /integral viejo que importaba app.database inexistente.
write_file("app/routes/integral_routes.py", r'''
from __future__ import annotations

from flask import Blueprint, redirect


integral_bp = Blueprint("integral", __name__, url_prefix="/integral")


@integral_bp.get("/")
def index():
    return redirect("/integral-v2")


@integral_bp.get("/panel")
def panel():
    return redirect("/integral-v2")


@integral_bp.post("/validar")
def validar():
    return redirect("/integral-v2")
''')

write_file("app/controllers/integral_controller.py", r'''
from __future__ import annotations

from flask import redirect


class IntegralController:
    """Compatibilidad con el módulo Integral anterior."""

    @staticmethod
    def index():
        return redirect("/integral-v2")

    @staticmethod
    def panel():
        return redirect("/integral-v2")

    @staticmethod
    def validar():
        return redirect("/integral-v2")
''')

# ---------------------------------------------------------------------
# SQL externos
# ---------------------------------------------------------------------

write_file("app/sql/integral/v2/mysql/count_usuarios.sql", r'''
SELECT COUNT(*) AS total
FROM crm;
''')

write_file("app/sql/integral/v2/mysql/count_comentarios.sql", r'''
SELECT COUNT(*) AS total
FROM comentarios
WHERE DATE(fecha) = %s
  AND entidad = %s;
''')

write_file("app/sql/integral/v2/mysql/probar_conexion.sql", r'''
SELECT 1 AS ok;
''')

write_file("app/sql/integral/v2/sqlserver_origen/count_usuarios.sql", r'''
SELECT COUNT(1) AS total
FROM dbo.usuarios;
''')

write_file("app/sql/integral/v2/sqlserver_origen/count_comentarios.sql", r'''
SELECT COUNT(1) AS total
FROM dbo.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
''')

write_file("app/sql/integral/v2/sqlserver_origen/probar_conexion.sql", r'''
SELECT DB_NAME() AS database_actual;
''')

write_file("app/sql/integral/v2/sqlserver_destino/count_usuarios.sql", r'''
SELECT COUNT(1) AS total
FROM Integral.usuarios;
''')

write_file("app/sql/integral/v2/sqlserver_destino/count_comentarios.sql", r'''
SELECT COUNT(1) AS total
FROM Integral.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
''')

write_file("app/sql/integral/v2/sqlserver_destino/delete_usuarios.sql", r'''
DELETE FROM Integral.usuarios;
''')

write_file("app/sql/integral/v2/sqlserver_destino/delete_comentarios.sql", r'''
DELETE FROM Integral.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
''')

# ---------------------------------------------------------------------
# Templates Jinja
# ---------------------------------------------------------------------

write_file("app/templates/integral_v2/index.html", r'''
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Integral v2</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/orion_diario_v2.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/integral_v2.css') }}">
</head>
<body class="integral-v2-body">
    <header class="integral-v2-topbar">
        <div>
            <h1>⚙ Orion Procesos</h1>
            <p>Integral v2 — pipeline MVC/OOP con SQL externo y HTML renderizado por Flask/Jinja</p>
        </div>

        <nav class="integral-v2-nav">
            <a href="/orion-diario-v2">Gestión Diaria Orion</a>
            <a href="/aster-diario-v2">Gestión Diaria ASTER</a>
            <a href="/consolidar-gestion-v2">Consolidar Gestión</a>
            <a class="active" href="/integral-v2">Integral</a>
        </nav>
    </header>

    <main class="integral-v2-layout">
        <aside class="integral-v2-sidebar">
            {% include "integral_v2/partials/_estado.html" %}
            {% include "integral_v2/partials/_reglas.html" %}
        </aside>

        <section class="integral-v2-main">
            <section class="integral-v2-hero">
                <div>
                    <h2>Proceso Integral</h2>
                    <p>
                        Validación inicial de usuarios y comentarios para preparar la migración del proceso SSIS a pipeline Python.
                    </p>
                </div>
                <span class="integral-v2-badge">V2 MVC/OOP</span>
            </section>

            {% include "integral_v2/partials/_panel_validacion.html" %}

            <section class="integral-v2-card">
                <h3>Resultado</h3>
                <div id="integral-v2-resultado" class="integral-v2-result-block">
                    {% include "integral_v2/partials/_sin_resultado.html" %}
                </div>
            </section>
        </section>
    </main>

    <template id="integral-v2-loading-template">
        {% include "integral_v2/partials/_loading.html" %}
    </template>

    <template id="integral-v2-error-comunicacion-template">
        {% include "integral_v2/partials/_error_comunicacion.html" %}
    </template>

    <script src="{{ url_for('static', filename='js/integral_diario_v2.js') }}"></script>
</body>
</html>
''')

write_file("app/templates/integral_v2/partials/_estado.html", r'''
<section class="integral-v2-card">
    <h3>🎯 Estado Integral</h3>
    <div class="integral-v2-muted">
        Módulo preparado para conexión local/remota y validación de origen/destino.
    </div>
</section>
''')

write_file("app/templates/integral_v2/partials/_reglas.html", r'''
<section class="integral-v2-card">
    <h3>📐 Reglas técnicas</h3>
    <ul class="integral-v2-rule-list">
        <li>JavaScript solo envía datos y coloca HTML.</li>
        <li>Flask/Jinja renderiza cards, tablas y resultados.</li>
        <li>SQL externo en <code>app/sql/integral/v2</code>.</li>
        <li>Servicios y repositorios separados.</li>
    </ul>
</section>
''')

write_file("app/templates/integral_v2/partials/_panel_validacion.html", r'''
<section class="integral-v2-card">
    <div class="integral-v2-section-header">
        <h3>Validación inicial Integral</h3>
        <p>Compara conteos de usuarios y comentarios entre origen y destino.</p>
    </div>

    <form id="integral-v2-validar-form" action="/accion/integral-v2/validar" method="post" class="integral-v2-form">
        <label>
            Conexión
            <select name="conexion" id="integral-v2-conexion">
                <option value="local" selected>LOCAL - Pruebas</option>
                <option value="remoto">REMOTO - Producción</option>
            </select>
        </label>

        <label>
            Fecha proceso
            <input name="fecha" id="integral-v2-fecha" type="text" value="20260518" placeholder="YYYYMMDD o YYYY-MM-DD">
        </label>

        <label>
            Entidad
            <input name="entidad" id="integral-v2-entidad" type="text" value="Manual_Base_Churn_18052026" placeholder="Manual_Base_Churn_18052026">
        </label>

        <button type="submit" class="integral-v2-btn primary">
            Validar conteos Integral
        </button>
    </form>
</section>
''')

write_file("app/templates/integral_v2/partials/_resultado_validacion.html", r'''
<div class="integral-v2-result-card">
    <div class="integral-v2-result-header">
        <div>
            <h4>Resultado de validación Integral</h4>
            <p>
                Conexión: <strong>{{ resultado.conexion|upper }}</strong> ·
                Origen: <strong>{{ resultado.modo_origen }}</strong> ·
                Fecha SQL: <strong>{{ resultado.fecha_sql }}</strong> ·
                Entidad: <strong>{{ resultado.entidad }}</strong>
            </p>
        </div>
        <span class="integral-v2-badge">{{ resultado.destino_database }}</span>
    </div>

    <table class="integral-v2-table">
        <thead>
            <tr>
                <th>Proceso</th>
                <th>Origen</th>
                <th>Destino</th>
                <th>Estado</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Usuarios CRM</td>
                <td>{{ resultado.usuarios.origen }}</td>
                <td>{{ resultado.usuarios.destino }}</td>
                <td>
                    {% if resultado.usuarios.coincide %}
                        <span class="integral-v2-chip ok">Coincide</span>
                    {% else %}
                        <span class="integral-v2-chip warn">No coincide</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Comentarios</td>
                <td>{{ resultado.comentarios.origen }}</td>
                <td>{{ resultado.comentarios.destino }}</td>
                <td>
                    {% if resultado.comentarios.coincide %}
                        <span class="integral-v2-chip ok">Coincide</span>
                    {% else %}
                        <span class="integral-v2-chip warn">No coincide</span>
                    {% endif %}
                </td>
            </tr>
        </tbody>
    </table>

    <div class="integral-v2-note">
        Esta fase solo valida conteos. La carga real se implementará después como pipeline por fases.
    </div>
</div>
''')

write_file("app/templates/integral_v2/partials/_sin_resultado.html", r'''
<div class="integral-v2-log warning">⚠️ Sin resultados. Ejecute la validación inicial.</div>
''')

write_file("app/templates/integral_v2/partials/_loading.html", r'''
<div class="integral-v2-log info">⏳ Ejecutando validación Integral...</div>
''')

write_file("app/templates/integral_v2/partials/_error.html", r'''
<div class="integral-v2-log error">
    ❌ Error en Integral:<br>
    <strong>{{ mensaje }}</strong>
</div>
''')

write_file("app/templates/integral_v2/partials/_error_comunicacion.html", r'''
<div class="integral-v2-log error">
    ❌ Error de comunicación con el servidor.
</div>
''')

# ---------------------------------------------------------------------
# CSS / JS
# ---------------------------------------------------------------------

write_file("app/static/css/integral_v2.css", r'''
.integral-v2-body {
    margin: 0;
    background: #07111f;
    color: #e8eef7;
    font-family: Arial, Helvetica, sans-serif;
}

.integral-v2-topbar {
    display: flex;
    justify-content: space-between;
    gap: 24px;
    align-items: center;
    padding: 18px 28px;
    background: linear-gradient(135deg, #07111f, #10253f);
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.integral-v2-topbar h1,
.integral-v2-topbar p {
    margin: 0;
}

.integral-v2-topbar p {
    margin-top: 4px;
    color: #9fb0c6;
}

.integral-v2-nav {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.integral-v2-nav a {
    color: #d7e4f7;
    text-decoration: none;
    padding: 10px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
}

.integral-v2-nav a.active,
.integral-v2-nav a:hover {
    background: #2d6cdf;
    color: #fff;
}

.integral-v2-layout {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 18px;
    padding: 22px;
}

.integral-v2-sidebar,
.integral-v2-main {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.integral-v2-card,
.integral-v2-hero,
.integral-v2-result-card {
    background: rgba(14, 30, 52, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
}

.integral-v2-hero,
.integral-v2-result-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
}

.integral-v2-hero h2,
.integral-v2-card h3,
.integral-v2-result-card h4 {
    margin-top: 0;
}

.integral-v2-muted,
.integral-v2-card p,
.integral-v2-result-header p,
.integral-v2-note {
    color: #9fb0c6;
}

.integral-v2-rule-list {
    padding-left: 18px;
    line-height: 1.7;
    color: #cdd9ea;
}

.integral-v2-form {
    display: grid;
    grid-template-columns: repeat(4, minmax(160px, 1fr));
    gap: 14px;
    align-items: end;
}

.integral-v2-form label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-weight: 700;
    color: #cdd9ea;
}

.integral-v2-form input,
.integral-v2-form select {
    min-height: 38px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    background: #07111f;
    color: #f4f7fb;
    padding: 8px 10px;
}

.integral-v2-btn {
    min-height: 40px;
    border: 0;
    border-radius: 10px;
    padding: 10px 14px;
    cursor: pointer;
    font-weight: 700;
}

.integral-v2-btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.integral-v2-result-block {
    margin-top: 8px;
}

.integral-v2-log {
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.12);
}

.integral-v2-log.warning {
    background: rgba(255, 193, 7, 0.12);
    color: #ffe08a;
}

.integral-v2-log.info {
    background: rgba(45, 108, 223, 0.14);
    color: #cfe0ff;
}

.integral-v2-log.error {
    background: rgba(220, 53, 69, 0.14);
    color: #ffb5bd;
}

.integral-v2-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
    overflow: hidden;
    border-radius: 12px;
}

.integral-v2-table th,
.integral-v2-table td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    padding: 12px;
    text-align: left;
}

.integral-v2-table th {
    background: rgba(45, 108, 223, 0.22);
    color: #fff;
}

.integral-v2-chip,
.integral-v2-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 800;
}

.integral-v2-badge {
    background: rgba(45, 108, 223, 0.20);
    color: #cfe0ff;
}

.integral-v2-chip.ok {
    background: rgba(25, 135, 84, 0.20);
    color: #8ff0bc;
}

.integral-v2-chip.warn {
    background: rgba(255, 193, 7, 0.18);
    color: #ffe08a;
}

@media (max-width: 980px) {
    .integral-v2-layout,
    .integral-v2-form {
        grid-template-columns: 1fr;
    }

    .integral-v2-topbar,
    .integral-v2-hero,
    .integral-v2-result-header {
        flex-direction: column;
    }
}
''')

write_file("app/static/js/integral_diario_v2.js", r'''
(function () {
    "use strict";

    function onReady(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
            return;
        }

        callback();
    }

    function templateHtml(id) {
        const template = document.getElementById(id);
        return template ? template.innerHTML : "";
    }

    function initIntegralV2() {
        const form = document.getElementById("integral-v2-validar-form");
        const resultado = document.getElementById("integral-v2-resultado");

        if (!form || !resultado) {
            return;
        }

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            resultado.innerHTML = templateHtml("integral-v2-loading-template");

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                });

                resultado.innerHTML = await response.text();
            } catch (error) {
                resultado.innerHTML = templateHtml("integral-v2-error-comunicacion-template");
            }
        });
    }

    onReady(initIntegralV2);
})();
''')

# ---------------------------------------------------------------------
# Parches finales
# ---------------------------------------------------------------------

ensure_blueprint_registered()
patch_config_default()
patch_navs()

print("\nLISTO. Integral v2 quedó preparado en /integral-v2 y /integral-diario-v2")
print("Prueba recomendada: python -m compileall app")
