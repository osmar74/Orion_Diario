from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re
import pyodbc

ROOT = Path.cwd()

TARGET_FILES = [
    ROOT / "app" / "services" / "aster_phase_i_execution_service.py",
    ROOT / "app" / "services" / "aster_phase_i_prepare_service.py",
    ROOT / "app" / "services" / "aster_source_service.py",
]

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

MARKER_BEGIN = "# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_BEGIN ==="
MARKER_END = "# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_END ==="

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
    if not path.exists():
        return

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


def audit_sql_local():
    title("1. AUDITORIA SQL SERVER LOCAL - dbo.usuarios")

    with pyodbc.connect(LOCAL_CONN_STR, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())
        print("SUSER_SNAME():", cur.execute("SELECT SUSER_SNAME()").fetchval())

        rows = cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='usuarios'
            ORDER BY ORDINAL_POSITION;
            """
        ).fetchall()

        cols = [r.COLUMN_NAME for r in rows]

        print("\nColumnas reales dbo.usuarios:")
        for r in rows:
            print(f"- {r.COLUMN_NAME} | {r.DATA_TYPE}")

        if "id" in [c.lower() for c in cols]:
            print("\nAVISO: existe columna id en dbo.usuarios.")
        else:
            print("\nOK: dbo.usuarios NO tiene id. Para local se usará usuario como identificador lógico.")


def build_helper_block():
    block = '''
# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_BEGIN ===
# Fix local ASTER Fase I:
#
# En gestioncomercial_dev.dbo.usuarios no existe la columna id.
# La columna lógica para usuarios local es usuario.
#
# Este helper evita que la validación bloquee Fase I por faltar id
# cuando la conexión es local.
#
# Fecha generación: __TIMESTAMP__


def _aster_phase_i_es_local_required_id_fix(scope=None):
    scope = scope or {}

    conexion = (
        scope.get("conexion")
        or scope.get("modo")
        or scope.get("origen")
        or scope.get("tipo_conexion")
        or "local"
    )

    conexion = str(conexion or "local").strip().lower()

    return conexion in [
        "local",
        "sqlserver",
        "sql_server",
        "dev",
        "desarrollo",
    ]


def _aster_phase_i_filtrar_faltantes_usuarios_local(faltantes, scope=None):
    """
    En local, dbo.usuarios no tiene id.
    Por tanto, si la única columna faltante es id, no debe bloquear la Fase I.
    """
    if not faltantes:
        return faltantes

    faltantes_lista = list(faltantes)

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return faltantes_lista

    ignorables_local = {
        "id",
    }

    filtrados = [
        col for col in faltantes_lista
        if str(col).strip().lower() not in ignorables_local
    ]

    return filtrados


def _aster_phase_i_columnas_requeridas_usuarios_local(columnas=None, scope=None):
    """
    Normaliza columnas requeridas para usuarios local.
    Si aparece id, se elimina.
    Si no aparece usuario, se agrega como mínimo requerido.
    """
    columnas = list(columnas or [])

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return columnas

    columnas = [
        col for col in columnas
        if str(col).strip().lower() != "id"
    ]

    if "usuario" not in [str(c).strip().lower() for c in columnas]:
        columnas.insert(0, "usuario")

    return columnas


# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def patch_required_lists(text: str):
    """
    Busca listas de columnas requeridas de usuarios y elimina 'id'.
    Ejemplo:
      columnas_requeridas_usuarios = ["id", "usuario"]
    pasa a:
      columnas_requeridas_usuarios = ["usuario"]
    """

    def repl(match):
        prefix = match.group("prefix")
        body = match.group("body")

        # Solo tocar si realmente parece lista de usuarios y contiene id.
        if not re.search(r'["\']id["\']', body):
            return match.group(0)

        if not re.search(r'["\']usuario["\']', body):
            return match.group(0)

        items = re.findall(r'["\']([^"\']+)["\']', body)

        cleaned = []
        for item in items:
            if item.strip().lower() == "id":
                continue

            if item not in cleaned:
                cleaned.append(item)

        if "usuario" not in [x.lower() for x in cleaned]:
            cleaned.insert(0, "usuario")

        replacement_body = ", ".join(f'"{x}"' for x in cleaned)

        return f"{prefix}[{replacement_body}]"

    patterns = [
        r'(?P<prefix>\b\w*requerid\w*usuarios\w*\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\bcolumnas_usuarios_requeridas\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\brequired_usuarios\w*\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\brequired_user\w*\s*=\s*)\[(?P<body>[^\]]+)\]',
    ]

    for pattern in patterns:
        text = re.sub(pattern, repl, text, flags=re.I | re.S)

    return text


def patch_missing_column_raise(text: str):
    """
    Inserta filtro antes de:
      if faltantes:
          raise ... "Faltan columnas requeridas para usuarios..."
    """

    lines = text.splitlines()
    inserts = []

    for i, line in enumerate(lines):
        if "Faltan columnas requeridas para usuarios" not in line:
            continue

        # Buscar hacia arriba el if faltantes:
        for j in range(max(0, i - 6), i):
            m = re.match(r'^(\s*)if\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$', lines[j])
            if not m:
                continue

            indent = m.group(1)
            var_name = m.group(2)

            previous = "\n".join(lines[max(0, j - 3):j + 1])

            if "_aster_phase_i_filtrar_faltantes_usuarios_local" in previous:
                break

            inserts.append(
                (
                    j,
                    f'{indent}{var_name} = _aster_phase_i_filtrar_faltantes_usuarios_local({var_name}, locals())'
                )
            )
            break

    if not inserts:
        return text

    # Insertar de abajo hacia arriba para no desplazar índices.
    for index, new_line in reversed(inserts):
        lines.insert(index, new_line)

    return "\n".join(lines) + "\n"


def patch_file(path: Path):
    if not path.exists():
        return False

    original = read(path)
    text = original

    text = remove_old_block(text)

    # Agregar helper al final solo en archivos donde puede existir la validación.
    text = text.rstrip() + "\n\n" + build_helper_block()

    text = patch_required_lists(text)
    text = patch_missing_column_raise(text)

    if text != original:
        backup(path)
        write(path, text)
        return True

    return False


def audit_code():
    title("2. AUDITORIA CODIGO - Faltan columnas requeridas para usuarios")

    for path in TARGET_FILES:
        if not path.exists():
            continue

        text = read(path)

        print(f"\n--- {path.relative_to(ROOT)} ---")

        found = False
        for i, line in enumerate(text.splitlines(), start=1):
            if (
                "Faltan columnas requeridas para usuarios" in line
                or "requerid" in line.lower() and "usuarios" in line.lower()
                or '"id"' in line and "usuario" in line.lower()
            ):
                found = True
                print(f"{i:04d}: {line[:220]}")

        if not found:
            print("Sin coincidencias relevantes.")


def apply_patch():
    title("3. APLICANDO FIX")

    changed = []

    for path in TARGET_FILES:
        if patch_file(path):
            changed.append(path)

    if not changed:
        print("No se modificó ningún archivo.")
    else:
        print("Archivos modificados:")
        for path in changed:
            print("-", path.relative_to(ROOT))

    return changed


def compile_files():
    title("4. COMPILACION")

    files = [str(path) for path in TARGET_FILES if path.exists()]

    subprocess.run(
        [sys.executable, "-m", "py_compile", *files],
        check=True,
    )

    print("OK: servicios ASTER Fase I compilan.")


def validate_import():
    title("5. VALIDACION IMPORT FASE I")

    code = (
        "from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster; "
        "print('OK ejecutar_fase_i_aster importado')"
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def audit_final():
    title("6. AUDITORIA FINAL")

    for path in TARGET_FILES:
        if not path.exists():
            continue

        text = read(path)

        print(f"\n--- {path.relative_to(ROOT)} ---")

        for i, line in enumerate(text.splitlines(), start=1):
            if (
                "Faltan columnas requeridas para usuarios" in line
                or "_aster_phase_i_filtrar_faltantes_usuarios_local" in line
                or "columnas_requeridas" in line.lower()
            ):
                print(f"{i:04d}: {line[:220]}")


def main():
    title("FIX ASTER FASE I - id NO REQUERIDO EN USUARIOS LOCAL")

    audit_sql_local()
    audit_code()
    apply_patch()
    compile_files()
    validate_import()
    audit_final()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase I -> Ejecutar Fase I completa")
    print("")
    print("Si aparece otro error, ya será la siguiente validación del pipeline.")


if __name__ == "__main__":
    main()