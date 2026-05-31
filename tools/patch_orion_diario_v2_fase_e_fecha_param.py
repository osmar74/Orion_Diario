from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")


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


def patch_js():
    title("PATCH JS - FASE E USAR fecha=YYYYMMDD")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    old = '''            const url = meta.endpoint + "?" + getParams(true).toString();
            const response = await fetch(url + "&_=" + Date.now(), {
                method: "GET",
                credentials: "same-origin"
            });'''

    new = '''            const fechaProcesoActiva = (
                document.getElementById("odv2-fecha-proceso")?.value ||
                state.fechaProceso ||
                "20260429"
            ).trim();

            // Los endpoints antiguos de procesamiento usan principalmente "fecha".
            // También enviamos "fecha_proceso" para mantener compatibilidad con Orion v2.
            const params = getParams(true);
            params.set("fecha", fechaProcesoActiva);
            params.set("fecha_proceso", fechaProcesoActiva);
            params.set("mes_gestion", state.mesGestion || "");
            params.set("conexion", state.conexion || "local");

            state.fechaProceso = fechaProcesoActiva;
            saveState();

            const url = meta.endpoint + "?" + params.toString();

            const response = await fetch(url + "&_=" + Date.now(), {
                method: "GET",
                credentials: "same-origin"
            });'''

    if old not in text:
        raise RuntimeError(
            "No encontré el bloque exacto de fetch dentro de ejecutarProcesamientoMvc. "
            "Necesitamos revisar esa función."
        )

    text = text.replace(old, new, 1)

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: Fase E ahora envía fecha y fecha_proceso.")
    else:
        print("OK: JS sin cambios.")


def validate_python():
    title("VALIDACION PYTHON")

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
    title("PATCH ORION DIARIO V2 - FASE E FECHA PARAM")

    patch_js()
    validate_python()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("")
    print("Antes de probar, confirma que Fecha proceso sea 20260429.")
    print("Luego ejecuta:")
    print("  1. Procesar Discador")
    print("  2. Procesar Causales")
    print("  3. Procesar Lotes")


if __name__ == "__main__":
    main()