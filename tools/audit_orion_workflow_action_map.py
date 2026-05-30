from pathlib import Path
import re

ROOT = Path.cwd()

TARGETS = [
    ROOT / "app" / "static" / "js" / "orion_workflow.js",
    ROOT / "app" / "static" / "js" / "orion.js",
    ROOT / "app" / "controllers" / "fases_blueprint.py",
    ROOT / "app" / "controllers" / "carga_blueprint.py",
    ROOT / "app" / "controllers" / "ocr_blueprint.py",
]

ACTIONS = [
    "crear.carpetas",
    "verificar.red",
    "ocr.procesar",
    "ocr.consolidar",
    "distribuir.preparar",
    "distribuir.copiar",
    "procesar.discador",
    "procesar.causales",
    "procesar.lotes",
    "carga.causales.verificar",
    "carga.causales.insertar",
    "carga.lotes.verificar",
    "carga.lotes.insertar",
    "carga.discador.verificar",
    "carga.discador.insertar",
    "consolidado.gestion.consultar",
]


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def print_context(path: Path, line_no: int, radius: int = 12):
    lines = read(path).splitlines()
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)

    print(f"\n--- {path.relative_to(ROOT)} | contexto línea {line_no} ---")
    for n in range(start, end + 1):
        marker = ">>" if n == line_no else "  "
        print(f"{marker} {n:04d}: {lines[n - 1][:260]}")


def audit_action_strings():
    title("1. ACCIONES WORKFLOW EN JS / HTML / CONTROLADORES")

    bases = [
        ROOT / "app" / "static" / "js",
        ROOT / "app" / "templates",
        ROOT / "app" / "controllers",
    ]

    for action in ACTIONS:
        print(f"\n### ACTION: {action}")

        found = False

        for base in bases:
            if not base.exists():
                continue

            for path in base.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in [".js", ".html", ".py"]:
                    continue

                text = read(path)

                if action not in text:
                    continue

                found = True
                lines = text.splitlines()

                for i, line in enumerate(lines, start=1):
                    if action in line:
                        print(f"{path.relative_to(ROOT)}:{i}: {line.strip()[:240]}")

        if not found:
            print("No encontrada.")


def audit_fetch_urls():
    title("2. FETCH / POST / URLS EN JS")

    for path in [ROOT / "app" / "static" / "js" / "orion_workflow.js", ROOT / "app" / "static" / "js" / "orion.js"]:
        if not path.exists():
            print(f"No existe: {path.relative_to(ROOT)}")
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")
        lines = read(path).splitlines()

        for i, line in enumerate(lines, start=1):
            lower = line.lower()

            if (
                "fetch(" in lower
                or "postform" in lower
                or "posthtml" in lower
                or "/accion/" in line
                or "url:" in lower
                or ".open(" in lower
            ):
                print(f"{i:04d}: {line.strip()[:260]}")


def audit_flask_routes():
    title("3. RUTAS FLASK EN CONTROLADORES ORION")

    for path in [
        ROOT / "app" / "controllers" / "fases_blueprint.py",
        ROOT / "app" / "controllers" / "carga_blueprint.py",
        ROOT / "app" / "controllers" / "ocr_blueprint.py",
    ]:
        if not path.exists():
            print(f"No existe: {path.relative_to(ROOT)}")
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")
        lines = read(path).splitlines()

        for i, line in enumerate(lines, start=1):
            if ".route(" in line or "@ocr_bp.route" in line or "@carga_bp.route" in line or "@fases_ab_bp.route" in line:
                print_context(path, i, radius=4)


def audit_v2_current():
    title("4. ORION V2 ACTUAL")

    for path in [
        ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py",
        ROOT / "app" / "static" / "js" / "orion_diario_v2.js",
        ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py",
    ]:
        if not path.exists():
            print(f"No existe: {path.relative_to(ROOT)}")
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")
        lines = read(path).splitlines()

        for i, line in enumerate(lines, start=1):
            if (
                "route(" in line
                or "fetch(" in line
                or "data-action" in line
                or "odv2-run" in line
                or "alert(" in line
            ):
                print(f"{i:04d}: {line.strip()[:260]}")


def main():
    title("AUDITORIA EXACTA ORION WORKFLOW ACTION MAP")
    audit_action_strings()
    audit_fetch_urls()
    audit_flask_routes()
    audit_v2_current()

    title("FIN")
    print("Pega esta salida completa.")
    print("Con esto hacemos el bridge real v2: botones v2 -> endpoints actuales.")


if __name__ == "__main__":
    main()