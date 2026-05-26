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
        "/accion/gestion-consolidada/verificar-calidad",
        "/accion/gestion-consolidada/ajuste-no-contestan",
        "/accion/gestion-consolidada/limpiar-nota",
        "/accion/gestion-consolidada/compromiso",
        "/accion/gestion-consolidada/archivo-final",
        "/accion/gestion-consolidada/archivos-generados",
        "/accion/gestion-consolidada/cargar-sql",
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
        "gcEjecutarFaseC",
        "gcEjecutarFaseD",
        "gcEjecutarFaseE",
        "gcEjecutarFaseF",
        "gcEjecutarFaseG",
        "gcEjecutarFaseH",
        "gcEjecutarFaseI",
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


    print("\n[4] UX refinement v1D")
    css = read(APP / "static" / "css" / "deepblack.css")
    renderer = read(APP / "services" / "gestion_consolidada_renderer_service.py")

    for item in [
        "CONSOLIDAR GESTIÓN UX REFINEMENT v1D",
        "CONSOLIDAR GESTIÓN UX REFINEMENT v1D.2",
        "CONSOLIDAR GESTIÓN LAYOUT v1D.3",
        "CONSOLIDAR GESTIÓN LAYOUT v1D.4",
        "gc-collapse",
        "gc-values-grid-six",
        "gc-donut-card",
        "gc-state-section",
        "gc-donut-row-quality",
        "gc-work-layout",
        "gc-phase-sidebar",
    ]:
        if item in css or item in renderer:
            ok(f"UX OK: {item}")
        else:
            errors += fail(f"Falta UX: {item}")


    print("\n[5] v1J - acceso pantalla principal")
    index = read(APP / "templates" / "index.html")
    header = read(APP / "templates" / "partials" / "header.html")
    launcher = APP / "templates" / "partials" / "consolidar_gestion_launcher.html"
    css = read(APP / "static" / "css" / "deepblack.css")

    if launcher.exists():
        ok("Launcher Consolidar Gestión existe")
    else:
        errors += fail("No existe partial consolidar_gestion_launcher.html")

    if "/gestion-consolidada" in index or "gestion_consolidada.vista_gestion_consolidada" in index:
        ok("Index contiene acceso a Consolidar Gestión")
    else:
        errors += fail("Index no contiene acceso a Consolidar Gestión")

    if "Consolidar Gestión" in header or "gestion_consolidada.vista_gestion_consolidada" in header:
        ok("Header contiene acceso a Consolidar Gestión")
    else:
        print("⚠️ Header no contiene acceso a Consolidar Gestión; si la pantalla principal ya tiene launcher, no es crítico.")

    if "CONSOLIDAR GESTIÓN v1J" in css:
        ok("CSS v1J presente")
    else:
        errors += fail("Falta CSS v1J")

    print("\n" + "=" * 100)
    if errors:
        print(f"❌ Auditoría Consolidar Gestión con {errors} pendiente(s).")
    else:
        print("✅ Auditoría Consolidar Gestión v1A OK.")
    print("=" * 100)

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
