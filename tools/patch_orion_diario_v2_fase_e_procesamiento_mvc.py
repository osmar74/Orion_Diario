from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

JS_BEGIN = "/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_BEGIN === */"
JS_END = "/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_END === */"

CSS_BEGIN = "/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_END === */"


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


def js_block():
    return r'''
/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_BEGIN === */

    const ORION_PROC_ACTIONS = new Set([
        "procesar.discador",
        "procesar.causales",
        "procesar.lotes"
    ]);

    const ORION_PROC_META = {
        "procesar.discador": {
            tipo: "Discador",
            icono: "📞",
            esperado: "Consolidado Discador",
            color: "cyan"
        },
        "procesar.causales": {
            tipo: "Causales",
            icono: "📋",
            esperado: "Causales_Consolidado.xlsx",
            color: "blue"
        },
        "procesar.lotes": {
            tipo: "Lotes",
            icono: "🧩",
            esperado: "Lotes consolidados",
            color: "green"
        }
    };

    function odv2ProcStripHtml(html) {
        const div = document.createElement("div");
        div.innerHTML = html || "";
        return div.textContent || div.innerText || "";
    }

    function odv2ProcNum(value) {
        const clean = String(value ?? "")
            .replace(/\./g, "")
            .replace(/,/g, "")
            .replace(/[^\d-]/g, "");

        if (!clean) return null;

        const n = Number(clean);
        return Number.isFinite(n) ? n : null;
    }

    function odv2ProcTableRows(html) {
        const doc = new DOMParser().parseFromString(html || "", "text/html");
        const tables = Array.from(doc.querySelectorAll("table"));
        const parsed = [];

        tables.forEach(table => {
            const headers = Array.from(table.querySelectorAll("tr:first-child th"))
                .map(th => th.textContent.trim());

            const rows = Array.from(table.querySelectorAll("tr"))
                .slice(1)
                .map(tr => Array.from(tr.querySelectorAll("td")).map(td => td.textContent.trim()))
                .filter(row => row.length);

            parsed.push({ headers, rows });
        });

        return parsed;
    }

    function odv2ProcFindMetricFromPasoTable(tables, labelIncludes) {
        const label = String(labelIncludes || "").toLowerCase();

        for (const table of tables) {
            const h = table.headers.map(x => x.toLowerCase());

            if (!(h.includes("paso") && h.includes("cantidad"))) continue;

            for (const row of table.rows) {
                const first = String(row[0] || "").toLowerCase();

                if (first.includes(label)) {
                    return odv2ProcNum(row[1]);
                }
            }
        }

        return null;
    }

    function odv2ProcFindIndicator(tables, labelIncludes) {
        const label = String(labelIncludes || "").toLowerCase();

        for (const table of tables) {
            const h = table.headers.map(x => x.toLowerCase());

            if (!(h.includes("indicador") && h.includes("valor"))) continue;

            for (const row of table.rows) {
                const first = String(row[0] || "").toLowerCase();

                if (first.includes(label)) {
                    return odv2ProcNum(row[1]);
                }
            }
        }

        return null;
    }

    function odv2ProcSumColumn(tables, headerIncludes) {
        const target = String(headerIncludes || "").toLowerCase();

        for (const table of tables) {
            const idx = table.headers.findIndex(h => String(h || "").toLowerCase().includes(target));

            if (idx < 0) continue;

            let total = 0;
            let found = false;

            for (const row of table.rows) {
                const first = String(row[0] || "").trim().toLowerCase();

                if (first === "total") {
                    const nTotal = odv2ProcNum(row[idx]);
                    if (nTotal !== null) return nTotal;
                }

                const n = odv2ProcNum(row[idx]);

                if (n !== null) {
                    total += n;
                    found = true;
                }
            }

            if (found) return total;
        }

        return null;
    }

    function odv2ProcExtract(actionName, html, httpStatus) {
        const meta = ORION_PROC_META[actionName] || {};
        const text = odv2ProcStripHtml(html);
        const textLower = text.toLowerCase();
        const tables = odv2ProcTableRows(html);

        const ok = textLower.includes("procesado correctamente") ||
                   textLower.includes("procesados correctamente");

        const parsed = {
            actionName,
            tipo: meta.tipo || actionName,
            icono: meta.icono || "⚙️",
            esperado: meta.esperado || "",
            httpStatus,
            ok,
            mensaje: ok ? "Procesamiento completado correctamente." : "El procesamiento respondió con error o advertencia.",
            original: null,
            filtrado: null,
            consolidado: null,
            archivos: null,
            extra: [],
            rawHtml: html || ""
        };

        if (actionName === "procesar.discador") {
            parsed.original = odv2ProcFindMetricFromPasoTable(tables, "registros originales");
            parsed.filtrado = odv2ProcFindMetricFromPasoTable(tables, "tras filtro campaña");
            parsed.consolidado = odv2ProcFindMetricFromPasoTable(tables, "tras filtro estado");
            parsed.archivos = textLower.includes("discador usado") ? 1 : null;

            parsed.extra.push(["Fuente", "Archivo Discador"]);
            parsed.extra.push(["Salida esperada", "Reporte_Discador_*_Consolidado.xlsx"]);
        }

        if (actionName === "procesar.causales") {
            parsed.original = odv2ProcSumColumn(tables, "original");
            parsed.filtrado = odv2ProcSumColumn(tables, "tras evento");
            parsed.consolidado = odv2ProcFindIndicator(tables, "total filas consolidadas") || odv2ProcSumColumn(tables, "normalizados");
            parsed.archivos = odv2ProcFindIndicator(tables, "total archivos procesados");

            parsed.extra.push(["Fuente", "Carpeta Causales"]);
            parsed.extra.push(["Salida esperada", "Causales_Consolidado.xlsx"]);
        }

        if (actionName === "procesar.lotes") {
            parsed.original = odv2ProcSumColumn(tables, "filas orig");
            parsed.filtrado = odv2ProcSumColumn(tables, "filas tras piv");
            parsed.consolidado = parsed.filtrado;
            parsed.archivos = null;

            const lotesEncontradosMatch = text.match(/Valores únicos encontrados.*?(\d+)/i);
            if (lotesEncontradosMatch) {
                parsed.extra.push(["Valores únicos en Discador[Lote]", lotesEncontradosMatch[1]]);
            }

            parsed.extra.push(["Fuente", "Carpeta Lotes"]);
            parsed.extra.push(["Salida esperada", "Lotes consolidados"]);
        }

        return parsed;
    }

    function odv2ProcKpi(label, value, hint = "") {
        const display = value === null || value === undefined ? "--" : fmt(value);

        return `
            <div class="odv2-proc-kpi">
                <span>${escapeHtml(label)}</span>
                <strong>${display}</strong>
                ${hint ? `<em>${escapeHtml(hint)}</em>` : ""}
            </div>
        `;
    }

    function odv2ProcResumenTable(parsed) {
        const rows = [
            ["Tipo", parsed.tipo],
            ["HTTP", parsed.httpStatus],
            ["Estado", parsed.ok ? "Correcto" : "Revisar"],
            ["Archivo/Salida", parsed.esperado || "--"],
            ["Registros originales", parsed.original ?? "--"],
            ["Registros filtrados/procesados", parsed.filtrado ?? "--"],
            ["Registros consolidados", parsed.consolidado ?? "--"],
            ["Archivos procesados", parsed.archivos ?? "--"],
            ...parsed.extra
        ];

        return `
            <table class="odv2-table odv2-proc-table">
                <thead>
                    <tr>
                        <th>Indicador</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${escapeHtml(row[0])}</td>
                            <td>${escapeHtml(row[1])}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function odv2ProcPie(parsed) {
        const values = [
            { label: "Original", short: "Ori", color: "#0ea5ff", value: Number(parsed.original || 0) },
            { label: "Filtrado", short: "Fil", color: "#f59e0b", value: Number(parsed.filtrado || 0) },
            { label: "Consolidado", short: "Con", color: "#22c55e", value: Number(parsed.consolidado || 0) },
        ];

        const total = values.reduce((acc, item) => acc + item.value, 0);

        if (!total) {
            return `
                <div class="odv2-proc-pie-card">
                    <strong>Resumen visual</strong>
                    <div class="odv2-proc-pie-empty">--</div>
                </div>
            `;
        }

        let start = 0;

        const segments = values.map(item => {
            const pct = item.value / total * 100;
            const end = start + pct;
            const segment = `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        return `
            <div class="odv2-proc-pie-card">
                <strong>Resumen visual</strong>
                <div class="odv2-proc-pie-stage">
                    <div class="odv2-proc-pie" style="background: conic-gradient(${segments.join(", ")});">
                        <div class="odv2-proc-pie-center">
                            <b>${fmt(parsed.consolidado || parsed.filtrado || 0)}</b>
                            <span>Final</span>
                        </div>
                    </div>

                    ${values.map((item, idx) => `
                        <div class="odv2-proc-pie-value odv2-proc-pie-value-${idx}">
                            <i style="background:${item.color}"></i>
                            <span>${escapeHtml(item.short)}</span>
                            <b>${fmt(item.value)}</b>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function odv2ProcResultHtml(parsed) {
        return `
            <div class="odv2-proc-box ${parsed.ok ? "success" : "error"}">
                <div class="odv2-proc-head">
                    <div>
                        <h4>${parsed.icono} ${escapeHtml(parsed.tipo)}</h4>
                        <p>${escapeHtml(parsed.mensaje)}</p>
                    </div>
                    <span class="odv2-proc-chip ${parsed.ok ? "success" : "error"}">
                        ${parsed.ok ? "Correcto" : "Revisar"}
                    </span>
                </div>

                <div class="odv2-proc-kpis">
                    ${odv2ProcKpi("Original", parsed.original)}
                    ${odv2ProcKpi("Filtrado", parsed.filtrado)}
                    ${odv2ProcKpi("Consolidado", parsed.consolidado)}
                    ${odv2ProcKpi("Archivos", parsed.archivos)}
                </div>

                <div class="odv2-proc-layout">
                    <div class="odv2-proc-table-side">
                        <div class="odv2-proc-section-title">Resumen de procesamiento</div>
                        ${odv2ProcResumenTable(parsed)}
                    </div>

                    <div class="odv2-proc-visual-side">
                        ${odv2ProcPie(parsed)}
                    </div>
                </div>

                <details class="odv2-proc-details">
                    <summary>Ver detalle técnico original</summary>
                    <div class="odv2-proc-original">${parsed.rawHtml}</div>
                </details>
            </div>
        `;
    }

    async function ejecutarProcesamientoMvc(actionName, button) {
        const meta = ORION_V2_ACTION_MAP[actionName];

        if (!meta) {
            debug("Acción de procesamiento no encontrada: " + actionName, "error");
            return;
        }

        try {
            collectInputs();

            if (button) {
                button.disabled = true;
                button.classList.add("loading");
            }

            setPhaseStatus(actionName, "running", "Procesando");
            setPhaseResult(actionName, `<div class="odv2-result-loading">Procesando ${escapeHtml(ORION_PROC_META[actionName]?.tipo || actionName)}...</div>`);

            const url = meta.endpoint + "?" + getParams(true).toString();
            const response = await fetch(url + "&_=" + Date.now(), {
                method: "GET",
                credentials: "same-origin"
            });

            const html = await response.text();
            const parsed = odv2ProcExtract(actionName, html, response.status);

            setPhaseResult(actionName, odv2ProcResultHtml(parsed));
            setPhaseStatus(actionName, parsed.ok ? "success" : "error", parsed.ok ? "Completado" : "Revisar");

            debug(
                parsed.ok
                    ? `${parsed.tipo} procesado correctamente.`
                    : `${parsed.tipo} respondió con observaciones.`,
                parsed.ok ? "success" : "error"
            );

        } catch (error) {
            setPhaseStatus(actionName, "error", "Error");
            setPhaseResult(actionName, `<div class="odv2-result-error">Error procesando: ${escapeHtml(error.message || error)}</div>`);
            debug("Error en procesamiento MVC: " + (error.message || error), "error");

        } finally {
            if (button) {
                button.disabled = false;
                button.classList.remove("loading");
            }
        }
    }

    window.OrionProcesamientoMVC = {
        ejecutar: ejecutarProcesamientoMvc,
        extract: odv2ProcExtract
    };

/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_END === */
'''


def patch_js():
    title("1. PATCH JS - FASE E PROCESAMIENTO MVC")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = remove_block(original, JS_BEGIN, JS_END)

    marker = "    async function executeWorkflowAction(actionName, button) {"

    if marker not in text:
        raise RuntimeError("No encontré executeWorkflowAction en orion_diario_v2.js")

    text = text.replace(marker, js_block() + "\n\n" + marker, 1)

    guard = '''        if (ORION_PROC_ACTIONS.has(actionName)) {
            await ejecutarProcesamientoMvc(actionName, button);
            return;
        }

'''

    if guard.strip() not in text:
        text = text.replace(
            "    async function executeWorkflowAction(actionName, button) {\n",
            "    async function executeWorkflowAction(actionName, button) {\n" + guard,
            1,
        )

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: JS actualizado.")
    else:
        print("OK: JS sin cambios.")


def css_block():
    return r'''
/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_BEGIN === */

.odv2-proc-box {
    border: 1px solid #263752;
    border-radius: 16px;
    background: #07111f;
    padding: 14px;
}

.odv2-proc-box.success {
    border-color: rgba(34, 197, 94, .35);
}

.odv2-proc-box.error {
    border-color: rgba(248, 113, 113, .45);
}

.odv2-proc-head {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 12px;
}

.odv2-proc-head h4 {
    margin: 0;
    color: var(--cyan);
    font-size: 16px;
}

.odv2-proc-head p {
    margin: 5px 0 0;
    color: var(--muted);
    font-size: 13px;
}

.odv2-proc-chip {
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 900;
    white-space: nowrap;
}

.odv2-proc-chip.success {
    background: #052e16;
    border: 1px solid #22c55e;
    color: #86efac;
}

.odv2-proc-chip.error {
    background: #3f1212;
    border: 1px solid #f87171;
    color: #fecaca;
}

.odv2-proc-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(120px, 1fr));
    gap: 10px;
    margin-bottom: 14px;
}

.odv2-proc-kpi {
    border: 1px solid #263752;
    border-radius: 13px;
    background: #0b1222;
    padding: 10px;
}

.odv2-proc-kpi span {
    display: block;
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
}

.odv2-proc-kpi strong {
    display: block;
    margin-top: 4px;
    color: var(--cyan);
    font-size: 20px;
    line-height: 1;
}

.odv2-proc-kpi em {
    display: block;
    margin-top: 4px;
    color: var(--muted);
    font-size: 10px;
    font-style: normal;
}

.odv2-proc-layout {
    display: grid;
    grid-template-columns: minmax(420px, 1.1fr) minmax(240px, .9fr);
    gap: 14px;
    align-items: stretch;
}

.odv2-proc-table-side,
.odv2-proc-visual-side {
    border: 1px solid #263752;
    border-radius: 15px;
    background: #07111f;
    padding: 12px;
}

.odv2-proc-section-title {
    color: var(--cyan);
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 8px;
}

.odv2-proc-table {
    font-size: 12px;
}

.odv2-proc-table th,
.odv2-proc-table td {
    padding: 7px 8px;
}

.odv2-proc-pie-card {
    display: grid;
    justify-items: center;
    gap: 10px;
}

.odv2-proc-pie-card > strong {
    color: var(--text);
    font-size: 13px;
}

.odv2-proc-pie-stage {
    position: relative;
    width: 230px;
    height: 160px;
    display: grid;
    place-items: center;
}

.odv2-proc-pie {
    width: 105px;
    height: 105px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 1px solid #263752;
}

.odv2-proc-pie-center {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: #0b1222;
    border: 1px solid #263752;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 5px;
}

.odv2-proc-pie-center b {
    display: block;
    color: var(--text);
    font-size: 15px;
    line-height: 1;
}

.odv2-proc-pie-center span {
    display: block;
    color: var(--muted);
    font-size: 8.5px;
    font-weight: 900;
}

.odv2-proc-pie-value {
    position: absolute;
    display: grid;
    grid-template-columns: 8px auto auto;
    gap: 5px;
    align-items: center;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 999px;
    padding: 4px 7px;
    font-size: 10px;
    white-space: nowrap;
}

.odv2-proc-pie-value i {
    width: 7px;
    height: 7px;
    border-radius: 999px;
}

.odv2-proc-pie-value span {
    color: var(--muted);
    font-weight: 800;
}

.odv2-proc-pie-value b {
    color: var(--cyan);
    font-weight: 900;
}

.odv2-proc-pie-value-0 {
    top: 4px;
    right: 8px;
}

.odv2-proc-pie-value-1 {
    bottom: 4px;
    left: 12px;
}

.odv2-proc-pie-value-2 {
    top: 70px;
    right: 0;
}

.odv2-proc-pie-empty {
    width: 105px;
    height: 105px;
    border-radius: 50%;
    border: 1px dashed #334155;
    display: grid;
    place-items: center;
    color: var(--muted);
    font-size: 20px;
    font-weight: 900;
}

.odv2-proc-details {
    margin-top: 14px;
    border: 1px solid #263752;
    border-radius: 14px;
    background: #0b1222;
    padding: 10px 12px;
}

.odv2-proc-details summary {
    cursor: pointer;
    color: var(--cyan);
    font-weight: 900;
    font-size: 12px;
}

.odv2-proc-original {
    margin-top: 10px;
    overflow-x: auto;
}

.odv2-proc-original table,
.odv2-proc-original .dataframe {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
}

.odv2-proc-original th,
.odv2-proc-original td {
    border: 1px solid #263752;
    padding: 6px 7px;
}

@media (max-width: 1200px) {
    .odv2-proc-layout {
        grid-template-columns: 1fr;
    }

    .odv2-proc-kpis {
        grid-template-columns: repeat(2, minmax(120px, 1fr));
    }
}

@media (max-width: 700px) {
    .odv2-proc-kpis {
        grid-template-columns: 1fr;
    }
}

/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_END === */
'''


def patch_css():
    title("2. PATCH CSS - FASE E PROCESAMIENTO MVC")

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


def validate_python():
    title("3. VALIDACION PYTHON")

    targets = [
        ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py",
        ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py",
        ROOT / "app" / "__init__.py",
    ]

    subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in targets if p.exists()]],
        check=True,
    )

    print("OK: Python relacionado compila.")


def main():
    title("PATCH ORION DIARIO V2 - FASE E PROCESAMIENTO MVC")

    patch_js()
    patch_css()
    validate_python()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("")
    print("Validar:")
    print("  1. Ejecutar Procesar Discador")
    print("  2. Ejecutar Procesar Causales")
    print("  3. Ejecutar Procesar Lotes")
    print("  4. Ver KPIs, tabla resumen, pie y detalle técnico plegable")


if __name__ == "__main__":
    main()