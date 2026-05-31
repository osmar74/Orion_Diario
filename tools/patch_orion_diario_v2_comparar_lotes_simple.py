from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_BEGIN = "/* === ORION_DIARIO_V2_COMPARAR_LOTES_SIMPLE_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_COMPARAR_LOTES_SIMPLE_END === */"


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


def replace_function(text: str, function_name: str, replacement: str) -> str:
    start, end = find_function_bounds(text, function_name)
    return text[:start] + replacement.strip() + text[end:]


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


def new_odv2_proc_result_html():
    return r'''
    function odv2ProcResultHtml(parsed) {
        if (parsed.actionName === "comparar.lotes") {
            return `
                <div class="odv2-proc-box odv2-comparar-lotes-simple ${parsed.ok ? "success" : "error"}">
                    <div class="odv2-proc-head">
                        <div>
                            <h4>${parsed.icono} ${escapeHtml(parsed.tipo)}</h4>
                            <p>Resultado de validación cruzada de lotes contra Discador.</p>
                        </div>
                    </div>

                    <details class="odv2-proc-details odv2-comparar-lotes-details" open>
                        <summary>Ver detalle técnico original</summary>
                        <div class="odv2-proc-original">${parsed.rawHtml}</div>
                    </details>
                </div>
            `;
        }

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
'''


def patch_js():
    title("1. PATCH JS - COMPARAR LOTES SIMPLE")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    text = replace_function(text, "odv2ProcResultHtml", new_odv2_proc_result_html())

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: Comparar Lotes ahora muestra solo detalle técnico.")
    else:
        print("OK: JS sin cambios.")


def css_block():
    return r'''
/* === ORION_DIARIO_V2_COMPARAR_LOTES_SIMPLE_BEGIN === */

.odv2-comparar-lotes-simple .odv2-proc-head {
    margin-bottom: 10px;
}

.odv2-comparar-lotes-simple .odv2-proc-head h4 {
    color: #fbbf24;
}

.odv2-comparar-lotes-details {
    margin-top: 8px !important;
}

.odv2-comparar-lotes-details[open] summary {
    margin-bottom: 10px;
}

.odv2-comparar-lotes-simple .odv2-proc-original {
    max-height: none;
}

.odv2-comparar-lotes-simple .odv2-proc-original table {
    font-size: 12px;
}

/* === ORION_DIARIO_V2_COMPARAR_LOTES_SIMPLE_END === */
'''


def patch_css():
    title("2. PATCH CSS - COMPARAR LOTES SIMPLE")

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
    title("PATCH ORION DIARIO V2 - COMPARAR LOTES SIMPLE")

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
    print("  1. Ejecutar Comparar Lotes")
    print("  2. Confirmar que no aparezcan KPIs, resumen de procesamiento ni pie visual.")
    print("  3. Confirmar que se muestre solo Ver detalle técnico original abierto.")


if __name__ == "__main__":
    main()