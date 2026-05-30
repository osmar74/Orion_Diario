from pathlib import Path
from datetime import datetime, date
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

ENV_FILE = ROOT / ".env"
ASTER_BLUEPRINT = ROOT / "app" / "controllers" / "aster_blueprint.py"
ASTER_SOURCE_SERVICE = ROOT / "app" / "services" / "aster_source_service.py"
ASTER_RENDERER_SERVICE = ROOT / "app" / "services" / "aster_renderer_service.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

MARKER_BEGIN = "# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_BEGIN ==="
MARKER_END = "# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_END ==="


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def backup(path: Path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def read(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def parse_env(text):
    data = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")

    return data


def mask(key, value):
    if "PASSWORD" in key.upper() or "PWD" in key.upper():
        return "***"
    return value


def update_env():
    title("1. ACTUALIZANDO .env PARA ASTER LOCAL / REMOTO")

    original = read(ENV_FILE) if ENV_FILE.exists() else ""

    required = {
        # ASTER local: reemplazo local de MySQL remoto
        "ASTER_CONEXION_DEFAULT": "local",
        "ASTER_LOCAL_DRIVER": "ODBC Driver 18 for SQL Server",
        "ASTER_LOCAL_SERVER": r"localhost\SQL2025DEV",
        "ASTER_LOCAL_DATABASE": "gestioncomercial_dev",
        "ASTER_LOCAL_USER": "Admin1",
        "ASTER_LOCAL_PASSWORD": "1234",

        # También se mantiene la familia SQLSERVER_* usada por aster_source_service.py
        "SQLSERVER_DRIVER": "ODBC Driver 18 for SQL Server",
        "SQLSERVER_SERVER": r"localhost\SQL2025DEV",
        "SQLSERVER_DATABASE": "gestioncomercial_dev",
        "SQLSERVER_USER": "Admin1",
        "SQLSERVER_PASSWORD": "1234",

        # ASTER remoto: NO usar para pruebas salvo que lo elijas explícitamente
        "ASTER_REMOTE_HOST": "10.24.90.101",
    }

    lines = original.splitlines()
    written = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        key = stripped.split("=", 1)[0].strip()

        if key in required:
            new_lines.append(f"{key}={required[key]}")
            written.add(key)
        else:
            new_lines.append(line)

    missing = [key for key in required if key not in written]

    if missing:
        new_lines.append("")
        new_lines.append("# ASTER FASE E - LOCAL / REMOTO")
        for key in missing:
            new_lines.append(f"{key}={required[key]}")

    new_text = "\n".join(new_lines).rstrip() + "\n"

    if new_text != original:
        backup(ENV_FILE)
        write(ENV_FILE, new_text)
        print("OK: .env actualizado.")
    else:
        print("OK: .env ya estaba correcto.")

    env = parse_env(new_text)

    print("\nVariables ASTER principales:")
    for key in [
        "ASTER_CONEXION_DEFAULT",
        "ASTER_LOCAL_SERVER",
        "ASTER_LOCAL_DATABASE",
        "ASTER_LOCAL_USER",
        "ASTER_LOCAL_PASSWORD",
        "SQLSERVER_SERVER",
        "SQLSERVER_DATABASE",
        "SQLSERVER_USER",
        "SQLSERVER_PASSWORD",
        "ASTER_REMOTE_HOST",
    ]:
        print(f"- {key}={mask(key, env.get(key, ''))}")


def remove_old_block(text):
    if MARKER_BEGIN not in text:
        return text

    before = text.split(MARKER_BEGIN, 1)[0].rstrip()
    rest = text.split(MARKER_BEGIN, 1)[1]

    if MARKER_END in rest:
        after = rest.split(MARKER_END, 1)[1].lstrip()
        return before + "\n\n" + after

    return before + "\n"


def build_blueprint_helper_block():
    block = '''
# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_BEGIN ===
# Helper defensivo para ASTER Fase E.
#
# Corrige:
# - KeyError: 'fecha_sql'
# - Selección local/remoto para consulta SQL ASTER
#
# Local:
#   SQL Server localhost\\SQL2025DEV / gestioncomercial_dev
#
# Remoto:
#   Servidor ASTER remoto, por ejemplo 10.24.90.101
#
# Fecha generación: __TIMESTAMP__


def _aster_phase_e_request_dict():
    """
    Obtiene datos enviados por fetch/ajax/form sin romper si falta JSON.
    """
    data = {}

    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            if isinstance(payload, dict):
                data.update(payload)
    except Exception:
        pass

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

    return data


def _aster_phase_e_fecha_sql(default=None):
    """
    Retorna fecha_sql de forma segura.
    Si el frontend no la envía, usa la fecha actual en formato YYYY-MM-DD.
    """
    if default is None:
        default = date.today().strftime("%Y-%m-%d")

    data = _aster_phase_e_request_dict()

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

    return default


def _aster_phase_e_conexion(default=None):
    """
    Retorna conexión ASTER segura: local/remoto.
    Por defecto LOCAL, para no consultar producción accidentalmente.
    """
    import os

    if default is None:
        default = os.getenv("ASTER_CONEXION_DEFAULT", "local")

    data = _aster_phase_e_request_dict()

    for key in [
        "conexion",
        "conexion_aster",
        "origen",
        "modo",
        "ambiente",
        "tipo_conexion",
    ]:
        value = data.get(key)
        if value is not None and str(value).strip():
            value = str(value).strip().lower()

            if value in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
                return "local"

            if value in ["remoto", "remote", "mysql", "produccion", "producción", "prod"]:
                return "remoto"

    default = str(default or "local").strip().lower()

    if default not in ["local", "remoto"]:
        return "local"

    return default


def _aster_phase_e_normalizar_payload(payload=None):
    """
    Garantiza que cualquier payload tenga fecha_sql y conexion.
    """
    if payload is None or not isinstance(payload, dict):
        payload = {}

    payload.setdefault("fecha_sql", _aster_phase_e_fecha_sql())
    payload.setdefault("conexion", _aster_phase_e_conexion())

    return payload


# === FIX_ASTER_PHASE_E_FECHA_SQL_CONEXION_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def insert_helper_in_blueprint():
    title("2. INSERTANDO HELPER EN aster_blueprint.py")

    if not ASTER_BLUEPRINT.exists():
        raise FileNotFoundError(f"No existe: {ASTER_BLUEPRINT}")

    original = read(ASTER_BLUEPRINT)
    text = remove_old_block(original)

    if not re.search(r"^\s*from\s+datetime\s+import\s+", text, flags=re.M):
        text = "from datetime import date, datetime\n" + text
    else:
        # asegurar date
        text = re.sub(
            r"from datetime import ([^\n]+)",
            lambda m: m.group(0) if "date" in m.group(1) else m.group(0) + ", date",
            text,
            count=1,
        )

    if "from flask import" in text and "request" not in text.split("from flask import", 1)[1].splitlines()[0]:
        text = re.sub(
            r"from flask import ([^\n]+)",
            lambda m: "from flask import " + m.group(1).rstrip() + ", request",
            text,
            count=1,
        )
    elif "from flask import" not in text:
        text = "from flask import request\n" + text

    # Insertar helper después de imports principales
    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, "\n" + build_blueprint_helper_block())

    new_text = "\n".join(lines).rstrip() + "\n"

    if new_text != original:
        backup(ASTER_BLUEPRINT)
        write(ASTER_BLUEPRINT, new_text)
        print("OK: helper insertado en aster_blueprint.py.")
    else:
        print("OK: aster_blueprint.py sin cambios.")


def patch_fecha_sql_references_in_blueprint():
    title("3. CORRIGIENDO ACCESOS DIRECTOS A fecha_sql / conexion EN aster_blueprint.py")

    original = read(ASTER_BLUEPRINT)
    text = original

    replacements = [
        # request directo
        (r'request\.form\[\s*[\'"]fecha_sql[\'"]\s*\]', r'_aster_phase_e_fecha_sql()'),
        (r'request\.args\[\s*[\'"]fecha_sql[\'"]\s*\]', r'_aster_phase_e_fecha_sql()'),
        (r'request\.values\[\s*[\'"]fecha_sql[\'"]\s*\]', r'_aster_phase_e_fecha_sql()'),
        (r'request\.json\[\s*[\'"]fecha_sql[\'"]\s*\]', r'_aster_phase_e_fecha_sql()'),

        (r'request\.form\[\s*[\'"]conexion[\'"]\s*\]', r'_aster_phase_e_conexion()'),
        (r'request\.args\[\s*[\'"]conexion[\'"]\s*\]', r'_aster_phase_e_conexion()'),
        (r'request\.values\[\s*[\'"]conexion[\'"]\s*\]', r'_aster_phase_e_conexion()'),
        (r'request\.json\[\s*[\'"]conexion[\'"]\s*\]', r'_aster_phase_e_conexion()'),

        # variables comunes tipo payload["fecha_sql"]
        (r'\b(payload|data|datos|params|body|form_data|request_data|filtros)\[\s*[\'"]fecha_sql[\'"]\s*\]',
         r'(\1.get("fecha_sql") or _aster_phase_e_fecha_sql())'),

        (r'\b(payload|data|datos|params|body|form_data|request_data|filtros)\[\s*[\'"]conexion[\'"]\s*\]',
         r'(\1.get("conexion") or _aster_phase_e_conexion())'),
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    # Si hay payloads creados desde JSON/form, normalizarlos después de la línea.
    payload_patterns = [
        r'(\bpayload\s*=\s*request\.get_json\(silent=True\)\s*or\s*\{\}\s*)',
        r'(\bdata\s*=\s*request\.get_json\(silent=True\)\s*or\s*\{\}\s*)',
        r'(\bdatos\s*=\s*request\.get_json\(silent=True\)\s*or\s*\{\}\s*)',
    ]

    for pattern in payload_patterns:
        text = re.sub(
            pattern,
            r'\1\n    payload = _aster_phase_e_normalizar_payload(payload) if "payload" in locals() else payload',
            text,
            count=1,
        )

    if text != original:
        backup(ASTER_BLUEPRINT)
        write(ASTER_BLUEPRINT, text)
        print("OK: referencias en aster_blueprint.py corregidas.")
    else:
        print("No se encontraron accesos directos a corregir en blueprint.")


def patch_safe_renderer_result_access():
    title("4. CORRIGIENDO ACCESOS RESULTADO['fecha_sql'] EN SERVICIOS ASTER")

    target_files = [
        ASTER_RENDERER_SERVICE,
        ASTER_SOURCE_SERVICE,
        ROOT / "app" / "services" / "aster_sql_entity_service.py",
        ROOT / "app" / "services" / "aster_phase_i_prepare_service.py",
        ROOT / "app" / "services" / "aster_phase_i_execution_service.py",
    ]

    changed = []

    for path in target_files:
        if not path.exists():
            continue

        original = read(path)
        text = original

        # Solo para variables de resultado/contexto; evita tocar request o payload en servicios.
        text = re.sub(
            r'\b(resultado|result|res|contexto|context|detalle|consulta|diagnostico|diagnóstico)\[\s*[\'"]fecha_sql[\'"]\s*\]',
            r'\1.get("fecha_sql", "")',
            text,
        )

        text = re.sub(
            r'\b(resultado|result|res|contexto|context|detalle|consulta|diagnostico|diagnóstico)\[\s*[\'"]conexion[\'"]\s*\]',
            r'\1.get("conexion", "local")',
            text,
        )

        if text != original:
            backup(path)
            write(path, text)
            changed.append(path.relative_to(ROOT))

    if changed:
        print("Archivos corregidos:")
        for item in changed:
            print("-", item)
    else:
        print("No se encontraron accesos resultado['fecha_sql'] en servicios.")


def audit_fecha_sql():
    title("5. AUDITORIA fecha_sql / conexion")

    target_dirs = [
        ROOT / "app" / "controllers",
        ROOT / "app" / "services",
    ]

    for base in target_dirs:
        if not base.exists():
            continue

        for path in base.rglob("*.py"):
            text = read(path)
            if "fecha_sql" not in text and "conexion_aster" not in text:
                continue

            print(f"\n--- {path.relative_to(ROOT)} ---")
            for i, line in enumerate(text.splitlines(), start=1):
                if "fecha_sql" in line or "conexion_aster" in line:
                    print(f"{i:04d}: {line[:220]}")


def compile_modified():
    title("6. COMPILACION")

    files = [
        ASTER_BLUEPRINT,
        ASTER_SOURCE_SERVICE,
        ASTER_RENDERER_SERVICE,
        ROOT / "app" / "services" / "aster_sql_entity_service.py",
        ROOT / "app" / "services" / "aster_phase_i_prepare_service.py",
        ROOT / "app" / "services" / "aster_phase_i_execution_service.py",
    ]

    py_files = [str(p) for p in files if p.exists()]

    subprocess.run([sys.executable, "-m", "py_compile", *py_files], check=True)
    print("OK: archivos Python ASTER compilan correctamente.")


def main():
    title("FIX ASTER FASE E - fecha_sql + conexion local/remoto")

    update_env()
    insert_helper_in_blueprint()
    patch_fecha_sql_references_in_blueprint()
    patch_safe_renderer_result_access()
    audit_fecha_sql()
    compile_modified()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase E -> Ejecutar consulta SQL ASTER")
    print("")
    print("Para pruebas debe usar LOCAL:")
    print("  local -> localhost\\SQL2025DEV / gestioncomercial_dev")
    print("")
    print("No uses REMOTO salvo que quieras consultar 10.24.90.101.")


if __name__ == "__main__":
    main()