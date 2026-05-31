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

SERVICE_BEGIN = "# === ORION_DIARIO_V2_COMPARAR_LOTES_BEGIN ==="
SERVICE_END = "# === ORION_DIARIO_V2_COMPARAR_LOTES_END ==="

CSS_BEGIN = "/* === ORION_DIARIO_V2_COMPARAR_LOTES_BEGIN === */"
CSS_END = "/* === ORION_DIARIO_V2_COMPARAR_LOTES_END === */"


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


def patch_action_map(text: str) -> str:
    if '"comparar.lotes"' in text:
        return text

    old = '"procesar.lotes": { method: "GET", endpoint: "/accion/procesar-lotes" },'

    new = '''"procesar.lotes": { method: "GET", endpoint: "/accion/procesar-lotes" },
        "comparar.lotes": { method: "GET", endpoint: "/accion/comparar-lotes" },'''

    if old not in text:
        raise RuntimeError("No encontré procesar.lotes en ORION_V2_ACTION_MAP.")

    return text.replace(old, new, 1)


def patch_proc_actions(text: str) -> str:
    # Agregar comparar.lotes al set de procesamiento MVC si existe.
    if "const ORION_PROC_ACTIONS" in text:
        old = '''        "procesar.lotes"
    ]);'''

        new = '''        "procesar.lotes",
        "comparar.lotes"
    ]);'''

        if old in text and '"comparar.lotes"' not in text[text.find("const ORION_PROC_ACTIONS"):text.find("const ORION_PROC_META")]:
            text = text.replace(old, new, 1)

    # Agregar metadata visual.
    if "const ORION_PROC_META" in text and '"comparar.lotes":' not in text:
        old_meta = '''        "procesar.lotes": {
            tipo: "Lotes",
            icono: "🧩",
            esperado: "Lotes consolidados",
            color: "green"
        }'''

        new_meta = '''        "procesar.lotes": {
            tipo: "Lotes",
            icono: "🧩",
            esperado: "Lotes consolidados",
            color: "green"
        },
        "comparar.lotes": {
            tipo: "Comparar Lotes",
            icono: "⚖️",
            esperado: "Validación Lotes vs Discador",
            color: "orange"
        }'''

        if old_meta in text:
            text = text.replace(old_meta, new_meta, 1)

    return text


def patch_js():
    title("1. PATCH JS - REGISTRAR ACCION comparar.lotes")

    if not JS.exists():
        raise FileNotFoundError(f"No existe: {JS}")

    original = read(JS)
    text = original

    text = patch_action_map(text)
    text = patch_proc_actions(text)

    if text != original:
        backup(JS)
        write(JS, text)
        print("OK: JS actualizado con comparar.lotes.")
    else:
        print("OK: JS ya tenía comparar.lotes.")


def service_injector_block():
    return r'''
# === ORION_DIARIO_V2_COMPARAR_LOTES_BEGIN ===

def _odv2_accion_item(item):
    if not isinstance(item, dict):
        return ""

    return (
        item.get("accion")
        or item.get("action")
        or item.get("id")
        or item.get("codigo_accion")
        or ""
    )


def _odv2_crear_comparar_lotes_item():
    return {
        "codigo": "F4",
        "letra": "F4",
        "fase": "F",
        "titulo": "Comparar Lotes",
        "nombre": "Comparar Lotes",
        "descripcion": "Compara lotes procesados contra Discador para validar consistencia.",
        "detalle": "Validación cruzada Lotes vs Discador.",
        "accion": "comparar.lotes",
        "action": "comparar.lotes",
        "icono": "⚖️",
        "orden": 8.5,
    }


def _odv2_insertar_comparar_lotes_en_lista(lista):
    if not isinstance(lista, list):
        return False

    if any(_odv2_accion_item(item) == "comparar.lotes" for item in lista):
        return False

    idx_lotes = -1

    for idx, item in enumerate(lista):
        if _odv2_accion_item(item) == "procesar.lotes":
            idx_lotes = idx
            break

    if idx_lotes < 0:
        return False

    lista.insert(idx_lotes + 1, _odv2_crear_comparar_lotes_item())
    return True


def _odv2_asegurar_comparar_lotes(contexto):
    visitados = set()

    def walk(obj):
        oid = id(obj)

        if oid in visitados:
            return

        visitados.add(oid)

        if isinstance(obj, list):
            _odv2_insertar_comparar_lotes_en_lista(obj)

            for item in obj:
                walk(item)

            return

        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    walk(value)

    if isinstance(contexto, dict):
        walk(contexto)

    return contexto


try:
    _odv2_construir_contexto_original = construir_contexto_orion_v2

    def construir_contexto_orion_v2(*args, **kwargs):
        contexto = _odv2_construir_contexto_original(*args, **kwargs)
        return _odv2_asegurar_comparar_lotes(contexto)

except NameError:
    pass

# === ORION_DIARIO_V2_COMPARAR_LOTES_END ===
'''


def patch_service():
    title("2. PATCH SERVICE - AGREGAR COMPARAR LOTES AL CONTEXTO")

    if not SERVICE.exists():
        raise FileNotFoundError(f"No existe: {SERVICE}")

    original = read(SERVICE)
    text = remove_block(original, SERVICE_BEGIN, SERVICE_END).rstrip()

    # Este wrapper debe quedar al final del archivo para envolver construir_contexto_orion_v2
    text += "\n\n" + service_injector_block().strip() + "\n"

    if text != original:
        backup(SERVICE)
        write(SERVICE, text)
        print("OK: service actualizado.")
    else:
        print("OK: service sin cambios.")


def patch_css():
    title("3. PATCH CSS - ESTILO COMPARAR LOTES")

    if not CSS.exists():
        raise FileNotFoundError(f"No existe: {CSS}")

    original = read(CSS)
    text = remove_block(original, CSS_BEGIN, CSS_END).rstrip()

    block = r'''
/* === ORION_DIARIO_V2_COMPARAR_LOTES_BEGIN === */

[data-action="comparar.lotes"] {
    border-color: rgba(245, 158, 11, .35);
}

[data-action="comparar.lotes"] .odv2-phase-title,
[data-action="comparar.lotes"] h4 {
    color: #fbbf24;
}

/* === ORION_DIARIO_V2_COMPARAR_LOTES_END === */
'''

    text += "\n\n" + block.strip() + "\n"

    if text != original:
        backup(CSS)
        write(CSS, text)
        print("OK: CSS actualizado.")
    else:
        print("OK: CSS sin cambios.")


def validate_python():
    title("4. VALIDACION PYTHON")

    targets = [
        ROOT / "app" / "controllers" / "orion_diario_v2_blueprint.py",
        SERVICE,
        ROOT / "app" / "__init__.py",
    ]

    subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in targets if p.exists()]],
        check=True,
    )

    print("OK: Python relacionado compila.")


def main():
    title("PATCH ORION DIARIO V2 - AGREGAR COMPARAR LOTES V2")

    patch_js()
    patch_service()
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
    print("  1. Cargar contexto")
    print("  2. Ver Comparar Lotes en Estado de fases")
    print("  3. Ver Comparar Lotes en panel central")
    print("  4. Ejecutar Comparar Lotes")


if __name__ == "__main__":
    main()