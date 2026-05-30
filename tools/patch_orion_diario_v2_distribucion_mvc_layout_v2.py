from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_BEGIN = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_LAYOUT_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_LAYOUT_END === */"


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


def new_odv2_dist_render_summary():
    return r'''
    function odv2DistRenderSummary(copiados = null) {
        const root = document.getElementById("odv2-distribucion-mvc");
        if (!root) return;

        const data = odv2DistCollect();
        const copiedCounts = copiados || odv2DistEmptyCounts();

        const target = document.getElementById("odv2-dist-summary");

        if (!target) return;

        target.innerHTML = `
            <div class="odv2-dist-summary-layout">
                <div class="odv2-dist-summary-table-side">
                    <div class="odv2-dist-pies-title">Resumen de archivos</div>
                    ${odv2DistSummaryTable(data.encontrados, data.seleccionados, copiedCounts)}
                </div>

                <div class="odv2-dist-summary-pies-side">
                    <div class="odv2-dist-pies-title">Resumen visual</div>
                    <div class="odv2-dist-pies odv2-dist-pies-stacked">
                        ${odv2DistPie(data.seleccionados, "Antes")}
                        ${odv2DistPie(copiedCounts, "Después")}
                    </div>
                </div>
            </div>
        `;
    }
'''


def patch_js():
    title("1. PATCH JS - LAYOUT DISTRIBUCION MVC V2")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    # Reemplazar la función real existente.
    text = replace_function(text, "odv2DistRenderSummary", new_odv2_dist_render_summary())

    # Quitar el botón del encabezado superior si existe.
    text = re.sub(
        r'\s*<button\s+type="button"\s+id="odv2-dist-copy"\s+class="odv2-dist-copy-btn">\s*Copiar seleccionados\s*</button>',
        "",
        text,
        flags=re.I,
    )

    # Insertar botón antes del resumen, si aún no existe el bloque de acciones.
    if 'class="odv2-dist-actions"' not in text:
        marker = '<div id="odv2-dist-summary"></div>'

        if marker not in text:
            raise RuntimeError("No encontré <div id=\"odv2-dist-summary\"></div> para insertar el botón.")

        replacement = '''
                <div class="odv2-dist-actions">
                    <button type="button" id="odv2-dist-copy" class="odv2-dist-copy-btn">
                        Copiar seleccionados
                    </button>
                </div>

                <div id="odv2-dist-summary"></div>'''

        text = text.replace(marker, replacement, 1)

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: JS actualizado.")
    else:
        print("OK: JS sin cambios.")


def css_block():
    return r'''
/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_LAYOUT_BEGIN === */

.odv2-dist-head {
    align-items: flex-start;
}

.odv2-dist-actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin: 16px 0 14px;
    padding: 12px;
    border: 1px solid #263752;
    border-radius: 14px;
    background: #0b1222;
}

.odv2-dist-actions .odv2-dist-copy-btn {
    min-width: 220px;
}

.odv2-dist-summary-layout {
    display: grid;
    grid-template-columns: minmax(520px, 1.25fr) minmax(320px, .75fr);
    gap: 18px;
    align-items: start;
    margin-top: 10px;
}

.odv2-dist-summary-table-side,
.odv2-dist-summary-pies-side {
    border: 1px solid #263752;
    border-radius: 15px;
    background: #07111f;
    padding: 14px;
}

.odv2-dist-summary-table-side .odv2-dist-summary-table {
    margin-top: 10px;
}

.odv2-dist-pies-stacked {
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 14px !important;
    margin-top: 10px;
}

.odv2-dist-pies-stacked .odv2-dist-pie-card {
    min-height: 240px;
}

.odv2-dist-pies-stacked .odv2-dist-pie-stage {
    width: 280px;
    height: 190px;
}

.odv2-dist-pies-title {
    color: var(--cyan);
    font-weight: 900;
    font-size: 13px;
    margin-bottom: 8px;
}

@media (max-width: 1280px) {
    .odv2-dist-summary-layout {
        grid-template-columns: 1fr;
    }

    .odv2-dist-actions {
        justify-content: stretch;
    }

    .odv2-dist-actions .odv2-dist-copy-btn {
        width: 100%;
    }
}

/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_LAYOUT_END === */
'''


def patch_css():
    title("2. PATCH CSS - LAYOUT TABLA + PIES APILADOS")

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
    title("PATCH ORION DIARIO V2 - DISTRIBUCION MVC LAYOUT V2")

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
    print("  1. Ejecutar D - Distribuir archivos")
    print("  2. Ver tabla de archivos con checkboxes")
    print("  3. Ver botón Copiar seleccionados debajo de la tabla de archivos")
    print("  4. Ver tabla resumen al lado de los dos pies")
    print("  5. Ver los pies Antes y Después uno debajo del otro")


if __name__ == "__main__":
    main()