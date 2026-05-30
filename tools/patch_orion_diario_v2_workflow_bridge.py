from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

SERVICE = ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py"
JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_MARKER_BEGIN = "/* === ORION_DIARIO_V2_WORKFLOW_BRIDGE_BEGIN === */"
CSS_MARKER_END = "/* === ORION_DIARIO_V2_WORKFLOW_BRIDGE_END === */"


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


def patch_service_actions():
    title("1. PATCH acciones reales en orion_diario_v2_dashboard_service.py")

    if not SERVICE.exists():
        raise FileNotFoundError(f"No existe: {SERVICE}")

    original = read(SERVICE)
    text = original

    replacements = {
        '"accion": "crear_carpetas"': '"accion": "crear.carpetas"',
        '"accion": "verificar_red"': '"accion": "verificar.red"',
        '"accion": "ocr_totales"': '"accion": "ocr.procesar"',
        '"accion": "distribuir_archivos"': '"accion": "distribuir.preparar"',
        '"accion": "procesar_discador"': '"accion": "procesar.discador"',
        '"accion": "procesar_causales"': '"accion": "procesar.causales"',
        '"accion": "procesar_lotes"': '"accion": "procesar.lotes"',
        '"accion": "carga_causales"': '"accion": "carga.causales.verificar"',
        '"accion": "carga_lotes"': '"accion": "carga.lotes.verificar"',
        '"accion": "carga_discador"': '"accion": "carga.discador.verificar"',
        '"accion": "consolidado_orion"': '"accion": "consolidado.gestion.consultar"',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        backup(SERVICE)
        write(SERVICE, text)
        print("OK: acciones v2 convertidas al workflow real.")
    else:
        print("OK: no hubo cambios o ya estaba actualizado.")


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


def workflow_bridge_js_block():
    return r'''
    const ORION_V2_ACTION_MAP = {
        "crear.carpetas": {
            method: "GET",
            endpoint: "/accion/crear-carpetas"
        },
        "verificar.red": {
            method: "GET",
            endpoint: "/accion/verificar-red"
        },
        "distribuir.preparar": {
            method: "GET",
            endpoint: "/accion/distribuir"
        },
        "distribuir.copiar": {
            blocked: true,
            message: "La copia requiere selección previa de archivos. Por ahora ejecútela desde la pantalla Orion actual."
        },
        "procesar.discador": {
            method: "GET",
            endpoint: "/accion/procesar-discador"
        },
        "procesar.causales": {
            method: "GET",
            endpoint: "/accion/procesar-causales"
        },
        "procesar.lotes": {
            method: "GET",
            endpoint: "/accion/procesar-lotes"
        },
        "ocr.procesar": {
            blocked: true,
            message: "OCR requiere carga de imágenes. Por ahora ejecútelo desde la pantalla Orion actual."
        },
        "ocr.consolidar": {
            blocked: true,
            message: "La consolidación OCR requiere totales manuales. Se conectará en el siguiente paso."
        },
        "carga.causales.verificar": {
            method: "POST",
            endpoint: "/accion/verificar-carga",
            tipo: "causales"
        },
        "carga.causales.insertar": {
            method: "POST",
            endpoint: "/accion/insertar-datos",
            tipo: "causales"
        },
        "carga.lotes.verificar": {
            method: "POST",
            endpoint: "/accion/verificar-carga",
            tipo: "lote"
        },
        "carga.lotes.insertar": {
            method: "POST",
            endpoint: "/accion/insertar-datos",
            tipo: "lote"
        },
        "carga.discador.verificar": {
            method: "POST",
            endpoint: "/accion/verificar-carga",
            tipo: "discador"
        },
        "carga.discador.insertar": {
            method: "POST",
            endpoint: "/accion/insertar-datos",
            tipo: "discador"
        },
        "consolidado.gestion.consultar": {
            method: "POST",
            endpoint: "/accion/consolidar-consulta"
        }
    };

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function phaseResultId(actionName) {
        return "odv2-result-" + String(actionName || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function phaseStatusId(actionName) {
        return "odv2-status-" + String(actionName || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function setPhaseStatus(actionName, status, label) {
        const el = document.getElementById(phaseStatusId(actionName));
        if (!el) return;

        el.className = "odv2-phase-status " + status;
        el.textContent = label;
    }

    function looksLikeError(html) {
        const text = String(html || "").toLowerCase();

        return (
            text.includes("❌") ||
            text.includes("error") ||
            text.includes("traceback") ||
            text.includes("falló") ||
            text.includes("fallo")
        );
    }

    function buildWorkflowForm(actionName, meta) {
        collectInputs();

        const form = new FormData();
        form.append("fecha", state.fechaProceso);
        form.append("fecha_proceso", state.fechaProceso);
        form.append("mes_gestion", state.mesGestion);
        form.append("conexion", state.conexion);

        if (meta.tipo) {
            form.append("tipo", meta.tipo);
        }

        return form;
    }

    async function executeWorkflowAction(actionName, button) {
        const meta = ORION_V2_ACTION_MAP[actionName];

        const resultId = phaseResultId(actionName);
        const result = document.getElementById(resultId);

        if (!result) {
            alert("No se encontró contenedor de resultado para " + actionName);
            return;
        }

        if (!meta) {
            result.innerHTML = `<div class="odv2-result-warning">Acción no mapeada todavía: ${escapeHtml(actionName)}</div>`;
            return;
        }

        if (meta.blocked) {
            result.innerHTML = `<div class="odv2-result-warning">${escapeHtml(meta.message)}</div>`;
            setPhaseStatus(actionName, "warning", "Pendiente");
            return;
        }

        button.disabled = true;
        button.classList.add("loading");
        setPhaseStatus(actionName, "running", "Ejecutando");

        result.innerHTML = `
            <div class="odv2-result-loading">
                Ejecutando ${escapeHtml(actionName)}...
            </div>
        `;

        try {
            collectInputs();

            let response;

            if (meta.method === "GET") {
                const params = new URLSearchParams({
                    fecha: state.fechaProceso,
                    fecha_proceso: state.fechaProceso,
                    mes_gestion: state.mesGestion,
                    conexion: state.conexion,
                    _: Date.now().toString()
                });

                response = await fetch(meta.endpoint + "?" + params.toString(), {
                    method: "GET",
                    credentials: "same-origin"
                });
            } else {
                response = await fetch(meta.endpoint + "?_=" + Date.now(), {
                    method: "POST",
                    body: buildWorkflowForm(actionName, meta),
                    credentials: "same-origin"
                });
            }

            const html = await response.text();

            result.innerHTML = `
                <div class="odv2-result-toolbar">
                    <strong>Resultado: ${escapeHtml(actionName)}</strong>
                    <span>HTTP ${response.status}</span>
                </div>
                <div class="odv2-result-html">${html}</div>
            `;

            const error = !response.ok || looksLikeError(html);

            setPhaseStatus(
                actionName,
                error ? "error" : "success",
                error ? "Error" : "Correcto"
            );

            if (!error) {
                await loadStats();
            }

        } catch (error) {
            result.innerHTML = `<div class="odv2-result-error">Error ejecutando ${escapeHtml(actionName)}: ${escapeHtml(error.message || error)}</div>`;
            setPhaseStatus(actionName, "error", "Error");
        } finally {
            button.disabled = false;
            button.classList.remove("loading");
        }
    }

    function renderPhaseBoard(data) {
        const root = $("#odv2-phase-board");
        root.innerHTML = "";

        data.fases.forEach(f => {
            const item = document.createElement("div");
            item.className = "odv2-phase";

            const action = f.accion || "";
            const resultId = phaseResultId(action);
            const statusId = phaseStatusId(action);

            item.innerHTML = `
                <div class="odv2-phase-head">
                    <span>${escapeHtml(f.codigo)} — ${escapeHtml(f.nombre)}</span>
                    <span id="${statusId}" class="odv2-phase-status pending">${escapeHtml(f.badge || "Pendiente")}</span>
                </div>
                <div class="odv2-phase-body">
                    <div>
                        <strong>${escapeHtml(f.grupo)}</strong><br>
                        ${escapeHtml(f.descripcion)}
                        <div class="odv2-phase-action-code">${escapeHtml(action)}</div>
                    </div>
                    <button class="odv2-run" data-phase="${escapeHtml(f.codigo)}" data-action="${escapeHtml(action)}">Ejecutar fase</button>
                </div>
                <div class="odv2-phase-result" id="${resultId}">
                    <div class="odv2-empty">Resultado pendiente.</div>
                </div>
            `;

            root.appendChild(item);
        });

        root.querySelectorAll(".odv2-run").forEach(btn => {
            btn.addEventListener("click", () => {
                executeWorkflowAction(btn.dataset.action, btn);
            });
        });
    }
'''


def patch_js():
    title("2. PATCH JS: botones v2 -> endpoints reales")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    start, end = find_function_bounds(text, "renderPhaseBoard")
    replacement = workflow_bridge_js_block()

    text = text[:start] + replacement + text[end:]

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: orion_diario_v2.js actualizado.")
    else:
        print("OK: JS sin cambios.")


def remove_css_block(text):
    if CSS_MARKER_BEGIN not in text:
        return text

    before = text.split(CSS_MARKER_BEGIN, 1)[0].rstrip()
    rest = text.split(CSS_MARKER_BEGIN, 1)[1]

    if CSS_MARKER_END in rest:
        after = rest.split(CSS_MARKER_END, 1)[1].lstrip()
        return before + "\n\n" + after

    return before + "\n"


def patch_css():
    title("3. PATCH CSS: resultados de fases")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)
    text = remove_css_block(original).rstrip()

    block = f"""
{CSS_MARKER_BEGIN}

.odv2-phase-status {{
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 900;
    background: #1f2937;
    color: var(--yellow);
}}

.odv2-phase-status.running {{
    background: #172554;
    color: #93c5fd;
}}

.odv2-phase-status.success {{
    background: #052e16;
    color: #86efac;
}}

.odv2-phase-status.error {{
    background: #450a0a;
    color: #fca5a5;
}}

.odv2-phase-status.warning {{
    background: #422006;
    color: #facc15;
}}

.odv2-phase-action-code {{
    margin-top: 8px;
    color: var(--cyan);
    font-size: 12px;
    font-family: Consolas, monospace;
}}

.odv2-phase-result {{
    border-top: 1px solid #243755;
    padding: 12px 16px;
    background: #07111f;
}}

.odv2-result-toolbar {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 10px;
    color: var(--cyan);
}}

.odv2-result-html {{
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 12px;
    padding: 12px;
    overflow-x: auto;
}}

.odv2-result-loading,
.odv2-result-warning,
.odv2-result-error {{
    border-radius: 12px;
    padding: 12px;
    font-weight: 800;
}}

.odv2-result-loading {{
    background: #082f49;
    color: #7dd3fc;
    border: 1px solid #0369a1;
}}

.odv2-result-warning {{
    background: #422006;
    color: #facc15;
    border: 1px solid #a16207;
}}

.odv2-result-error {{
    background: #450a0a;
    color: #fca5a5;
    border: 1px solid #b91c1c;
}}

.odv2-run.loading {{
    opacity: .65;
    cursor: wait;
}}

{CSS_MARKER_END}
"""

    text = text + "\n\n" + block.strip() + "\n"

    if text != original:
        backup(CSS)
        write(CSS, text)
        print("OK: CSS actualizado.")
    else:
        print("OK: CSS sin cambios.")


def compile_python():
    title("4. COMPILACION PYTHON")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SERVICE),
            str(ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py"),
            str(ROOT / "app" / "__init__.py"),
        ],
        check=True,
    )

    print("OK: Python compila.")


def main():
    title("PATCH ORION DIARIO V2 WORKFLOW BRIDGE")

    patch_service_actions()
    patch_js()
    patch_css()
    compile_python()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Abre:")
    print("  http://127.0.0.1:5000/orion-diario-v2")
    print("")
    print("Prueba primero:")
    print("  1) Cargar contexto")
    print("  2) Ejecutar Crear carpetas")
    print("  3) Ejecutar Verificar red")
    print("  4) Ejecutar panel estadístico")
    print("")
    print("OCR y distribución con selección quedan bloqueados por seguridad hasta integrarlos con sus formularios.")


if __name__ == "__main__":
    main()