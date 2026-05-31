from __future__ import annotations

from html import escape
from typing import Any


def _v(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def _textarea(name: str, values: list[str]) -> str:
    text = "\n".join(str(v) for v in values or [])
    return f"<textarea name='{_v(name)}' rows='4'>{_v(text)}</textarea>"


def _sql_fields(prefix: str, cfg: dict[str, Any]) -> str:
    return f"""
    <div class="oac-sql-grid" data-sql-prefix="{_v(prefix)}">
        <label>Servidor<input name="{_v(prefix)}.server" value="{_v(cfg.get('server', ''))}"></label>
        <label>Puerto<input name="{_v(prefix)}.port" value="{_v(cfg.get('port', ''))}"></label>
        <label>Base datos<input name="{_v(prefix)}.database" value="{_v(cfg.get('database', ''))}"></label>
        <label>Auth
            <select name="{_v(prefix)}.auth">
                <option value="sql" {'selected' if cfg.get('auth', 'sql') == 'sql' else ''}>SQL</option>
                <option value="windows" {'selected' if cfg.get('auth') == 'windows' else ''}>Windows</option>
            </select>
        </label>
        <label>Usuario<input name="{_v(prefix)}.username" value="{_v(cfg.get('username', ''))}"></label>
        <label>Password<input name="{_v(prefix)}.password" value="{_v(cfg.get('password', ''))}" type="password"></label>
    </div>
    """


def render_config_panel(config: dict[str, Any]) -> str:
    rutas = config.get("rutas", {})
    sql = config.get("sql", {})

    html = f"""
    <div class="oac-card">
        <div class="oac-header">
            <div>
                <h3>⚙ Configuración global</h3>
                <p>Rutas, carpeta DATA y conexiones SQL compartidas por Orion, ASTER y Consolidado Gestión.</p>
            </div>
            <span class="oac-pill">{_v(config.get('ambiente_activo', 'local')).upper()}</span>
        </div>

        <div class="oac-grid">
            <label class="oac-wide">
                Carpeta DATA raíz
                <input id="oac-data-root" value="{_v(config.get('data_root', ''))}">
            </label>

            <label>
                Ambiente activo
                <select id="oac-ambiente">
                    <option value="local" {'selected' if config.get('ambiente_activo') == 'local' else ''}>LOCAL - Pruebas</option>
                    <option value="remoto" {'selected' if config.get('ambiente_activo') == 'remoto' else ''}>REMOTO - Producción</option>
                </select>
            </label>
        </div>

        <details class="oac-details" open>
            <summary>Rutas LOCAL</summary>
            <div class="oac-grid two">
                <label>ORION LOCAL{_textarea('rutas.local.orion', rutas.get('local', {}).get('orion', []))}</label>
                <label>ASTER LOCAL{_textarea('rutas.local.aster', rutas.get('local', {}).get('aster', []))}</label>
            </div>
        </details>

        <details class="oac-details">
            <summary>Rutas REMOTO</summary>
            <div class="oac-grid two">
                <label>ORION REMOTO{_textarea('rutas.remoto.orion', rutas.get('remoto', {}).get('orion', []))}</label>
                <label>ASTER REMOTO{_textarea('rutas.remoto.aster', rutas.get('remoto', {}).get('aster', []))}</label>
            </div>
        </details>

        <details class="oac-details">
            <summary>SQL LOCAL</summary>
            <h4>Orion</h4>
            {_sql_fields('sql.local.orion', sql.get('local', {}).get('orion', {}))}
            <h4>ASTER API</h4>
            {_sql_fields('sql.local.aster_api', sql.get('local', {}).get('aster_api', {}))}
            <h4>Gestión Consolidada</h4>
            {_sql_fields('sql.local.gestion_consolidada', sql.get('local', {}).get('gestion_consolidada', {}))}
        </details>

        <details class="oac-details">
            <summary>SQL REMOTO</summary>
            <h4>Orion</h4>
            {_sql_fields('sql.remoto.orion', sql.get('remoto', {}).get('orion', {}))}
            <h4>ASTER API</h4>
            {_sql_fields('sql.remoto.aster_api', sql.get('remoto', {}).get('aster_api', {}))}
            <h4>Gestión Consolidada</h4>
            {_sql_fields('sql.remoto.gestion_consolidada', sql.get('remoto', {}).get('gestion_consolidada', {}))}
        </details>

        <div class="oac-actions">
            <button type="button" id="oac-save" class="odv2-primary">Guardar configuración</button>
            <button type="button" id="oac-test-local" class="odv2-secondary" data-oac-test="local">Probar LOCAL</button>
            <button type="button" id="oac-test-remoto" class="odv2-secondary danger" data-oac-test="remoto">Probar REMOTO</button>
        </div>

        <div id="oac-result" class="oac-result">
            Configuración cargada. Modifique y guarde si corresponde.
        </div>
    </div>
    """

    return html


def _render_status_item(item: dict[str, Any]) -> str:
    cls = "success" if item.get("ok") else "error"

    return f"""
    <tr>
        <td>{_v(item.get('path') or item.get('modulo') or '')}</td>
        <td>{_v(item.get('server') or '')}</td>
        <td>{_v(item.get('database') or '')}</td>
        <td><span class="oac-status {cls}">{_v(item.get('estado'))}</span></td>
        <td>{_v(item.get('detalle'))}</td>
    </tr>
    """


def render_config_test_result(data: dict[str, Any]) -> str:
    rutas_orion = data.get("rutas", {}).get("orion", [])
    rutas_aster = data.get("rutas", {}).get("aster", [])
    sql = data.get("sql", {})

    rows = []
    rows.append(_render_status_item(data.get("data_root", {})))

    for item in rutas_orion:
        item = dict(item)
        item["path"] = "ORION: " + str(item.get("path", ""))
        rows.append(_render_status_item(item))

    for item in rutas_aster:
        item = dict(item)
        item["path"] = "ASTER: " + str(item.get("path", ""))
        rows.append(_render_status_item(item))

    for key, item in sql.items():
        item = dict(item)
        item["modulo"] = key
        rows.append(_render_status_item(item))

    return f"""
    <div class="oac-test-box">
        <h4>Resultado prueba configuración { _v(data.get('conexion', '')).upper() }</h4>
        <table class="dataframe ui-table-compact">
            <tr>
                <th>Elemento</th>
                <th>Servidor</th>
                <th>BD</th>
                <th>Estado</th>
                <th>Detalle</th>
            </tr>
            {''.join(rows)}
        </table>
    </div>
    """
