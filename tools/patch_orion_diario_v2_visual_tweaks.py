from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_BEGIN = "/* === ORION_DIARIO_V2_VISUAL_TWEAKS_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_VISUAL_TWEAKS_END === */"


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


def new_render_bars_as_pie():
    return r'''
    function renderBars(data) {
        const root = $("#odv2-bars");
        if (!root) return;

        root.innerHTML = "";

        const metricas = (data.metricas || [])
            .map(m => ({
                titulo: String(m.titulo || ""),
                valor: Number(m.valor || 0),
                detalle: String(m.detalle || "")
            }))
            .filter(m => !Number.isNaN(m.valor));

        const total = metricas.reduce((acc, item) => acc + Math.max(0, item.valor), 0);

        if (!metricas.length || total <= 0) {
            root.innerHTML = '<div class="odv2-empty">No hay datos suficientes para graficar.</div>';
            return;
        }

        const colors = [
            "#0ea5ff",
            "#22c55e",
            "#f59e0b",
            "#a855f7",
            "#ef4444",
            "#14b8a6"
        ];

        let start = 0;

        const segments = metricas.map((m, idx) => {
            const pct = Math.max(0, m.valor) / total * 100;
            const end = start + pct;
            const color = colors[idx % colors.length];
            const segment = `${color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        const pie = document.createElement("div");
        pie.className = "odv2-pie-wrap";
        pie.innerHTML = `
            <div class="odv2-pie" style="background: conic-gradient(${segments.join(", ")});">
                <div class="odv2-pie-center">
                    <strong>${fmt(total)}</strong>
                    <span>Total</span>
                </div>
            </div>
            <div class="odv2-pie-legend">
                ${metricas.map((m, idx) => {
                    const pct = total > 0 ? (Math.max(0, m.valor) / total * 100) : 0;
                    const color = colors[idx % colors.length];

                    return `
                        <div class="odv2-pie-legend-row">
                            <i style="background:${color}"></i>
                            <span>${escapeHtml(m.titulo)}</span>
                            <b>${fmt(m.valor)}</b>
                            <em>${pct.toFixed(1)}%</em>
                        </div>
                    `;
                }).join("")}
            </div>
        `;

        root.appendChild(pie);
    }
'''


def patch_js():
    title("1. PATCH JS - reemplazar barras por pie/donut")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    start, end = find_function_bounds(text, "renderBars")
    text = text[:start] + new_render_bars_as_pie() + text[end:]

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: renderBars ahora muestra pie/donut.")
    else:
        print("OK: JS sin cambios.")


def remove_css_block(text: str):
    while CSS_BEGIN in text:
        before = text.split(CSS_BEGIN, 1)[0].rstrip()
        rest = text.split(CSS_BEGIN, 1)[1]

        if CSS_END in rest:
            after = rest.split(CSS_END, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def css_block():
    return f'''
{CSS_BEGIN}

/* Panel estadístico más compacto */
.odv2-metrics {{
    grid-template-columns: repeat(4, minmax(120px, 1fr));
    gap: 10px;
    margin-bottom: 14px;
}}

.odv2-metric {{
    min-height: 92px;
    padding: 11px 12px;
    border-radius: 13px;
}}

.odv2-metric small {{
    font-size: 11px;
    line-height: 1.1;
}}

.odv2-metric strong {{
    margin-top: 5px;
    font-size: 21px;
    line-height: 1.05;
}}

.odv2-metric span {{
    margin-top: 5px;
    font-size: 10.5px;
    line-height: 1.25;
}}

/* Pie / donut compacto */
.odv2-pie-wrap {{
    display: grid;
    grid-template-columns: 170px 1fr;
    gap: 16px;
    align-items: center;
    margin-top: 8px;
}}

.odv2-pie {{
    width: 154px;
    height: 154px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 1px solid #263752;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.05), 0 18px 34px rgba(0,0,0,.25);
}}

.odv2-pie-center {{
    width: 92px;
    height: 92px;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 50%;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 8px;
}}

.odv2-pie-center strong {{
    display: block;
    font-size: 18px;
    line-height: 1;
    color: var(--text);
}}

.odv2-pie-center span {{
    display: block;
    margin-top: 2px;
    color: var(--muted);
    font-size: 10px;
    font-weight: 800;
}}

.odv2-pie-legend {{
    display: grid;
    gap: 7px;
}}

.odv2-pie-legend-row {{
    display: grid;
    grid-template-columns: 12px 1fr auto auto;
    gap: 8px;
    align-items: center;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 9px;
    padding: 7px 9px;
    font-size: 12px;
}}

.odv2-pie-legend-row i {{
    width: 10px;
    height: 10px;
    border-radius: 999px;
}}

.odv2-pie-legend-row span {{
    color: var(--text);
    font-weight: 700;
}}

.odv2-pie-legend-row b {{
    color: var(--cyan);
    font-weight: 900;
}}

.odv2-pie-legend-row em {{
    color: var(--muted);
    font-style: normal;
    font-size: 11px;
}}

/* Resultados de fases con tablas estilo origen/destino/BD/tabla */
.odv2-phase-result {{
    font-size: 12px;
}}

.odv2-result-html {{
    font-size: 12px;
    line-height: 1.35;
}}

.odv2-result-html table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    background: #0b1222;
    border: 1px solid #263752;
    border-radius: 12px;
    overflow: hidden;
    margin: 8px 0;
}}

.odv2-result-html table th,
.odv2-result-html table td {{
    border-bottom: 1px solid #263752;
    padding: 8px 9px;
    text-align: left;
    vertical-align: top;
}}

.odv2-result-html table th {{
    color: var(--cyan);
    background: #0b1222;
    font-size: 11.5px;
    font-weight: 900;
}}

.odv2-result-html table td {{
    color: var(--text);
}}

.odv2-result-html table tr:last-child td {{
    border-bottom: 0;
}}

.odv2-result-html .log-line,
.odv2-result-html .ui-result-block,
.odv2-result-html .orion-result-content,
.odv2-result-html .orion-info-card,
.odv2-result-html .orion-checklist {{
    font-size: 12px !important;
}}

.odv2-result-html .log-line {{
    border-radius: 9px;
    padding: 7px 9px;
    margin: 5px 0;
}}

/* Compactar badges de fases y panel lateral */
.odv2-phase-status {{
    padding: 3px 7px;
    font-size: 10.5px;
}}

.odv2-badge {{
    font-size: 10.5px;
}}

.odv2-phase-mini {{
    padding: 8px 9px;
    font-size: 12px;
}}

.odv2-phase-mini b {{
    padding: 3px 6px;
    font-size: 11px;
}}

@media (max-width: 1100px) {{
    .odv2-pie-wrap {{
        grid-template-columns: 1fr;
        justify-items: center;
    }}

    .odv2-pie-legend {{
        width: 100%;
    }}
}}

{CSS_END}
'''


def patch_css():
    title("2. PATCH CSS - badges compactos, pie y tablas de resultados")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)
    text = remove_css_block(original).rstrip() + "\n\n" + css_block().strip() + "\n"

    if text != original:
        backup(CSS)
        write(CSS, text)
        print("OK: CSS visual aplicado.")
    else:
        print("OK: CSS sin cambios.")


def compile_python_reference():
    title("3. VALIDACION RAPIDA")

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
    title("PATCH ORION DIARIO V2 - AJUSTES VISUALES")

    patch_js()
    patch_css()
    compile_python_reference()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("  http://127.0.0.1:5000/orion-diario-v2")
    print("")
    print("Validar:")
    print("  - Panel estadístico con tarjetas más pequeñas.")
    print("  - Gráfico tipo pie/donut pequeño.")
    print("  - Tablas dentro de A Crear Carpetas y B Verificar Red con estilo compacto.")


if __name__ == "__main__":
    main()