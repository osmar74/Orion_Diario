from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

SERVICE = ROOT / "app" / "services" / "orion_diario_v2_dashboard_service.py"
JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

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
    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def patch_service_remove_total_metric():
    title("1. QUITANDO METRICA TOTAL ORION DEL BACKEND")

    if not SERVICE.exists():
        raise FileNotFoundError(f"No existe: {SERVICE}")

    original = read(SERVICE)
    text = original

    # Quitar bloque de métrica Total Orion dentro de "metricas".
    pattern = r'''\s*,?\s*\{\s*
\s*"titulo"\s*:\s*"Total Orion"\s*,\s*
\s*"valor"\s*:\s*total_cargado\s*,\s*
\s*"detalle"\s*:\s*"Suma de tablas principales Orion"\s*,?\s*
\s*\}'''

    text = re.sub(pattern, "", text, flags=re.MULTILINE)

    # Si quedó coma doble o coma antes de cierre, limpiar casos comunes.
    text = text.replace(",\n                ,", ",")
    text = re.sub(r",\s*\n\s*\]", "\n            ]", text)

    if text != original:
        backup(SERVICE)
        write(SERVICE, text)
        print("OK: se quitó la métrica Total Orion.")
    else:
        print("AVISO: No encontré métrica Total Orion o ya estaba quitada.")


def patch_js_pie_center():
    title("2. QUITANDO TOTAL DEL CENTRO DEL PIE")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    old = '''<div class="odv2-pie-center">
                    <strong>${fmt(total)}</strong>
                    <span>Total</span>
                </div>'''

    new = '''<div class="odv2-pie-center">
                    <strong>ORION</strong>
                    <span>Distribución</span>
                </div>'''

    text = text.replace(old, new)

    # Seguridad adicional si el bloque tiene espacios distintos.
    text = re.sub(
        r'''<div class="odv2-pie-center">\s*
\s*<strong>\$\{fmt\(total\)\}</strong>\s*
\s*<span>Total</span>\s*
\s*</div>''',
        '''<div class="odv2-pie-center">
                    <strong>ORION</strong>
                    <span>Distribución</span>
                </div>''',
        text,
        flags=re.MULTILINE,
    )

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: el pie ya no muestra el total.")
    else:
        print("AVISO: No encontré el centro del pie con total. Puede que el patch visual no esté aplicado todavía.")


def patch_css_smaller_badges():
    title("3. AJUSTANDO BADGES/TARJETAS MAS PEQUEÑAS")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)

    marker = "/* === ORION_DIARIO_V2_REMOVE_TOTAL_TWEAKS === */"

    if marker in original:
        print("OK: CSS ya tenía este ajuste.")
        return

    block = f"""
{marker}

.odv2-metrics {{
    grid-template-columns: repeat(3, minmax(120px, 1fr));
}}

.odv2-metric {{
    min-height: 78px !important;
    padding: 9px 10px !important;
}}

.odv2-metric strong {{
    font-size: 19px !important;
}}

.odv2-metric small {{
    font-size: 10.5px !important;
}}

.odv2-metric span {{
    font-size: 10px !important;
}}

.odv2-pie-center strong {{
    font-size: 15px !important;
    letter-spacing: .6px;
}}

.odv2-pie-center span {{
    font-size: 9.5px !important;
}}

@media (max-width: 1100px) {{
    .odv2-metrics {{
        grid-template-columns: 1fr;
    }}
}}
"""

    backup(CSS)
    write(CSS, original.rstrip() + "\n\n" + block.strip() + "\n")
    print("OK: CSS compacto aplicado.")


def compile_python():
    title("4. COMPILACION")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SERVICE),
            str(ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py"),
            str(ROOT / "app" / "__init__.py"),
        ],
        check=True,
    )

    print("OK: Python compila.")


def main():
    title("PATCH ORION DIARIO V2 - QUITAR TOTAL EN BADGES Y PIE")

    patch_service_remove_total_metric()
    patch_js_pie_center()
    patch_css_smaller_badges()
    compile_python()

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
    print("  - Ya no debe aparecer badge/tarjeta Total Orion.")
    print("  - El pie/donut ya no debe mostrar número total al centro.")
    print("  - Deben quedar solo Causales, Lotes y Discador.")


if __name__ == "__main__":
    main()