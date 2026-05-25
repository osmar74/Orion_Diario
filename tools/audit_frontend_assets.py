from pathlib import Path
import re
from collections import Counter, defaultdict


JS_FILES = [
    Path("app/static/js/main.js"),
    Path("app/static/js/orion.js"),
    Path("app/static/js/aster.js"),
    Path("app/static/js/consolidado.js"),
]

CSS_FILE = Path("app/static/css/deepblack.css")
BASE_HTML = Path("app/templates/base.html")
TEMPLATES_DIR = Path("app/templates")


FUNCTION_RE = re.compile(r"\bfunction\s+([a-zA-Z_$][\w$]*)\s*\(")
WINDOW_EXPORT_RE = re.compile(r"\bwindow\.([a-zA-Z_$][\w$]*)\s*=")
CSS_CLASS_DEF_RE = re.compile(r"(?<![a-zA-Z0-9_-])\.([a-zA-Z_-][\w-]*)\s*[{,]")
CLASS_ATTR_RE = re.compile(r'class="([^"]+)"')
STYLE_ATTR_RE = re.compile(r'style="[^"]*"', re.IGNORECASE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def print_ok(ok: bool, message: str) -> int:
    print(f"{'✅' if ok else '❌'} {message}")
    return 0 if ok else 1


def file_stats(path: Path) -> dict:
    text = read(path) if path.exists() else ""
    return {
        "path": path,
        "exists": path.exists(),
        "lines": len(text.splitlines()),
        "kb": round(len(text.encode("utf-8")) / 1024, 2),
        "text": text,
    }


def audit_files() -> int:
    errors = 0

    print("\n[1] Archivos frontend principales")

    for path in JS_FILES + [CSS_FILE, BASE_HTML]:
        errors += print_ok(path.exists(), str(path))

    print("\n[2] Tamaño de archivos")

    for path in JS_FILES + [CSS_FILE]:
        stats = file_stats(path)

        if not stats["exists"]:
            continue

        estado = "OK"

        if path.suffix == ".js" and stats["lines"] > 900:
            estado = "REVISAR"
        elif path.suffix == ".css" and stats["lines"] > 1200:
            estado = "REVISAR"

        print(
            f"{estado:8} {path} | {stats['lines']} líneas | {stats['kb']} KB"
        )

    return errors


def audit_script_order() -> int:
    errors = 0
    print("\n[3] Orden de scripts en base.html")

    if not BASE_HTML.exists():
        return 1

    html = read(BASE_HTML)

    expected = [
        "js/main.js",
        "js/orion.js",
        "js/aster.js",
        "js/consolidado.js",
    ]

    positions = []

    for item in expected:
        pos = html.find(item)
        positions.append(pos)
        errors += print_ok(pos != -1, f"{item} cargado")

    if all(pos != -1 for pos in positions):
        errors += print_ok(
            positions == sorted(positions),
            "Orden correcto: main.js → orion.js → aster.js → consolidado.js",
        )

    return errors


def audit_functions() -> int:
    print("\n[4] Funciones declaradas por archivo JS")

    all_functions = defaultdict(list)

    for path in JS_FILES:
        if not path.exists():
            continue

        text = read(path)
        functions = FUNCTION_RE.findall(text)

        print(f"\n{path}")
        print(f"  Total funciones: {len(functions)}")

        for fn in functions:
            all_functions[fn].append(str(path))

    duplicates = {
        fn: files
        for fn, files in all_functions.items()
        if len(files) > 1
    }

    print("\n[5] Funciones duplicadas entre JS")

    if not duplicates:
        print("✅ No se detectaron funciones duplicadas entre archivos JS.")
        return 0

    for fn, files in duplicates.items():
        print(f"❌ {fn}")
        for file in files:
            print(f"   - {file}")

    return len(duplicates)


def audit_window_exports() -> int:
    print("\n[6] Exports window.* por archivo")

    for path in JS_FILES:
        if not path.exists():
            continue

        text = read(path)
        exports = WINDOW_EXPORT_RE.findall(text)

        print(f"\n{path}")
        print(f"  Total exports: {len(exports)}")

        for export in exports:
            print(f"  - window.{export}")

    return 0


def collect_template_and_js_usage() -> set[str]:
    used = set()

    for root in [TEMPLATES_DIR, Path("app/static/js")]:
        if not root.exists():
            continue

        patterns = ["*.html"] if root == TEMPLATES_DIR else ["*.js"]

        for pattern in patterns:
            for path in root.rglob(pattern):
                text = read(path)

                for match in CLASS_ATTR_RE.finditer(text):
                    classes = match.group(1).split()

                    for cls in classes:
                        if cls:
                            used.add(cls.strip())

                # Captura usos comunes en JS: classList.add("x"), className = "x y"
                for quoted in re.findall(r'["\']([a-zA-Z_-][\w-]*(?:\s+[a-zA-Z_-][\w-]*)*)["\']', text):
                    for token in quoted.split():
                        if re.match(r"^[a-zA-Z_-][\w-]*$", token):
                            used.add(token)

    return used


def audit_css_classes() -> int:
    print("\n[7] CSS clases definidas vs usadas")

    if not CSS_FILE.exists():
        print("❌ No existe deepblack.css")
        return 1

    css = read(CSS_FILE)
    defined = set(CSS_CLASS_DEF_RE.findall(css))
    used = collect_template_and_js_usage()

    unused = sorted(
        cls for cls in defined
        if cls.startswith("ui-") and cls not in used
    )

    print(f"Clases CSS definidas: {len(defined)}")
    print(f"Clases detectadas en templates/js: {len(used)}")

    if not unused:
        print("✅ No se detectaron clases ui-* sin uso.")
        return 0

    print("⚠️ Clases ui-* posiblemente sin uso:")
    for cls in unused:
        print(f"  - .{cls}")

    print("Nota: puede haber falsos positivos si una clase se arma dinámicamente.")
    return 0


def audit_inline_styles() -> int:
    print("\n[8] Estilos inline en templates")

    if not TEMPLATES_DIR.exists():
        return 0

    findings = []

    for path in TEMPLATES_DIR.rglob("*.html"):
        lines = read(path).splitlines()

        for number, line in enumerate(lines, start=1):
            if STYLE_ATTR_RE.search(line):
                findings.append(f"{path}:{number}")

    if not findings:
        print("✅ No se detectaron style=\"...\" en templates.")
        return 0

    print("❌ Se detectaron estilos inline:")
    for item in findings:
        print(f"  - {item}")

    return len(findings)


def audit_external_references() -> int:
    print("\n[9] Referencias importantes")

    required_strings = {
        "main.js": [
            "function seleccionarModulo",
            "function guardarVistaModuloActual",
            "function restaurarVistaModuloCache",
        ],
        "orion.js": [
            "function ejecutarAccion",
            "function subirOCR",
            "function verificarCarga",
        ],
        "aster.js": [
            "function subirOCRAster",
            "function ejecutarFaseIAster",
        ],
        "consolidado.js": [
            "function ejecutarConsultaConsolidado",
            "function aplicarFiltroYExportar",
        ],
    }

    errors = 0

    for filename, strings in required_strings.items():
        path = Path("app/static/js") / filename
        text = read(path) if path.exists() else ""

        for value in strings:
            errors += print_ok(value in text, f"{filename}: {value}")

    return errors


def main() -> None:
    print("=" * 100)
    print("AUDITORÍA FRONTEND ASSETS")
    print("=" * 100)

    errors = 0
    errors += audit_files()
    errors += audit_script_order()
    errors += audit_functions()
    errors += audit_window_exports()
    errors += audit_css_classes()
    errors += audit_inline_styles()
    errors += audit_external_references()

    print("\n" + "=" * 100)

    if errors == 0:
        print("✅ Auditoría frontend assets OK.")
    else:
        print(f"❌ Auditoría frontend assets con {errors} punto(s) pendiente(s).")

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()