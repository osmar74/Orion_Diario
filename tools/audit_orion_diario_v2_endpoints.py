from pathlib import Path
import re
import sys

ROOT = Path.cwd()
APP_DIR = ROOT / "app"

KEYWORDS = [
    "orion",
    "causales",
    "lotes",
    "lote",
    "discador",
    "ocr",
    "totales",
    "distribuir",
    "consolidado",
    "crear carpetas",
    "verificar red",
    "carga",
]


def title(text):
    print("\n" + "=" * 100)
    print(text)
    print("=" * 100)


def read(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def audit_flask_routes():
    title("1. RUTAS FLASK REGISTRADAS")

    sys.path.insert(0, str(ROOT))

    try:
        from app import create_app

        app = create_app()

        routes = []

        for rule in app.url_map.iter_rules():
            item = {
                "rule": str(rule),
                "endpoint": rule.endpoint,
                "methods": ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"})),
            }

            text = f"{item['rule']} {item['endpoint']}".lower()

            if any(k in text for k in KEYWORDS):
                routes.append(item)

        if not routes:
            print("No encontré rutas relacionadas con Orion por keywords.")
            return

        for r in sorted(routes, key=lambda x: x["rule"]):
            print(f"{r['methods']:10s} {r['rule']:60s} -> {r['endpoint']}")

    except Exception as exc:
        print("No se pudo importar create_app o listar rutas.")
        print("ERROR:", exc)


def audit_templates_and_js():
    title("2. BÚSQUEDA EN TEMPLATES / JS / CONTROLADORES")

    files = []

    for base in [
        APP_DIR / "templates",
        APP_DIR / "static",
        APP_DIR / "controllers",
        APP_DIR / "services",
    ]:
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in [".py", ".html", ".js"]:
                continue

            text = read(path)
            lower = text.lower()

            score = sum(1 for k in KEYWORDS if k in lower)

            if score >= 2:
                files.append((score, path))

    files.sort(reverse=True, key=lambda x: x[0])

    for score, path in files:
        print(f"\n--- {path.relative_to(ROOT)} | score={score} ---")

        lines = read(path).splitlines()

        for i, line in enumerate(lines, start=1):
            lower = line.lower()

            if any(k in lower for k in KEYWORDS):
                clean = line.strip()

                if len(clean) > 260:
                    clean = clean[:260] + "..."

                print(f"{i:04d}: {clean}")


def audit_orion_v2_files():
    title("3. ARCHIVOS ORION V2 ACTUALES")

    targets = [
        APP_DIR / "controllers" / "orion_diario_v2_blueprint.py",
        APP_DIR / "services" / "orion_diario_v2_dashboard_service.py",
        APP_DIR / "templates" / "orion_diario_v2" / "index.html",
        APP_DIR / "static" / "js" / "orion_diario_v2.js",
        APP_DIR / "static" / "css" / "orion_diario_v2.css",
    ]

    for path in targets:
        print(f"{path.relative_to(ROOT)}:", "OK" if path.exists() else "NO EXISTE")


def main():
    title("AUDITORÍA INTEGRACIÓN GESTIÓN DIARIA ORION V2")

    audit_orion_v2_files()
    audit_flask_routes()
    audit_templates_and_js()

    title("FIN")
    print("Pégame esta salida completa.")
    print("Con esto hacemos el siguiente script para conectar botones v2 a endpoints reales.")


if __name__ == "__main__":
    main()