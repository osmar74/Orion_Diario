from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re
import pyodbc

ROOT = Path.cwd()

PREPARE_SERVICE = ROOT / "app" / "services" / "aster_phase_i_prepare_service.py"
EXECUTION_SERVICE = ROOT / "app" / "services" / "aster_phase_i_execution_service.py"
SOURCE_SERVICE = ROOT / "app" / "services" / "aster_source_service.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

MARKER_BEGIN = "# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_BEGIN ==="
MARKER_END = "# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_END ==="

LOCAL_CONN_STR = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=gestioncomercial_dev;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

COLUMNAS_USUARIOS_LOCAL = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]

COLUMNAS_COMENTARIOS_LOCAL = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]

COLUMNAS_LEGACY_INVALIDAS = [
    "pass",
    "perfil",
    "nombre",
    "owned_by",
    "type",
    "web",
    "created_at",
    "updated_at",
]


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


def remove_old_block(text):
    while MARKER_BEGIN in text:
        before = text.split(MARKER_BEGIN, 1)[0].rstrip()
        rest = text.split(MARKER_BEGIN, 1)[1]

        if MARKER_END in rest:
            after = rest.split(MARKER_END, 1)[1].lstrip()
            text = before + "\n\n" + after
        else:
            text = before + "\n"

    return text


def audit_sqlserver_local_schema():
    title("1. AUDITORIA SQL SERVER LOCAL - gestioncomercial_dev")

    with pyodbc.connect(LOCAL_CONN_STR, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())
        print("SUSER_SNAME():", cur.execute("SELECT SUSER_SNAME()").fetchval())

        for tabla in ["usuarios", "comentarios"]:
            print(f"\nColumnas dbo.{tabla}:")

            rows = cur.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='dbo'
                  AND TABLE_NAME=?
                ORDER BY ORDINAL_POSITION;
                """,
                tabla,
            ).fetchall()

            if not rows:
                print(f"ERROR: No existe dbo.{tabla}")
                continue

            for r in rows:
                print(f"- {r.COLUMN_NAME} | {r.DATA_TYPE}")

        print("\nValidando que dbo.usuarios NO tiene columnas legacy:")
        rows = cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='usuarios'
            ORDER BY ORDINAL_POSITION;
            """
        ).fetchall()

        existing = {r.COLUMN_NAME.lower() for r in rows}

        for col in COLUMNAS_LEGACY_INVALIDAS:
            print(f"- {col}: {'EXISTE' if col.lower() in existing else 'NO EXISTE'}")


def audit_code_bad_columns():
    title("2. AUDITORIA CODIGO - COLUMNAS LEGACY EN SERVICIOS ASTER")

    for path in [PREPARE_SERVICE, EXECUTION_SERVICE, SOURCE_SERVICE]:
        if not path.exists():
            continue

        text = read(path)
        hits = []

        for i, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            if any(col in lower for col in COLUMNAS_LEGACY_INVALIDAS):
                hits.append((i, line))

        print(f"\n--- {path.relative_to(ROOT)} ---")

        if not hits:
            print("Sin columnas legacy detectadas.")
        else:
            for i, line in hits:
                print(f"{i:04d}: {line[:220]}")


def build_prepare_override_block():
    block = '''
# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_BEGIN ===
# Override final de columnas ASTER Fase I para origen LOCAL SQL Server.
#
# Motivo:
#   En local, gestioncomercial_dev.dbo.usuarios NO tiene columnas legacy:
#   id, pass, perfil, nombre, owned_by, type, web, created_at, updated_at.
#
#   La tabla local real tiene:
#   usuario, interno, grupos, permisosr2, seleccion, filtrar,
#   pausaragente, agente, modificarinterno, modificaragente, callback.
#
# Fecha generación: __TIMESTAMP__


ASTER_FASE_I_COLUMNAS_USUARIOS_LOCAL = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]


ASTER_FASE_I_COLUMNAS_COMENTARIOS_LOCAL = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


def columnas_sqlserver_usuarios_fase_i():
    """
    Columnas reales de gestioncomercial_dev.dbo.usuarios.
    """
    return list(ASTER_FASE_I_COLUMNAS_USUARIOS_LOCAL)


def columnas_sqlserver_crm_fase_i():
    """
    Alias local legacy.
    En local, crm equivale a usuarios.
    """
    return columnas_sqlserver_usuarios_fase_i()


def columnas_sqlserver_comentarios_fase_i():
    """
    Columnas reales de gestioncomercial_dev.dbo.comentarios.
    """
    return list(ASTER_FASE_I_COLUMNAS_COMENTARIOS_LOCAL)


# Overrides seguros para llamadas legacy que todavía usan nombres mysql_*.
# En local deben devolver columnas SQL Server reales.
def columnas_mysql_usuarios_fase_i():
    return columnas_sqlserver_usuarios_fase_i()


def columnas_mysql_crm_fase_i():
    return columnas_sqlserver_usuarios_fase_i()


def columnas_mysql_comentarios_fase_i():
    return columnas_sqlserver_comentarios_fase_i()


def columnas_usuarios_fase_i_por_conexion(conexion="local"):
    """
    Selector explícito por conexión.
    Para pruebas locales, siempre usa columnas reales SQL Server.
    """
    modo = str(conexion or "local").strip().lower()

    if modo in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
        return columnas_sqlserver_usuarios_fase_i()

    # Fallback remoto: se mantiene compatible con el set local para no romper
    # si el pipeline espera el mismo shape.
    return columnas_sqlserver_usuarios_fase_i()


def columnas_comentarios_fase_i_por_conexion(conexion="local"):
    modo = str(conexion or "local").strip().lower()

    if modo in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
        return columnas_sqlserver_comentarios_fase_i()

    return columnas_sqlserver_comentarios_fase_i()


# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def patch_prepare_service():
    title("3. PATCH aster_phase_i_prepare_service.py")

    if not PREPARE_SERVICE.exists():
        raise FileNotFoundError(f"No existe: {PREPARE_SERVICE}")

    original = read(PREPARE_SERVICE)
    text = remove_old_block(original).rstrip() + "\n\n" + build_prepare_override_block()

    if text != original:
        backup(PREPARE_SERVICE)
        write(PREPARE_SERVICE, text)
        print("OK: overrides de columnas agregados al final de prepare_service.")
    else:
        print("OK: prepare_service ya estaba actualizado.")


def build_execution_guard_block():
    block = '''
# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_BEGIN ===
# Guardas locales para ASTER Fase I.
#
# Si alguna función todavía arma SELECT con columnas legacy de usuarios,
# este bloque fuerza el set correcto para origen local.
#
# Fecha generación: __TIMESTAMP__


ASTER_FASE_I_USUARIOS_LOCAL_SAFE_COLUMNS = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]


ASTER_FASE_I_COMENTARIOS_LOCAL_SAFE_COLUMNS = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


ASTER_FASE_I_LEGACY_INVALID_USER_COLUMNS = {
    "pass",
    "perfil",
    "nombre",
    "owned_by",
    "type",
    "web",
    "created_at",
    "updated_at",
}


def _aster_phase_i_es_conexion_local(conexion=None):
    modo = str(conexion or "local").strip().lower()
    return modo in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]


def _aster_phase_i_normalizar_columnas_usuarios_local(columnas, conexion=None):
    """
    Evita SELECT id, pass, perfil, nombre... sobre dbo.usuarios local.
    """
    if not _aster_phase_i_es_conexion_local(conexion):
        return list(columnas or ASTER_FASE_I_USUARIOS_LOCAL_SAFE_COLUMNS)

    columnas = list(columnas or [])

    lower = {str(c).lower() for c in columnas}

    if not columnas or (lower & ASTER_FASE_I_LEGACY_INVALID_USER_COLUMNS):
        return list(ASTER_FASE_I_USUARIOS_LOCAL_SAFE_COLUMNS)

    return columnas


def _aster_phase_i_normalizar_columnas_comentarios_local(columnas, conexion=None):
    if not _aster_phase_i_es_conexion_local(conexion):
        return list(columnas or ASTER_FASE_I_COMENTARIOS_LOCAL_SAFE_COLUMNS)

    return list(columnas or ASTER_FASE_I_COMENTARIOS_LOCAL_SAFE_COLUMNS)


# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def patch_execution_service():
    title("4. PATCH DEFENSIVO aster_phase_i_execution_service.py")

    if not EXECUTION_SERVICE.exists():
        print("AVISO: No existe execution_service.")
        return

    original = read(EXECUTION_SERVICE)
    text = remove_old_block(original)

    # Agregar guardas al final.
    text = text.rstrip() + "\n\n" + build_execution_guard_block()

    # Parchear patrones típicos donde se asignan columnas usuarios/crm.
    # No reemplaza todos los usos; solo envuelve asignaciones evidentes.
    patterns = [
        (
            r'(?m)^(\s*)(columnas_usuarios\s*=\s*columnas_mysql_usuarios_fase_i\(\)\s*)$',
            r'\1\2\n\1columnas_usuarios = _aster_phase_i_normalizar_columnas_usuarios_local(columnas_usuarios, conexion)',
        ),
        (
            r'(?m)^(\s*)(columnas_usuarios\s*=\s*columnas_mysql_crm_fase_i\(\)\s*)$',
            r'\1\2\n\1columnas_usuarios = _aster_phase_i_normalizar_columnas_usuarios_local(columnas_usuarios, conexion)',
        ),
        (
            r'(?m)^(\s*)(columnas_crm\s*=\s*columnas_mysql_crm_fase_i\(\)\s*)$',
            r'\1\2\n\1columnas_crm = _aster_phase_i_normalizar_columnas_usuarios_local(columnas_crm, conexion)',
        ),
        (
            r'(?m)^(\s*)(columnas_comentarios\s*=\s*columnas_mysql_comentarios_fase_i\(\)\s*)$',
            r'\1\2\n\1columnas_comentarios = _aster_phase_i_normalizar_columnas_comentarios_local(columnas_comentarios, conexion)',
        ),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    if text != original:
        backup(EXECUTION_SERVICE)
        write(EXECUTION_SERVICE, text)
        print("OK: execution_service actualizado con guardas.")
    else:
        print("OK: execution_service no requería cambios.")


def patch_source_service_selects():
    title("5. PATCH DEFENSIVO aster_source_service.py")

    if not SOURCE_SERVICE.exists():
        print("AVISO: No existe aster_source_service.py")
        return

    original = read(SOURCE_SERVICE)
    text = original

    # Si en source service hay listas explícitas con columnas legacy de usuarios, las reemplazamos.
    legacy_list_regex = r'\[\s*["\']id["\']\s*,\s*["\']usuario["\']\s*,\s*["\']pass["\']\s*,\s*["\']perfil["\']\s*,\s*["\']nombre["\'][^\]]*\]'

    safe_list = """[
        "usuario",
        "interno",
        "grupos",
        "permisosr2",
        "seleccion",
        "filtrar",
        "pausaragente",
        "agente",
        "modificarinterno",
        "modificaragente",
        "callback",
    ]"""

    text = re.sub(legacy_list_regex, safe_list, text, flags=re.S)

    if text != original:
        backup(SOURCE_SERVICE)
        write(SOURCE_SERVICE, text)
        print("OK: source_service reemplazó lista legacy de usuarios.")
    else:
        print("No se detectó lista legacy explícita en source_service.")


def validate_imports_and_functions():
    title("6. VALIDACION DE FUNCIONES DE COLUMNAS")

    # py_compile primero
    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(PREPARE_SERVICE),
            str(EXECUTION_SERVICE),
            str(SOURCE_SERVICE),
        ],
        check=True,
    )

    print("OK: servicios compilan.")

    # Import directo
    code = (
        "from app.services.aster_phase_i_prepare_service import "
        "columnas_mysql_usuarios_fase_i, columnas_mysql_comentarios_fase_i; "
        "print('usuarios:', columnas_mysql_usuarios_fase_i()); "
        "print('comentarios:', columnas_mysql_comentarios_fase_i())"
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def validate_no_invalid_select_local():
    title("7. VALIDACION SQL LOCAL CON COLUMNAS CORRECTAS")

    usuarios_cols = ", ".join(f"[{c}]" for c in COLUMNAS_USUARIOS_LOCAL)
    comentarios_cols = ", ".join(f"[{c}]" for c in COLUMNAS_COMENTARIOS_LOCAL)

    with pyodbc.connect(LOCAL_CONN_STR, timeout=10) as conn:
        cur = conn.cursor()

        print("Probando SELECT TOP 1 dbo.usuarios...")
        cur.execute(f"SELECT TOP 1 {usuarios_cols} FROM dbo.usuarios")
        print("OK: dbo.usuarios acepta columnas locales.")

        print("Probando SELECT TOP 1 dbo.comentarios...")
        cur.execute(f"SELECT TOP 1 {comentarios_cols} FROM dbo.comentarios")
        print("OK: dbo.comentarios acepta columnas locales.")


def audit_final():
    title("8. AUDITORIA FINAL")

    for path in [PREPARE_SERVICE, EXECUTION_SERVICE, SOURCE_SERVICE]:
        if not path.exists():
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")
        text = read(path)

        for i, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            if any(col in lower for col in COLUMNAS_LEGACY_INVALIDAS):
                print(f"{i:04d}: {line[:220]}")


def main():
    title("FIX ASTER FASE I - COLUMNAS LOCALES SQL SERVER")

    audit_sqlserver_local_schema()
    audit_code_bad_columns()
    patch_prepare_service()
    patch_execution_service()
    patch_source_service_selects()
    validate_imports_and_functions()
    validate_no_invalid_select_local()
    audit_final()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase I -> Ejecutar Fase I completa")
    print("")
    print("La Fase I local debe usar:")
    print("  gestioncomercial_dev.dbo.usuarios")
    print("  gestioncomercial_dev.dbo.comentarios")


if __name__ == "__main__":
    main()