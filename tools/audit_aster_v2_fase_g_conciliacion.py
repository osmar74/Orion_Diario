from pathlib import Path
import sys
import re
import inspect
import importlib
import json

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

FILES = [
    "app/controllers/aster_blueprint.py",
    "app/controllers/aster_diario_v2_blueprint.py",
    "app/services/aster_reconciliation_service.py",
    "app/services/aster_classification_service.py",
    "app/services/aster_diario_v2_actions_service.py",
    "app/services/aster_renderer_service.py",
]

PATTERNS = [
    "conciliacion",
    "conciliación",
    "conciliar",
    "validacion",
    "validación",
    "aster-conciliacion",
    "aster-validacion",
    "accion_aster_conciliacion",
    "accion_aster_validacion",
    "entidades_aster",
    "exclu_entidades",
    "clasificacion",
    "bases_cobranza",
    "bases_integral",
    "no_seleccionadas",
    "removidos",
    "Excel",
    "xlsx",
]

MODULES = [
    "app.controllers.aster_blueprint",
    "app.services.aster_reconciliation_service",
    "app.services.aster_classification_service",
]

FUNCTION_HINTS = [
    "concili",
    "valid",
    "reconc",
    "clasificacion",
    "entidades",
    "excel",
    "compar",
]


def title(txt):
    print("\n" + "=" * 110)
    print(txt)
    print("=" * 110)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def compact(txt, n=260):
    return re.sub(r"\s+", " ", str(txt or "")).strip()[:n]


def search_files():
    title("1. BUSQUEDA EN ARCHIVOS FASE G")

    result = {}

    for rel in FILES:
        path = ROOT / rel
        print(f"\n--- {rel} ---")

        if not path.exists():
            print("NO EXISTE")
            result[rel] = {"exists": False, "matches": 0}
            continue

        lines = read(path).splitlines()
        total = 0

        for i, line in enumerate(lines, start=1):
            found = [p for p in PATTERNS if p.lower() in line.lower()]

            if found:
                total += 1
                print(f"L{i:04d}: {compact(line)}")

        result[rel] = {"exists": True, "matches": total}
        print("Coincidencias:", total)

    return result


def endpoint_context():
    title("2. CONTEXTO ENDPOINTS ANTIGUOS FASE G")

    path = ROOT / "app" / "controllers" / "aster_blueprint.py"

    if not path.exists():
        print("No existe aster_blueprint.py")
        return {}

    lines = read(path).splitlines()

    posibles = []

    for i, line in enumerate(lines):
        l = line.lower()
        if "def accion_aster" in l and (
            "concili" in l
            or "valid" in l
            or "final" in l
            or "reporte" in l
        ):
            posibles.append((i, line.strip()))

    data = {}

    if not posibles:
        print("No encontré endpoints obvios por nombre.")
        return data

    for idx, name_line in posibles:
        print(f"\n--- {name_line} ---")

        start = max(0, idx - 10)
        end = min(len(lines), idx + 140)
        snippet = []

        for n in range(start, end):
            marker = ">>" if n == idx else "  "
            line = f"{marker} L{n + 1:04d}: {lines[n][:260]}"
            snippet.append(line)
            print(line)

        data[name_line] = snippet

    return data


def inspect_modules():
    title("3. IMPORTS Y FIRMAS")

    output = {}

    for module_name in MODULES:
        print(f"\n--- {module_name} ---")

        try:
            module = importlib.import_module(module_name)
            print("IMPORT OK")
        except Exception as exc:
            print("IMPORT ERROR:", exc)
            output[module_name] = {"import": False, "error": str(exc)}
            continue

        funcs = {}

        for name, obj in inspect.getmembers(module, inspect.isfunction):
            lname = name.lower()

            if any(h.lower() in lname for h in FUNCTION_HINTS):
                try:
                    sig = str(inspect.signature(obj))
                except Exception:
                    sig = "?"

                funcs[name] = sig
                print(f"{name}{sig}")

        output[module_name] = {"import": True, "funciones": funcs}

    return output


def revisar_archivos_entidades():
    title("4. REVISION ARCHIVOS GENERADOS ENTIDADES")

    posibles = [
        ROOT / "data",
        Path("E:/data"),
        Path("D:/data"),
    ]

    encontrados = []

    for base in posibles:
        if not base.exists():
            continue

        for patron in [
            "**/Entidades/entidades_aster_*.xlsx",
            "**/Entidades/exclu_entidades_aster_*.xlsx",
            "**/Entidades/validacion_entidades_aster_*.json",
        ]:
            for p in base.glob(patron):
                try:
                    encontrados.append({
                        "ruta": str(p),
                        "size": p.stat().st_size,
                        "modified": p.stat().st_mtime,
                    })
                except Exception:
                    encontrados.append({"ruta": str(p)})

    encontrados = sorted(encontrados, key=lambda x: x.get("modified", 0), reverse=True)

    for item in encontrados[:20]:
        print(item)

    return encontrados[:50]


def main():
    title("AUDITORIA ASTER V2 - FASE G CONCILIACION / VALIDACION")

    data = {
        "files": search_files(),
        "endpoint_context": endpoint_context(),
        "modules": inspect_modules(),
        "archivos_entidades": revisar_archivos_entidades(),
    }

    out = ROOT / "tools" / "audit_aster_v2_fase_g_conciliacion_result.json"
    out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    title("FIN")
    print("Resultado guardado en:")
    print(out)
    print("")
    print("Pega la salida para preparar el patch JSON de Fase G.")


if __name__ == "__main__":
    main()