from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import ast
import re

ROOT = Path.cwd()

BLUEPRINT = ROOT / "app" / "controllers" / "aster_blueprint.py"
SOURCE_SERVICE = ROOT / "app" / "services" / "aster_source_service.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

BAD_BEGIN = "# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_BEGIN ==="
BAD_END = "# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_END ==="

GOOD_BEGIN = "# === FIX_ASTER_PHASE_E_SAFE_FECHA_SQL_BEGIN ==="
GOOD_END = "# === FIX_ASTER_PHASE_E_SAFE_FECHA_SQL_END ==="


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path: Path):
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


def remove_block(text: str, begin: str, end: str):
    while begin in text:
        before = text.split(begin, 1)[0].rstrip()
        rest = text.split(begin, 1)[1]

        if end in rest:
            after = rest.split(end, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def build_safe_helper_block():
    block = '''
# === FIX_ASTER_PHASE_E_SAFE_FECHA_SQL_BEGIN ===
# Helper seguro para ASTER Fase E.
#
# Corrige:
# - KeyError: 'fecha_sql'
# - Default local/remoto para consulta ASTER
#
# Fecha generación: __TIMESTAMP__


def _aster_phase_e_request_dict_safe():
    data = {}

    try:
        from flask import request

        if request.is_json:
            payload = request.get_json(silent=True) or {}
            if isinstance(payload, dict):
                data.update(payload)

        try:
            data.update(request.form.to_dict())
        except Exception:
            pass

        try:
            data.update(request.args.to_dict())
        except Exception:
            pass

        try:
            data.update(request.values.to_dict())
        except Exception:
            pass

    except Exception:
        pass

    return data


def _aster_phase_e_fecha_sql_safe(default=None):
    if default is None:
        from datetime import date as _date
        default = _date.today().strftime("%Y-%m-%d")

    data = _aster_phase_e_request_dict_safe()

    for key in [
        "fecha_sql",
        "fecha",
        "fecha_gestion",
        "fechaGestion",
        "fecha_proceso",
        "fechaProceso",
        "dia",
    ]:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    try:
        from flask import session
        value = session.get("aster_fecha_sql")
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    return default


def _aster_phase_e_conexion_safe(default=None):
    import os

    if default is None:
        default = os.getenv("ASTER_CONEXION_DEFAULT", "local")

    data = _aster_phase_e_request_dict_safe()

    for key in [
        "conexion",
        "conexion_aster",
        "origen",
        "modo",
        "ambiente",
        "tipo_conexion",
    ]:
        value = data.get(key)

        if value is None or not str(value).strip():
            continue

        value = str(value).strip().lower()

        if value in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
            return "local"

        if value in ["remoto", "remote", "mysql", "produccion", "producción", "prod"]:
            return "remoto"

    default = str(default or "local").strip().lower()

    if default not in ["local", "remoto"]:
        return "local"

    return default


def _aster_phase_e_fecha_from_resultado(resultado):
    """
    Compatibilidad:
    - Algunos servicios devuelven resultado["fecha"].
    - Otros consumidores esperan resultado["fecha_sql"].
    """
    if not isinstance(resultado, dict):
        return _aster_phase_e_fecha_sql_safe()

    return str(
        resultado.get("fecha_sql")
        or resultado.get("fecha")
        or _aster_phase_e_fecha_sql_safe()
    )


# === FIX_ASTER_PHASE_E_SAFE_FECHA_SQL_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def insert_helper_safely(text: str):
    text = remove_block(text, GOOD_BEGIN, GOOD_END)

    helper = build_safe_helper_block()

    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        print("ERROR: aster_blueprint.py sigue sin compilar después de quitar el bloque malo.")
        print(f"Línea: {e.lineno}")
        print(f"Detalle: {e}")
        raise

    last_import_end = 0

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_end = max(last_import_end, getattr(node, "end_lineno", node.lineno))

    lines = text.splitlines()

    if last_import_end <= 0:
        # Fallback: antes del primer route o antes de Blueprint.
        for idx, line in enumerate(lines):
            if "Blueprint(" in line or ".route(" in line:
                last_import_end = idx
                break

    if last_import_end <= 0:
        last_import_end = 0

    lines.insert(last_import_end, "\n" + helper)

    return "\n".join(lines).rstrip() + "\n"


def repair_blueprint():
    title("1. REPARANDO app/controllers/aster_blueprint.py")

    if not BLUEPRINT.exists():
        raise FileNotFoundError(f"No existe: {BLUEPRINT}")

    original = read(BLUEPRINT)
    backup(BLUEPRINT)

    text = original

    # 1) Quitar helper mal insertado del fix anterior.
    text = remove_block(text, BAD_BEGIN, BAD_END)

    # 2) Insertar helper seguro en una posición válida.
    text = insert_helper_safely(text)

    # 3) Corregir acceso directo que causa KeyError.
    text = re.sub(
        r'(?m)^(\s*)fecha_sql\s*=\s*str\(\s*resultado\[\s*[\'"]fecha_sql[\'"]\s*\]\s*\)',
        r'\1fecha_sql = _aster_phase_e_fecha_from_resultado(resultado)',
        text,
    )

    # 4) Si quedó algún resultado["fecha_sql"], hacerlo seguro.
    text = re.sub(
        r'\bresultado\[\s*[\'"]fecha_sql[\'"]\s*\]',
        r'resultado.get("fecha_sql")',
        text,
    )

    write(BLUEPRINT, text)
    print("OK: aster_blueprint.py reparado.")


def repair_source_service():
    title("2. REPARANDO app/services/aster_source_service.py")

    if not SOURCE_SERVICE.exists():
        print("AVISO: No existe aster_source_service.py")
        return

    original = read(SOURCE_SERVICE)
    backup(SOURCE_SERVICE)

    text = original

    # Donde el servicio devuelve "fecha": fecha_sql, agregamos también "fecha_sql": fecha_sql.
    text = re.sub(
        r'("fecha"\s*:\s*fecha_sql\s*,\s*\n)(?!\s*"fecha_sql"\s*:)',
        r'\1        "fecha_sql": fecha_sql,\n',
        text,
    )

    if text != original:
        write(SOURCE_SERVICE, text)
        print("OK: aster_source_service.py ahora devuelve fecha y fecha_sql.")
    else:
        print("OK: aster_source_service.py ya estaba compatible o no requería cambios.")


def audit():
    title("3. AUDITORIA RAPIDA")

    for path in [BLUEPRINT, SOURCE_SERVICE]:
        print(f"\n--- {path.relative_to(ROOT)} ---")
        text = read(path)

        for i, line in enumerate(text.splitlines(), start=1):
            if "fecha_sql" in line or "fecha\": fecha_sql" in line or "fecha_sql\": fecha_sql" in line:
                print(f"{i:04d}: {line[:220]}")


def compile_files():
    title("4. COMPILACION")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(BLUEPRINT),
            str(SOURCE_SERVICE),
            str(ROOT / "app" / "services" / "aster_sql_entity_service.py"),
            str(ROOT / "app" / "services" / "aster_renderer_service.py"),
        ],
        check=True,
    )

    print("OK: ASTER compila correctamente.")


def main():
    title("REPAIR ASTER FASE E DESPUES DE FIX FALLIDO")

    repair_blueprint()
    repair_source_service()
    audit()
    compile_files()

    title("FINALIZADO")
    print("Ahora reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase E -> Ejecutar consulta SQL ASTER")
    print("")
    print("Para pruebas debe usar LOCAL:")
    print("  localhost\\SQL2025DEV / gestioncomercial_dev")


if __name__ == "__main__":
    main()