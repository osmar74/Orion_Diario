from pathlib import Path
import sys
import re


ROOT = Path(".")
APP = ROOT / "app"

FILES = [
    APP / "controllers" / "gestion_consolidada_blueprint.py",
    APP / "services" / "gestion_consolidada_service.py",
    APP / "services" / "gestion_consolidada_renderer_service.py",
    APP / "templates" / "gestion_consolidada.html",
    APP / "static" / "js" / "gestion_consolidada.js",
    APP / "static" / "css" / "deepblack.css",
]


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def ok(msg):
    print(f"✅ {msg}")


def fail(msg):
    print(f"❌ {msg}")
    return 1


def main():
    fecha = sys.argv[1] if len(sys.argv) > 1 else "20260429"
    fecha_limpia = re.sub(r"\D", "", fecha)[:8]

    print("=" * 100)
    print("AUDITORÍA CONSOLIDAR GESTIÓN v1A")
    print("=" * 100)

    errors = 0

    print("\n[1] Archivos requeridos")
    for path in FILES:
        if path.exists():
            ok(str(path))
        else:
            errors += fail(f"No existe {path}")

    print("\n[2] Rutas y acciones")
    bp = read(APP / "controllers" / "gestion_consolidada_blueprint.py")
    js = read(APP / "static" / "js" / "gestion_consolidada.js")

    for item in [
        "/gestion-consolidada",
        "/accion/gestion-consolidada/resumen",
        "/accion/gestion-consolidada/preparar",
        "/accion/gestion-consolidada/unir",
    ]:
        if item in bp:
            ok(f"Ruta backend OK: {item}")
        else:
            errors += fail(f"Falta ruta backend: {item}")

    for item in [
        "gcSeleccionarConexion",
        "gcCargarResumen",
        "gcEjecutarFaseA",
        "gcEjecutarFaseB",
    ]:
        if item in js:
            ok(f"Función JS OK: {item}")
        else:
            errors += fail(f"Falta función JS: {item}")

    print("\n[3] Archivos fuente esperados")
    ruta_orion = ROOT / "data" / fecha_limpia / "Orion" / "Salidas" / f"{fecha_limpia}_Gestion_orion.xlsx"
    ruta_aster = ROOT / "data" / fecha_limpia / "Aster" / f"aster_{fecha_limpia}" / "Gestion" / f"{fecha_limpia}_Gestion_aster.xlsx"

    if ruta_orion.exists():
        ok(f"ORION existe: {ruta_orion}")
    else:
        print(f"⚠️ ORION no existe aún: {ruta_orion}")

    if ruta_aster.exists():
        ok(f"ASTER existe: {ruta_aster}")
    else:
        print(f"⚠️ ASTER no existe aún: {ruta_aster}")

    print("\n" + "=" * 100)
    if errors:
        print(f"❌ Auditoría Consolidar Gestión con {errors} pendiente(s).")
    else:
        print("✅ Auditoría Consolidar Gestión v1A OK.")
    print("=" * 100)

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
