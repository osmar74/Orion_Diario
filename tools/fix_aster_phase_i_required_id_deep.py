from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re
import pyodbc

ROOT = Path.cwd()
APP_DIR = ROOT / "app"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

ERROR_TEXT = "Faltan columnas requeridas para usuarios"

MARKER_BEGIN = "# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_BEGIN ==="
MARKER_END = "# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_END ==="

LOCAL_CONN_STR = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=gestioncomercial_dev;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def remove_old_block(text: str):
    while MARKER_BEGIN in text:
        before = text.split(MARKER_BEGIN, 1)[0].rstrip()
        rest = text.split(MARKER_BEGIN, 1)[1]

        if MARKER_END in rest:
            after = rest.split(MARKER_END, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def build_helper_block():
    block = '''
# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_BEGIN ===
# Fix profundo ASTER Fase I.
#
# En LOCAL, gestioncomercial_dev.dbo.usuarios no tiene columna id.
# La columna lógica de usuarios es usuario.
# Por eso id NO debe bloquear la validación de usuarios locales.
#
# Fecha generación: __TIMESTAMP__


def _aster_phase_i_required_id_deep_is_local(scope=None):
    scope = scope or {}

    conexion = (
        scope.get("conexion")
        or scope.get("modo")
        or scope.get("origen")
        or scope.get("tipo_conexion")
        or scope.get("conexion_aster")
        or "local"
    )

    conexion = str(conexion or "local").strip().lower()

    return conexion in {
        "local",
        "sqlserver",
        "sql_server",
        "dev",
        "desarrollo",
    }


def _aster_phase_i_required_id_deep_filter(faltantes, scope=None):
    """
    Quita id de faltantes cuando se valida usuarios en LOCAL.
    """
    if not faltantes:
        return faltantes

    try:
        faltantes_lista = list(faltantes)
    except Exception:
        return faltantes

    if not _aster_phase_i_required_id_deep_is_local(scope):
        return faltantes_lista

    return [
        col for col in faltantes_lista
        if str(col).strip().lower() != "id"
    ]


def _aster_phase_i_required_id_deep_normalize_required(columnas, scope=None):
    """
    Normaliza columnas requeridas para usuarios local.
    """
    try:
        columnas_lista = list(columnas or [])
    except Exception:
        return columnas

    if not _aster_phase_i_required_id_deep_is_local(scope):
        return columnas_lista

    columnas_lista = [
        col for col in columnas_lista
        if str(col).strip().lower() != "id"
    ]

    lower = [str(c).strip().lower() for c in columnas_lista]

    if "usuario" not in lower:
        columnas_lista.insert(0, "usuario")

    return columnas_lista


# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def audit_sql_local():
    title("1. AUDITORIA SQL LOCAL dbo.usuarios")

    with pyodbc.connect(LOCAL_CONN_STR, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())
        print("SUSER_SNAME():", cur.execute("SELECT SUSER_SNAME()").fetchval())

        rows = cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='usuarios'
            ORDER BY ORDINAL_POSITION;
            """
        ).fetchall()

        cols = [r.COLUMN_NAME.lower() for r in rows]

        print("\nColumnas dbo.usuarios:")
        for r in rows:
            print(f"- {r.COLUMN_NAME} | {r.DATA_TYPE}")

        print("\nValidación:")
        print("- id:", "EXISTE" if "id" in cols else "NO EXISTE")
        print("- usuario:", "EXISTE" if "usuario" in cols else "NO EXISTE")


def find_error_files():
    title("2. BUSCANDO GENERADOR DEL ERROR")

    files = []

    for path in APP_DIR.rglob("*.py"):
        text = read(path)

        if ERROR_TEXT in text or ("faltan columnas" in text.lower() and "usuarios" in text.lower()):
            files.append(path)

    if not files:
        print("No se encontró el texto exacto del error en app/.")
        print("Se hará auditoría amplia por columnas requeridas.")
    else:
        for path in files:
            print(f"\n--- {path.relative_to(ROOT)} ---")
            for i, line in enumerate(read(path).splitlines(), start=1):
                if ERROR_TEXT in line or ("faltan columnas" in line.lower() and "usuarios" in line.lower()):
                    print(f"{i:04d}: {line[:240]}")

    return files


def find_related_files():
    related = set(find_error_files())

    keywords = [
        "columnas requeridas",
        "columnas_requeridas",
        "faltantes",
        "usuarios",
        "fecha_sql",
        "ejecutar_fase_i_aster",
    ]

    for path in APP_DIR.rglob("*.py"):
        text = read(path).lower()

        if "aster" not in str(path).lower():
            continue

        if all(k in text for k in ["usuarios", "faltantes"]):
            related.add(path)

        if ERROR_TEXT.lower() in text:
            related.add(path)

    return sorted(related)


def add_helper_if_needed(text: str):
    text = remove_old_block(text)

    if "_aster_phase_i_required_id_deep_filter" in text:
        return text

    # Insertar después de imports si es posible.
    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, "\n" + build_helper_block())

    return "\n".join(lines).rstrip() + "\n"


def infer_missing_var(lines, error_index):
    """
    Intenta inferir variable faltantes desde:
    - if faltantes:
    - if faltantes_usuarios:
    - join(faltantes_usuarios)
    - {faltantes_usuarios}
    """

    # Primero buscar if hacia arriba.
    for j in range(error_index, max(-1, error_index - 15), -1):
        line = lines[j]

        m = re.match(r'^(\s*)if\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$', line)
        if m:
            var = m.group(2)
            if "falt" in var.lower() or "missing" in var.lower():
                return var, j, m.group(1)

    # Buscar join(variable) cerca del error.
    window = "\n".join(lines[max(0, error_index - 5): error_index + 3])

    m = re.search(r"\.join\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", window)
    if m:
        var = m.group(1)

        for j in range(error_index, max(-1, error_index - 15), -1):
            if re.match(rf'^(\s*)if\s+{re.escape(var)}\s*:\s*$', lines[j]):
                indent = re.match(r'^(\s*)', lines[j]).group(1)
                return var, j, indent

        return var, error_index, re.match(r'^(\s*)', lines[error_index]).group(1)

    # Buscar {faltantes}
    m = re.search(r"\{\s*([A-Za-z_][A-Za-z0-9_]*falt[A-Za-z0-9_]*)\s*\}", window)
    if m:
        var = m.group(1)

        for j in range(error_index, max(-1, error_index - 15), -1):
            if re.match(rf'^(\s*)if\s+{re.escape(var)}\s*:\s*$', lines[j]):
                indent = re.match(r'^(\s*)', lines[j]).group(1)
                return var, j, indent

        return var, error_index, re.match(r'^(\s*)', lines[error_index]).group(1)

    return None, None, None


def patch_error_conditions(text: str):
    lines = text.splitlines()
    inserts = []

    for i, line in enumerate(lines):
        if ERROR_TEXT not in line and not ("faltan columnas" in line.lower() and "usuarios" in line.lower()):
            continue

        var, if_index, indent = infer_missing_var(lines, i)

        if not var:
            print(f"AVISO: No pude inferir variable faltantes cerca de línea {i+1}")
            continue

        filter_line = f"{indent}{var} = _aster_phase_i_required_id_deep_filter({var}, locals())"

        # Evitar duplicar.
        previous_window = "\n".join(lines[max(0, if_index - 3):if_index + 1])
        if "_aster_phase_i_required_id_deep_filter" in previous_window:
            continue

        inserts.append((if_index, filter_line))

    for index, line in reversed(inserts):
        lines.insert(index, line)

    return "\n".join(lines).rstrip() + "\n"


def patch_required_lists(text: str):
    """
    Si hay columnas requeridas de usuarios = ["id", "usuario", ...],
    quita id y deja usuario.
    """

    def repl(match):
        prefix = match.group("prefix")
        body = match.group("body")

        if "id" not in body.lower():
            return match.group(0)

        if "usuario" not in body.lower() and "usuarios" not in prefix.lower():
            return match.group(0)

        items = re.findall(r'["\']([^"\']+)["\']', body)

        if not items:
            return match.group(0)

        cleaned = []

        for item in items:
            if item.strip().lower() == "id":
                continue

            if item not in cleaned:
                cleaned.append(item)

        if "usuario" not in [x.lower() for x in cleaned]:
            cleaned.insert(0, "usuario")

        return f'{prefix}[{", ".join(repr(x) for x in cleaned)}]'

    patterns = [
        r'(?P<prefix>\b[A-Za-z_]*requerid[A-Za-z_]*usuarios[A-Za-z_]*\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\bcolumnas_usuarios_requeridas\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\bcolumnas_requeridas_usuarios\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\brequired_users_columns\s*=\s*)\[(?P<body>[^\]]+)\]',
    ]

    for pattern in patterns:
        text = re.sub(pattern, repl, text, flags=re.I | re.S)

    return text


def patch_file(path: Path):
    original = read(path)
    text = original

    text = add_helper_if_needed(text)
    text = patch_required_lists(text)
    text = patch_error_conditions(text)

    if text != original:
        backup(path)
        write(path, text)
        return True

    return False


def apply_patch():
    title("3. APLICANDO PATCH PROFUNDO")

    files = find_related_files()

    if not files:
        print("No hay archivos candidatos. No se modificó nada.")
        return []

    changed = []

    for path in files:
        if patch_file(path):
            changed.append(path)

    if changed:
        print("\nArchivos modificados:")
        for path in changed:
            print("-", path.relative_to(ROOT))
    else:
        print("No se modificó ningún archivo. Necesitamos ver la auditoría completa.")

    return changed


def audit_after():
    title("4. AUDITORIA DESPUES DEL PATCH")

    for path in APP_DIR.rglob("*.py"):
        text = read(path)

        if ERROR_TEXT not in text and "_aster_phase_i_required_id_deep_filter" not in text:
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")

        for i, line in enumerate(text.splitlines(), start=1):
            if (
                ERROR_TEXT in line
                or "_aster_phase_i_required_id_deep_filter" in line
                or "columnas_requeridas_usuarios" in line
                or "requeridas_usuarios" in line
            ):
                print(f"{i:04d}: {line[:240]}")


def compile_all():
    title("5. COMPILACION")

    files = [str(path) for path in APP_DIR.rglob("*.py")]

    subprocess.run([sys.executable, "-m", "py_compile", *files], check=True)

    print("OK: todo app/ compila.")


def validate_import():
    title("6. VALIDACION IMPORT FASE I")

    code = (
        "from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster; "
        "print('OK ejecutar_fase_i_aster importado correctamente')"
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def main():
    title("FIX PROFUNDO ASTER FASE I - NO REQUERIR id EN USUARIOS LOCAL")

    audit_sql_local()
    apply_patch()
    audit_after()
    compile_all()
    validate_import()

    title("FINALIZADO")
    print("Reinicia Flask completamente:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase I -> Ejecutar Fase I completa")


if __name__ == "__main__":
    main()