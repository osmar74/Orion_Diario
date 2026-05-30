from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

JS = ROOT / "app" / "static" / "js" / "orion_diario_v2.js"
CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_BEGIN = "/* === ORION_DIARIO_V2_DISTRIBUCION_PIES_FIX_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_DISTRIBUCION_PIES_FIX_END === */"


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


def patch_js():
    title("1. PATCH JS - PIE ANTES = TOTAL ENCONTRADOS")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    old = '${odv2DistPie(data.seleccionados, "Antes")}'
    new = '${odv2DistPie(data.encontrados, "Antes")}'

    if old not in text:
        raise RuntimeError(
            'No encontré el patrón del pie Antes con data.seleccionados. '
            'Revisa si el JS cambió.'
        )

    text = text.replace(old, new, 1)

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: Antes ahora usa Total encontrados.")
    else:
        print("OK: JS sin cambios.")


def css_block():
    return r'''
/* === ORION_DIARIO_V2_DISTRIBUCION_PIES_FIX_BEGIN === */

/* Reducir pies aprox. 30% */
.odv2-dist-pies-stacked .odv2-dist-pie-card,
.odv2-dist-pie-card {
    min-height: 165px !important;
    padding: 10px !important;
}

.odv2-dist-pies-stacked .odv2-dist-pie-stage,
.odv2-dist-pie-stage {
    width: 196px !important;
    height: 135px !important;
}

.odv2-dist-pie {
    width: 92px !important;
    height: 92px !important;
}

.odv2-dist-pie-center {
    width: 52px !important;
    height: 52px !important;
    padding: 4px !important;
}

.odv2-dist-pie-center b {
    font-size: 15px !important;
}

.odv2-dist-pie-center span {
    font-size: 8.5px !important;
}

.odv2-dist-pie-value {
    font-size: 9.5px !important;
    padding: 4px 7px !important;
    grid-template-columns: 8px auto auto !important;
    gap: 4px !important;
}

.odv2-dist-pie-value i {
    width: 7px !important;
    height: 7px !important;
}

/* Reposicionar etiquetas alrededor del pie reducido */
.odv2-dist-pie-value-0 {
    top: 2px !important;
    right: 6px !important;
}

.odv2-dist-pie-value-1 {
    bottom: 4px !important;
    left: 10px !important;
}

.odv2-dist-pie-value-2 {
    top: 60px !important;
    right: 0 !important;
}

.odv2-dist-pies-stacked {
    gap: 10px !important;
}

/* Hacer más compacto el panel visual derecho */
.odv2-dist-summary-pies-side {
    padding: 12px !important;
}

.odv2-dist-pie-card > strong {
    font-size: 12.5px !important;
}

/* === ORION_DIARIO_V2_DISTRIBUCION_PIES_FIX_END === */
'''


def patch_css():
    title("2. PATCH CSS - REDUCIR PIES 30%")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)
    text = remove_block(original, CSS_BEGIN, CSS_END).rstrip()
    text = text + "\n\n" + css_block().strip() + "\n"

    if text != original:
        backup(CSS)
        write(CSS, text)
        print("OK: CSS de pies reducido aplicado.")
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
    title("PATCH ORION DIARIO V2 - FIX PIES DISTRIBUCION")

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
    print("  - Pie Antes debe mostrar Total encontrados.")
    print("  - Pie Después debe mostrar Total copiados.")
    print("  - Pies aproximadamente 30% más pequeños.")


if __name__ == "__main__":
    main()
