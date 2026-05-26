from pathlib import Path
import re
import sys


ROOT = Path(".")
APP = ROOT / "app"

BASE_HTML = APP / "templates" / "base.html"
MAIN_JS = APP / "static" / "js" / "main.js"
ORION_JS = APP / "static" / "js" / "orion.js"
ORION_WORKFLOW_JS = APP / "static" / "js" / "orion_workflow.js"
ASTER_JS = APP / "static" / "js" / "aster.js"
CONSOLIDADO_JS = APP / "static" / "js" / "consolidado.js"
CSS = APP / "static" / "css" / "deepblack.css"

ASTER_BP = APP / "controllers" / "aster_blueprint.py"

DATA_DIR = ROOT / "data"

ORION_PANELS = {
    "A Crear Carpetas": APP / "templates/partials/panels/panel_crear_carpetas.html",
    "B Verificar Red": APP / "templates/partials/panels/panel_verificar_red.html",
    "C OCR Totales": APP / "templates/partials/panels/panel_ocr.html",
    "D Distribuir": APP / "templates/partials/panels/panel_distribuir.html",
    "F Discador": APP / "templates/partials/panels/panel_discador.html",
    "F Causales": APP / "templates/partials/panels/panel_causales.html",
    "F Lotes": APP / "templates/partials/panels/panel_lotes.html",
    "F Comparar": APP / "templates/partials/panels/panel_comparar.html",
    "G Carga Causales": APP / "templates/partials/panels/panel_carga_causales.html",
    "G Carga Lotes": APP / "templates/partials/panels/panel_carga_lote.html",
    "G Carga Discador": APP / "templates/partials/panels/panel_carga_discador.html",
    "G Consolidado Orion": APP / "templates/partials/panels/panel_consolidado.html",
}

ORION_SIDEBARS = {
    "A/B": APP / "templates/partials/sidebar/fase_ingreso_carpetas.html",
    "C": APP / "templates/partials/sidebar/fase_ocr.html",
    "D": APP / "templates/partials/sidebar/fase_distribuir.html",
    "F": APP / "templates/partials/sidebar/fase_procesamiento.html",
    "G": APP / "templates/partials/sidebar/fase_carga.html",
}

ASTER_CRITICAL_PATTERNS = [
    "obtenerOCrearContenedorConexionAsterFaseH",
    "_asegurar_excel_entidades_aster_para_fase_i",
    "_ruta_excel_entidades_aster_para_fase_i",
    "entidades_aster_",
]

ORION_EXPECTED_ACTIONS = [
    "crear.carpetas",
    "verificar.red",
    "ocr.procesar",
    "ocr.consolidar",
    "distribuir.preparar",
    "distribuir.copiar",
    "procesar.discador",
    "procesar.causales",
    "procesar.lotes",
    "procesar.comparar",
    "carga.causales.verificar",
    "carga.causales.insertar",
    "carga.lotes.verificar",
    "carga.lotes.insertar",
    "carga.discador.verificar",
    "carga.discador.insertar",
    "consolidado.gestion.consultar",
]


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def ok(msg: str):
    print(f"✅ {msg}")


def warn(msg: str):
    print(f"⚠️ {msg}")


def fail(msg: str) -> int:
    print(f"❌ {msg}")
    return 1


def section(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def find_functions(text: str):
    return re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", text)


def audit_file_exists() -> int:
    section("[1] Archivos principales")
    errors = 0

    for path in [
        BASE_HTML,
        MAIN_JS,
        ORION_JS,
        ORION_WORKFLOW_JS,
        ASTER_JS,
        CONSOLIDADO_JS,
        CSS,
        ASTER_BP,
    ]:
        if path.exists():
            ok(str(path))
        else:
            errors += fail(f"No existe {path}")

    return errors


def audit_script_order() -> int:
    section("[2] Orden de scripts en base.html")
    errors = 0

    base = read(BASE_HTML)

    scripts = [
        "js/main.js",
        "js/orion.js",
        "js/aster.js",
        "js/consolidado.js",
        "js/orion_workflow.js",
    ]

    positions = {}

    for script in scripts:
        pos = base.find(script)
        positions[script] = pos

        if pos >= 0:
            ok(f"{script} cargado")
        else:
            errors += fail(f"{script} no cargado")

    if all(positions[s] >= 0 for s in scripts):
        if positions["js/main.js"] < positions["js/orion.js"] < positions["js/aster.js"] < positions["js/consolidado.js"] < positions["js/orion_workflow.js"]:
            ok("Orden correcto: main.js → orion.js → aster.js → consolidado.js → orion_workflow.js")
        else:
            errors += fail("Orden incorrecto de scripts. orion_workflow.js debe cargar después de consolidado.js.")

    return errors


def audit_orion_workflow_actions() -> int:
    section("[3] ORION Workflow Engine - acciones registradas")
    errors = 0

    workflow = read(ORION_WORKFLOW_JS)

    for action in ORION_EXPECTED_ACTIONS:
        if action in workflow:
            ok(f"Acción OK: {action}")
        else:
            errors += fail(f"Falta acción en orion_workflow.js: {action}")

    required_functions = [
        "ejecutarWorkflowOrion",
        "abrirWorkflowOrion",
        "actualizarEstadoWorkflowDirecto",
        "actualizarEstadoFaseCDirecto",
        "actualizarEstadoFaseDDirecto",
        "actualizarEstadoFaseFDirecto",
        "actualizarEstadoFaseGDirecto",
        "obtenerFechaConsolidadoWorkflow",
        "seleccionarConexionConsolidadoWorkflow",
    ]

    for fn in required_functions:
        if f"function {fn}" in workflow:
            ok(f"Función workflow OK: {fn}")
        else:
            errors += fail(f"Falta función workflow: {fn}")

    return errors


def audit_orion_panels() -> int:
    section("[4] ORION paneles workflow-managed")
    errors = 0

    for name, path in ORION_PANELS.items():
        html = read(path)

        if not path.exists():
            errors += fail(f"{name}: no existe {path}")
            continue

        if 'data-orion-workflow-managed="1"' in html:
            ok(f"{name}: workflow-managed")
        else:
            errors += fail(f"{name}: falta data-orion-workflow-managed=\"1\"")

        if "ejecutarWorkflowOrion(" in html:
            ok(f"{name}: ejecuta por workflow")
        else:
            errors += fail(f"{name}: no usa ejecutarWorkflowOrion")

    return errors


def audit_orion_sidebars() -> int:
    section("[5] ORION sidebars solo navegación")
    errors = 0

    prohibited = [
        "ejecutarAccion(",
        "verificarCarga(",
        "insertarDatos(",
        "subirOCR(",
        "consolidarTotales(",
        "copiarDistribucionSeleccionada(",
    ]

    for name, path in ORION_SIDEBARS.items():
        html = read(path)

        if not path.exists():
            errors += fail(f"Sidebar {name}: no existe {path}")
            continue

        if "abrirWorkflowOrion(" in html:
            ok(f"Sidebar {name}: usa abrirWorkflowOrion")
        else:
            errors += fail(f"Sidebar {name}: no usa abrirWorkflowOrion")

        for item in prohibited:
            if item in html:
                errors += fail(f"Sidebar {name}: todavía ejecuta lógica vieja: {item}")

    return errors


def audit_duplicates() -> int:
    section("[6] Duplicados JS críticos")
    errors = 0

    for path in [MAIN_JS, ORION_JS, ORION_WORKFLOW_JS, ASTER_JS, CONSOLIDADO_JS]:
        text = read(path)
        funcs = find_functions(text)
        repeated = sorted({fn for fn in funcs if funcs.count(fn) > 1})

        if repeated:
            for fn in repeated:
                errors += fail(f"{path}: función duplicada {fn}")
        else:
            ok(f"{path}: sin funciones duplicadas")

    return errors


def audit_orion_legacy_canonical() -> int:
    section("[7] ORION legacy compatibility canónico")
    errors = 0

    orion = read(ORION_JS)

    required = [
        "ORION LEGACY COMPATIBILITY CANÓNICO",
        "function obtenerPanelResultadoDistribucionOrion",
        "function obtenerChecksDistribucionOrion",
        "function valorCheckboxDistribucionOrion",
        "function obtenerSeleccionadosDistribucionOrion",
        "function htmlEsNotFoundOrion",
        "function mostrarIngresoManualOrion",
    ]

    for item in required:
        if item in orion:
            ok(f"Presente: {item}")
        else:
            errors += fail(f"Falta: {item}")

    if "data-orion-workflow-managed" in orion:
        ok("orion.js ignora paneles workflow-managed")
    else:
        errors += fail("orion.js no contiene protección workflow-managed")

    return errors


def audit_aster_h_i(fecha: str) -> int:
    section("[8] ASTER Fase H/I")
    errors = 0

    aster_js = read(ASTER_JS)
    aster_bp = read(ASTER_BP)

    checks = {
        "ASTER H helper JS": ("obtenerOCrearContenedorConexionAsterFaseH", aster_js),
        "ASTER H export JS": ("window.obtenerOCrearContenedorConexionAsterFaseH", aster_js),
        "ASTER I asegurar Excel": ("_asegurar_excel_entidades_aster_para_fase_i", aster_bp),
        "ASTER I ruta Excel": ("_ruta_excel_entidades_aster_para_fase_i", aster_bp),
        "ASTER I entidades_aster": ("entidades_aster_", aster_bp),
    }

    for label, (pattern, text) in checks.items():
        if pattern in text:
            ok(f"{label}: OK")
        else:
            errors += fail(f"{label}: falta {pattern}")

    if fecha:
        fecha_limpia = re.sub(r"\D", "", fecha)

        if len(fecha_limpia) >= 8:
            fecha_limpia = fecha_limpia[:8]

            ruta = (
                DATA_DIR
                / fecha_limpia
                / "Aster"
                / f"aster_{fecha_limpia}"
                / "Entidades"
                / f"entidades_aster_{fecha_limpia}.xlsx"
            )

            if ruta.exists():
                ok(f"Archivo entidades existe: {ruta}")
            else:
                errors += fail(f"No existe archivo entidades: {ruta}")
        else:
            errors += fail(f"Fecha inválida para validar entidades: {fecha}")

    return errors


def audit_inline_styles() -> int:
    section("[9] Estilos inline en templates")
    errors = 0

    templates = list((APP / "templates").rglob("*.html"))
    findings = []

    for path in templates:
        text = read(path)

        for i, line in enumerate(text.splitlines(), start=1):
            if "style=" in line.lower():
                findings.append((path, i, line.strip()))

    if not findings:
        ok("No se encontraron style=\"...\" en templates")
    else:
        for path, i, line in findings:
            errors += fail(f"{path}:{i}: {line}")

    return errors


def main():
    fecha = sys.argv[1] if len(sys.argv) > 1 else ""

    print("=" * 100)
    print("AUDITORÍA INTEGRAL WORKFLOW ORION + ASTER")
    print("=" * 100)

    errors = 0
    errors += audit_file_exists()
    errors += audit_script_order()
    errors += audit_orion_workflow_actions()
    errors += audit_orion_panels()
    errors += audit_orion_sidebars()
    errors += audit_duplicates()
    errors += audit_orion_legacy_canonical()
    errors += audit_aster_h_i(fecha)
    errors += audit_inline_styles()

    print()
    print("=" * 100)

    if errors:
        print(f"❌ Auditoría integral con {errors} pendiente(s).")
    else:
        print("✅ Auditoría integral OK.")

    print("=" * 100)

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()