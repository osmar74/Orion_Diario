from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

TPL_INDEX = ROOT / "app" / "templates" / "orion_diario_v2" / "index.html"
BLUEPRINT = ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py"
SERVICE = ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py"
JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

SERVICE_BEGIN = "# === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN ==="
SERVICE_END = "# === ORION_DIARIO_V2_DISTRIBUCION_MVC_END ==="

JS_BEGIN = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN === */"
JS_END = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_END === */"

CSS_BEGIN = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_END === */"


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def remove_block(text: str, begin: str, end: str) -> str:
    while begin in text:
        before = text.split(begin, 1)[0].rstrip()
        rest = text.split(begin, 1)[1]

        if end in rest:
            after = rest.split(end, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def find_function_bounds(text: str, function_name: str):
    needle = f"function {function_name}("
    start = text.find(needle)

    if start < 0:
        raise RuntimeError(f"No encontré función JS: {function_name}")

    brace_start = text.find("{", start)

    if brace_start < 0:
        raise RuntimeError(f"No encontré apertura de función: {function_name}")

    depth = 0
    in_string = None
    escape = False

    for idx in range(brace_start, len(text)):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == in_string:
                in_string = None

            continue

        if ch in ["'", '"', "`"]:
            in_string = ch
            continue

        if ch == "{":
            depth += 1

        elif ch == "}":
            depth -= 1

            if depth == 0:
                return start, idx + 1

    raise RuntimeError(f"No pude cerrar función JS: {function_name}")


def patch_template():
    title("1. LIMPIANDO TEMPLATE - QUITAR JS EXTERNO DE DISTRIBUCION")

    if not TPL_INDEX.exists():
        raise FileNotFoundError(f"No existe: {TPL_INDEX}")

    original = read(TPL_INDEX)
    text = original

    text = re.sub(
        r'\s*<script[^>]*orion_diario_v2_distribucion_fix\.js[^>]*>\s*</script>',
        "",
        text,
        flags=re.I,
    )

    if text != original:
        backup(TPL_INDEX)
        write(TPL_INDEX, text)
        print("OK: eliminado orion_diario_v2_distribucion_fix.js del template.")
    else:
        print("OK: el template no tenía JS externo de distribución.")


def service_block():
    return r'''
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
) -> dict[str, Any]:
    from app.services.orion_fases_service import preparar_distribucion_archivos_orion

    fecha = _fecha_yyyymmdd(fecha_proceso)
    candidatos = _rutas_base(rutas_base)
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
) -> dict[str, Any]:
    respuesta = _orion_v2_resolver_distribucion(
        data_dir=data_dir,
        fecha_proceso=fecha_proceso,
        rutas_base=rutas_base,
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
) -> dict[str, Any]:
    from app.services.orion_fases_service import distribuir_archivos_seleccionados_orion
    from app.services.orion_fases_renderer import render_distribucion_seleccionados_orion

    fecha = _fecha_yyyymmdd(fecha_proceso)
    candidatos = _rutas_base(rutas_base)
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
'''


def patch_service():
    title("2. PATCH SERVICE - AGREGAR LOGICA MVC DISTRIBUCION")

    if not SERVICE.exists():
        raise FileNotFoundError(f"No existe: {SERVICE}")

    original = read(SERVICE)
    text = remove_block(original, SERVICE_BEGIN, SERVICE_END).rstrip()

    text = text + "\n\n" + service_block().strip() + "\n"

    if text != original:
        backup(SERVICE)
        write(SERVICE, text)
        print("OK: service actualizado.")
    else:
        print("OK: service sin cambios.")


def routes_block():
    return r'''

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN ===

@orion_diario_v2_bp.route("/api/orion-diario-v2/distribucion/preparar")
def api_orion_diario_v2_distribucion_preparar():
    fecha_proceso = request.args.get("fecha_proceso", "20260429").strip()
    mes_gestion = request.args.get("mes_gestion", "abril").strip()
    rutas_base = request.args.getlist("rutas_base")

    data = preparar_distribucion_orion_v2(
        data_dir=DATA_DIR,
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        rutas_base=rutas_base,
    )

    status = 200 if data.get("success") else 400
    return jsonify(data), status


@orion_diario_v2_bp.route("/api/orion-diario-v2/distribucion/copiar", methods=["POST"])
def api_orion_diario_v2_distribucion_copiar():
    payload = request.get_json(silent=True) or {}

    fecha_proceso = str(
        payload.get("fecha_proceso")
        or payload.get("fecha")
        or "20260429"
    ).strip()

    mes_gestion = str(payload.get("mes_gestion") or "abril").strip()
    rutas_base = payload.get("rutas_base") or []
    seleccionados = payload.get("seleccionados") or []

    if not isinstance(rutas_base, list):
        rutas_base = []

    if not isinstance(seleccionados, list):
        seleccionados = []

    data = copiar_distribucion_orion_v2(
        data_dir=DATA_DIR,
        fecha_proceso=fecha_proceso,
        mes_gestion=mes_gestion,
        seleccionados=seleccionados,
        rutas_base=rutas_base,
    )

    status = 200 if data.get("success") else 400
    return jsonify(data), status

# === ORION_DIARIO_V2_DISTRIBUCION_MVC_END ===
'''


def patch_blueprint():
    title("3. PATCH BLUEPRINT - AGREGAR ENDPOINTS JSON")

    if not BLUEPRINT.exists():
        raise FileNotFoundError(f"No existe: {BLUEPRINT}")

    original = read(BLUEPRINT)
    text = remove_block(original, "# === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN ===", "# === ORION_DIARIO_V2_DISTRIBUCION_MVC_END ===").rstrip()

    if "from app.config import DATA_DIR" not in text:
        text = text.replace(
            "from flask import Blueprint, jsonify, render_template, request",
            "from flask import Blueprint, jsonify, render_template, request\n\nfrom app.config import DATA_DIR",
            1,
        )

    if "preparar_distribucion_orion_v2" not in text:
        text = text.replace(
            "construir_estadisticas_orion_v2,",
            "construir_estadisticas_orion_v2,\n    preparar_distribucion_orion_v2,\n    copiar_distribucion_orion_v2,",
            1,
        )

    text = text + "\n\n" + routes_block().strip() + "\n"

    if text != original:
        backup(BLUEPRINT)
        write(BLUEPRINT, text)
        print("OK: blueprint actualizado.")
    else:
        print("OK: blueprint sin cambios.")


def js_block():
    return r'''
/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN === */

    function odv2DistEmptyCounts() {
        return { Causales: 0, Lotes: 0, Discador: 0 };
    }

    function odv2DistCountKey(categoria) {
        const value = String(categoria || "").trim();

        if (value.toLowerCase().includes("causal")) return "Causales";
        if (value.toLowerCase().includes("lote")) return "Lotes";
        if (value.toLowerCase().includes("discador")) return "Discador";

        return value || "Otros";
    }

    function odv2DistCollect() {
        const checks = Array.from(document.querySelectorAll("#odv2-distribucion-mvc input[type='checkbox'][data-categoria][data-archivo]"));

        const encontrados = odv2DistEmptyCounts();
        const seleccionados = odv2DistEmptyCounts();
        const payload = [];

        checks.forEach(cb => {
            const categoria = cb.dataset.categoria;
            const archivo = cb.dataset.archivo;
            const key = odv2DistCountKey(categoria);

            if (!(key in encontrados)) encontrados[key] = 0;
            if (!(key in seleccionados)) seleccionados[key] = 0;

            encontrados[key] += 1;

            if (cb.checked) {
                seleccionados[key] += 1;
                payload.push({ categoria, archivo });
            }
        });

        return { encontrados, seleccionados, payload };
    }

    function odv2DistTotal(counts) {
        return Object.values(counts || {}).reduce((a, b) => a + Number(b || 0), 0);
    }

    function odv2DistPie(counts, title) {
        const rows = [
            { key: "Causales", label: "Cau", color: "#0ea5ff" },
            { key: "Lotes", label: "Lot", color: "#f59e0b" },
            { key: "Discador", label: "Dis", color: "#22c55e" },
        ];

        const total = odv2DistTotal(counts);

        if (!total) {
            return `
                <div class="odv2-dist-pie-card">
                    <strong>${escapeHtml(title)}</strong>
                    <div class="odv2-dist-pie-empty">0</div>
                </div>
            `;
        }

        let start = 0;

        const segments = rows.map(row => {
            const value = Number(counts[row.key] || 0);
            const pct = value / total * 100;
            const end = start + pct;
            const segment = `${row.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        return `
            <div class="odv2-dist-pie-card">
                <strong>${escapeHtml(title)}</strong>
                <div class="odv2-dist-pie-stage">
                    <div class="odv2-dist-pie" style="background: conic-gradient(${segments.join(", ")});">
                        <div class="odv2-dist-pie-center">
                            <b>${fmt(total)}</b>
                            <span>${escapeHtml(title)}</span>
                        </div>
                    </div>

                    ${rows.map((row, idx) => `
                        <div class="odv2-dist-pie-value odv2-dist-pie-value-${idx}">
                            <i style="background:${row.color}"></i>
                            <span>${row.label}</span>
                            <b>${fmt(counts[row.key] || 0)}</b>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function odv2DistSummaryTable(encontrados, seleccionados, copiados) {
        const rows = ["Causales", "Lotes", "Discador"];
        const totalEncontrados = odv2DistTotal(encontrados);
        const totalSeleccionados = odv2DistTotal(seleccionados);
        const totalCopiados = odv2DistTotal(copiados);

        return `
            <table class="odv2-table odv2-dist-summary-table">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Total encontrados</th>
                        <th>Total seleccionados</th>
                        <th>Total copiados</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${row}</td>
                            <td>${fmt(encontrados[row] || 0)}</td>
                            <td>${fmt(seleccionados[row] || 0)}</td>
                            <td>${fmt(copiados[row] || 0)}</td>
                        </tr>
                    `).join("")}
                    <tr class="odv2-dist-total-row">
                        <td>Total</td>
                        <td>${fmt(totalEncontrados)}</td>
                        <td>${fmt(totalSeleccionados)}</td>
                        <td>${fmt(totalCopiados)}</td>
                    </tr>
                </tbody>
            </table>
        `;
    }

    function odv2DistRenderSummary(copiados = null) {
        const root = document.getElementById("odv2-distribucion-mvc");
        if (!root) return;

        const data = odv2DistCollect();
        const copiedCounts = copiados || odv2DistEmptyCounts();

        const target = document.getElementById("odv2-dist-summary");

        if (!target) return;

        target.innerHTML = `
            ${odv2DistSummaryTable(data.encontrados, data.seleccionados, copiedCounts)}
            <div class="odv2-dist-pies-title">Resumen visual</div>
            <div class="odv2-dist-pies">
                ${odv2DistPie(data.seleccionados, "Antes")}
                ${odv2DistPie(copiedCounts, "Después")}
            </div>
        `;
    }

    function odv2DistCopiedCounts(detalle) {
        const counts = odv2DistEmptyCounts();

        (detalle || []).forEach(item => {
            const key = odv2DistCountKey(item.categoria);
            if (!(key in counts)) counts[key] = 0;
            counts[key] += 1;
        });

        return counts;
    }

    function odv2DistRender(data) {
        const grupos = data.grupos || [];

        const html = `
            <div id="odv2-distribucion-mvc" class="odv2-dist-box">
                <div class="odv2-dist-head">
                    <div>
                        <h4>Distribución de archivos Orion</h4>
                        <p>Seleccione los archivos a copiar. Todos vienen marcados por defecto.</p>
                        <small>Ruta usada: ${escapeHtml(data.red_base_usada || "--")}</small>
                    </div>
                    <button type="button" id="odv2-dist-copy" class="odv2-dist-copy-btn">Copiar seleccionados</button>
                </div>

                <div class="odv2-dist-selection">
                    ${grupos.map(g => `
                        <details class="odv2-dist-group" open>
                            <summary>📁 ${escapeHtml(g.categoria)} - ${fmt(g.total)} archivo(s)</summary>
                            <div class="odv2-dist-routes">
                                <div><b>Ruta origen:</b> ${escapeHtml(g.ruta_origen || "--")}</div>
                                <div><b>Ruta destino:</b> ${escapeHtml(g.ruta_destino || "--")}</div>
                            </div>
                            <table class="odv2-table odv2-dist-files-table">
                                <thead>
                                    <tr>
                                        <th>Copiar</th>
                                        <th>Archivo</th>
                                        <th>Ruta origen</th>
                                        <th>Ruta destino</th>
                                        <th>Estado destino</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${(g.archivos || []).map(a => `
                                        <tr>
                                            <td>
                                                <input type="checkbox"
                                                       checked
                                                       data-categoria="${escapeHtml(a.categoria)}"
                                                       data-archivo="${escapeHtml(a.archivo)}">
                                            </td>
                                            <td><b>${escapeHtml(a.archivo)}</b></td>
                                            <td>${escapeHtml(a.ruta_origen || "")}</td>
                                            <td>${escapeHtml(a.ruta_destino || "")}</td>
                                            <td class="${a.existe_destino ? "odv2-dist-warn" : "odv2-dist-ok"}">
                                                ${a.existe_destino ? "⚠️ Ya existe, se reemplazará" : "✅ Nuevo"}
                                            </td>
                                        </tr>
                                    `).join("")}
                                </tbody>
                            </table>
                        </details>
                    `).join("")}
                </div>

                <div id="odv2-dist-summary"></div>
                <div id="odv2-dist-result"></div>
            </div>
        `;

        setPhaseResult("distribuir.preparar", html);
        setPhaseStatus("distribuir.preparar", "success", "Correcto");

        document.querySelectorAll("#odv2-distribucion-mvc input[type='checkbox']").forEach(cb => {
            cb.addEventListener("change", () => odv2DistRenderSummary());
        });

        const btn = document.getElementById("odv2-dist-copy");
        if (btn) btn.addEventListener("click", copiarDistribucionMvc);

        odv2DistRenderSummary();
    }

    async function ejecutarDistribucionMvc(button) {
        try {
            collectInputs();

            button.disabled = true;
            button.classList.add("loading");

            setPhaseStatus("distribuir.preparar", "running", "Ejecutando");
            setPhaseResult("distribuir.preparar", `<div class="odv2-result-loading">Preparando distribución Orion v2...</div>`);

            const url = "/api/orion-diario-v2/distribucion/preparar?" + getParams(true).toString();
            const response = await fetch(url, { credentials: "same-origin" });
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Error preparando distribución.");
            }

            odv2DistRender(data);
            debug("Distribución Orion v2 preparada correctamente.", "success");

        } catch (error) {
            setPhaseStatus("distribuir.preparar", "error", "Error");
            setPhaseResult("distribuir.preparar", `<div class="odv2-result-error">Error preparando distribución: ${escapeHtml(error.message || error)}</div>`);
            debug("Error preparando distribución MVC: " + (error.message || error), "error");
        } finally {
            button.disabled = false;
            button.classList.remove("loading");
        }
    }

    async function copiarDistribucionMvc() {
        const result = document.getElementById("odv2-dist-result");
        const collected = odv2DistCollect();

        if (!collected.payload.length) {
            if (result) result.innerHTML = `<div class="odv2-result-warning">No hay archivos seleccionados para copiar.</div>`;
            return;
        }

        if (result) {
            result.innerHTML = `<div class="odv2-result-loading">Copiando ${fmt(collected.payload.length)} archivo(s)...</div>`;
        }

        try {
            const payload = {
                fecha_proceso: state.fechaProceso,
                fecha: state.fechaProceso,
                mes_gestion: state.mesGestion,
                conexion: state.conexion,
                rutas_base: getActiveRoutes(),
                seleccionados: collected.payload
            };

            const response = await fetch("/api/orion-diario-v2/distribucion/copiar?_=" + Date.now(), {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            const copiedCounts = data.success ? odv2DistCopiedCounts(data.copiados_detalle) : odv2DistEmptyCounts();
            odv2DistRenderSummary(copiedCounts);

            if (result) {
                result.innerHTML = `
                    <div class="odv2-result-toolbar">
                        <strong>Resultado copia seleccionados</strong>
                        <span>HTTP ${response.status}</span>
                    </div>
                    <div class="odv2-result-html">${data.result_html || escapeHtml(data.error || "")}</div>
                `;
            }

            setPhaseStatus("distribuir.preparar", data.success ? "success" : "error", data.success ? "Copiado" : "Error copia");
            debug(data.success ? "Copia realizada correctamente." : "Error copiando archivos.", data.success ? "success" : "error");

        } catch (error) {
            if (result) {
                result.innerHTML = `<div class="odv2-result-error">Error copiando seleccionados: ${escapeHtml(error.message || error)}</div>`;
            }

            setPhaseStatus("distribuir.preparar", "error", "Error copia");
            debug("Error copiando distribución MVC: " + (error.message || error), "error");
        }
    }

    window.OrionDistribucionMVC = {
        preparar: ejecutarDistribucionMvc,
        copiar: copiarDistribucionMvc,
    };

/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_END === */
'''


def patch_js():
    title("4. PATCH JS - DISTRIBUCION MVC EN JS PRINCIPAL")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = remove_block(original, JS_BEGIN, JS_END)

    marker = "    async function executeWorkflowAction(actionName, button) {"

    if marker not in text:
        raise RuntimeError("No encontré executeWorkflowAction en JS principal.")

    text = text.replace(marker, js_block() + "\n\n" + marker, 1)

    text = text.replace(
        '    async function executeWorkflowAction(actionName, button) {\n        const meta = ORION_V2_ACTION_MAP[actionName];',
        '''    async function executeWorkflowAction(actionName, button) {
        if (actionName === "distribuir.preparar") {
            await ejecutarDistribucionMvc(button);
            return;
        }

        const meta = ORION_V2_ACTION_MAP[actionName];''',
        1,
    )

    # Evitar llamada a helpers viejos de distribución si quedó en el flujo anterior.
    text = text.replace(
        '''
            if (actionName === "distribuir.preparar" && !error) {
                appendDistributionControls(actionName);
            }
''',
        "",
    )

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: JS principal actualizado.")
    else:
        print("OK: JS sin cambios.")


def css_block():
    return r'''
/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN === */

.odv2-dist-box {
    border: 1px solid #263752;
    border-radius: 16px;
    background: #07111f;
    padding: 14px;
}

.odv2-dist-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 14px;
}

.odv2-dist-head h4 {
    margin: 0;
    color: var(--cyan);
    font-size: 16px;
}

.odv2-dist-head p {
    margin: 5px 0;
    color: var(--muted);
    font-size: 13px;
}

.odv2-dist-head small {
    color: #93c5fd;
    font-size: 11px;
}

.odv2-dist-copy-btn {
    min-width: 190px;
    border: 0;
    border-radius: 12px;
    padding: 12px 18px;
    color: white;
    font-weight: 900;
    cursor: pointer;
    background: linear-gradient(90deg, #2563eb, #0ea5e9);
}

.odv2-dist-group {
    border: 1px solid #263752;
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 12px;
    background: #0b1222;
}

.odv2-dist-group summary {
    cursor: pointer;
    color: var(--text);
    font-weight: 900;
}

.odv2-dist-routes {
    display: grid;
    gap: 6px;
    margin: 10px 0;
    color: var(--muted);
    font-size: 12px;
    word-break: break-all;
}

.odv2-dist-files-table {
    font-size: 12px;
}

.odv2-dist-files-table th,
.odv2-dist-files-table td {
    padding: 8px 9px;
    vertical-align: top;
    word-break: break-word;
}

.odv2-dist-files-table input[type="checkbox"] {
    transform: scale(1.1);
    accent-color: #0ea5ff;
}

.odv2-dist-warn {
    color: #facc15;
    font-weight: 900;
}

.odv2-dist-ok {
    color: #86efac;
    font-weight: 900;
}

.odv2-dist-summary-table {
    margin-top: 14px;
    font-size: 12px;
}

.odv2-dist-total-row td {
    color: var(--cyan);
    font-weight: 900;
    background: #0b1222;
}

.odv2-dist-pies-title {
    color: var(--cyan);
    font-weight: 900;
    font-size: 13px;
    margin-top: 16px;
}

.odv2-dist-pies {
    display: grid;
    grid-template-columns: repeat(2, minmax(260px, 1fr));
    gap: 18px;
    margin-top: 10px;
}

.odv2-dist-pie-card {
    border: 1px solid #263752;
    border-radius: 15px;
    background: #07111f;
    padding: 14px;
    display: grid;
    justify-items: center;
    gap: 10px;
}

.odv2-dist-pie-card > strong {
    color: var(--text);
    font-size: 14px;
}

.odv2-dist-pie-stage {
    position: relative;
    width: 250px;
    height: 190px;
    display: grid;
    place-items: center;
}

.odv2-dist-pie {
    width: 132px;
    height: 132px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 1px solid #263752;
}

.odv2-dist-pie-center {
    width: 74px;
    height: 74px;
    border-radius: 50%;
    background: #0b1222;
    border: 1px solid #263752;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 6px;
}

.odv2-dist-pie-center b {
    display: block;
    font-size: 19px;
    line-height: 1;
    color: var(--text);
}

.odv2-dist-pie-center span {
    display: block;
    font-size: 10px;
    color: var(--muted);
    font-weight: 900;
}

.odv2-dist-pie-value {
    position: absolute;
    display: grid;
    grid-template-columns: 9px auto auto;
    gap: 5px;
    align-items: center;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 999px;
    padding: 5px 8px;
    font-size: 11px;
    white-space: nowrap;
}

.odv2-dist-pie-value i {
    width: 8px;
    height: 8px;
    border-radius: 999px;
}

.odv2-dist-pie-value span {
    color: var(--muted);
    font-weight: 800;
}

.odv2-dist-pie-value b {
    color: var(--cyan);
    font-weight: 900;
}

.odv2-dist-pie-value-0 {
    top: 6px;
    right: 8px;
}

.odv2-dist-pie-value-1 {
    bottom: 8px;
    left: 18px;
}

.odv2-dist-pie-value-2 {
    top: 82px;
    right: 0;
}

.odv2-dist-pie-empty {
    width: 132px;
    height: 132px;
    border-radius: 50%;
    border: 1px dashed #334155;
    display: grid;
    place-items: center;
    color: var(--muted);
    font-size: 22px;
    font-weight: 900;
}

@media (max-width: 1100px) {
    .odv2-dist-head {
        flex-direction: column;
        align-items: stretch;
    }

    .odv2-dist-pies {
        grid-template-columns: 1fr;
    }
}

/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_END === */
'''


def patch_css():
    title("5. PATCH CSS - ESTILO DISTRIBUCION MVC")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)
    text = remove_block(original, CSS_BEGIN, CSS_END).rstrip()
    text = text + "\n\n" + css_block().strip() + "\n"

    if text != original:
        backup(CSS)
        write(CSS, text)
        print("OK: CSS actualizado.")
    else:
        print("OK: CSS sin cambios.")


def compile_related():
    title("6. VALIDACION PYTHON")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(BLUEPRINT),
            str(SERVICE),
            str(ROOT / "app" / "__init__.py"),
        ],
        check=True,
    )

    print("OK: Python compila.")


def main():
    title("PATCH ORION DIARIO V2 - DISTRIBUCION MVC CLEAN")

    patch_template()
    patch_service()
    patch_blueprint()
    patch_js()
    patch_css()
    compile_related()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("")
    print("Validar:")
    print("  1. Cargar contexto")
    print("  2. Ejecutar D - Distribuir archivos")
    print("  3. Ver tabla propia con checkboxes")
    print("  4. Desmarcar algunos archivos")
    print("  5. Copiar seleccionados")
    print("  6. Ver tabla única + dos pies + resultado")


if __name__ == "__main__":
    main()