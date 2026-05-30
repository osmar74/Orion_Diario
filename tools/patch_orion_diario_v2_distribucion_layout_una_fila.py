from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

CSS = ROOT / "app" / "static" / "css" / "orion_diario_v2.css"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

CSS_BEGIN = "/* === ORION_DIARIO_V2_DISTRIBUCION_LAYOUT_UNA_FILA_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_DISTRIBUCION_LAYOUT_UNA_FILA_END === */"


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


def css_block():
    return r'''
/* === ORION_DIARIO_V2_DISTRIBUCION_LAYOUT_UNA_FILA_BEGIN === */

/* Resumen en una sola fila:
   tabla angosta + pie Antes + pie Después */
.odv2-dist-summary-layout {
    grid-template-columns: minmax(380px, 0.85fr) minmax(520px, 1.15fr) !important;
    gap: 14px !important;
    align-items: stretch !important;
}

.odv2-dist-summary-table-side,
.odv2-dist-summary-pies-side {
    padding: 11px !important;
}

/* Tabla más compacta para ganar ancho */
.odv2-dist-summary-table {
    font-size: 11px !important;
}

.odv2-dist-summary-table th,
.odv2-dist-summary-table td {
    padding: 6px 7px !important;
    white-space: nowrap;
}

.odv2-dist-summary-table th:first-child,
.odv2-dist-summary-table td:first-child {
    width: 90px;
}

.odv2-dist-summary-table th:not(:first-child),
.odv2-dist-summary-table td:not(:first-child) {
    text-align: center;
}

/* Los dos pies ahora van en la misma fila */
.odv2-dist-pies-stacked,
.odv2-dist-pies {
    grid-template-columns: repeat(2, minmax(210px, 1fr)) !important;
    gap: 10px !important;
    margin-top: 8px !important;
}

/* Pies más compactos */
.odv2-dist-pies-stacked .odv2-dist-pie-card,
.odv2-dist-pie-card {
    min-height: 155px !important;
    padding: 9px !important;
}

.odv2-dist-pies-stacked .odv2-dist-pie-stage,
.odv2-dist-pie-stage {
    width: 185px !important;
    height: 125px !important;
}

.odv2-dist-pie {
    width: 86px !important;
    height: 86px !important;
}

.odv2-dist-pie-center {
    width: 49px !important;
    height: 49px !important;
    padding: 3px !important;
}

.odv2-dist-pie-center b {
    font-size: 14px !important;
}

.odv2-dist-pie-center span {
    font-size: 8px !important;
}

.odv2-dist-pie-value {
    font-size: 9px !important;
    padding: 3px 6px !important;
    grid-template-columns: 7px auto auto !important;
    gap: 4px !important;
}

.odv2-dist-pie-value i {
    width: 6px !important;
    height: 6px !important;
}

/* Reposicionar etiquetas para el pie compacto */
.odv2-dist-pie-value-0 {
    top: 0 !important;
    right: 4px !important;
}

.odv2-dist-pie-value-1 {
    bottom: 2px !important;
    left: 8px !important;
}

.odv2-dist-pie-value-2 {
    top: 56px !important;
    right: 0 !important;
}

.odv2-dist-pie-card > strong {
    font-size: 12px !important;
}

/* En pantallas medianas vuelve a dos filas para evitar apretar demasiado */
@media (max-width: 1500px) {
    .odv2-dist-summary-layout {
        grid-template-columns: 1fr !important;
    }

    .odv2-dist-pies-stacked,
    .odv2-dist-pies {
        grid-template-columns: repeat(2, minmax(220px, 1fr)) !important;
    }
}

/* En pantallas pequeñas, un pie debajo del otro */
@media (max-width: 900px) {
    .odv2-dist-pies-stacked,
    .odv2-dist-pies {
        grid-template-columns: 1fr !important;
    }

    .odv2-dist-summary-table th,
    .odv2-dist-summary-table td {
        white-space: normal;
    }
}

/* === ORION_DIARIO_V2_DISTRIBUCION_LAYOUT_UNA_FILA_END === */
'''


def patch_css():
    title("1. PATCH CSS - TABLA Y PIES EN UNA FILA")

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
    title("2. VALIDACION PYTHON")

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
    title("PATCH ORION DIARIO V2 - DISTRIBUCION LAYOUT UNA FILA")

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
    print("  - Tabla resumen más angosta.")
    print("  - Pie Antes y Pie Después en la misma fila.")
    print("  - Todo el resumen debe entrar en una sola fila en pantallas anchas.")


if __name__ == "__main__":
    main()