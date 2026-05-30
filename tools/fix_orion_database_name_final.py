from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re
import pyodbc

ROOT = Path.cwd()

ENV_FILE = ROOT / ".env"
CONFIG_FILE = ROOT / "app" / "config.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

ORION_DB = "Orion"

MARKER_BEGIN = "# === FIX_ORION_DATABASE_NAME_FINAL_BEGIN ==="
MARKER_END = "# === FIX_ORION_DATABASE_NAME_FINAL_END ==="


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
    if "PASSWORD" in key.upper():
        return "***"
    return value


def update_env():
    title("1. ACTUALIZANDO .env")

    original = read(ENV_FILE) if ENV_FILE.exists() else ""

    required = {
        # ASTER local / reemplazo de MySQL remoto
        "SQLSERVER_DRIVER": "ODBC Driver 18 for SQL Server",
        "SQLSERVER_SERVER": r"localhost\SQL2025DEV",
        "SQLSERVER_DATABASE": "gestioncomercial_dev",
        "SQLSERVER_USER": "Admin1",
        "SQLSERVER_PASSWORD": "1234",

        # Gestión Diaria Orion / Causales / Discador / Lotes
        "ORION_SQL_LOCAL_DRIVER": "ODBC Driver 18 for SQL Server",
        "ORION_SQL_LOCAL_SERVER": r"localhost\SQL2025DEV",
        "ORION_SQL_LOCAL_DATABASE": ORION_DB,
        "ORION_SQL_LOCAL_USERNAME": "Admin1",
        "ORION_SQL_LOCAL_PASSWORD": "1234",
        "ORION_SQL_LOCAL_ENCRYPT": "yes",
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE": "yes",

        "ORION_CARGAS_SQL_DRIVER": "ODBC Driver 18 for SQL Server",
        "ORION_CARGAS_SQL_SERVER": r"localhost\SQL2025DEV",
        "ORION_CARGAS_SQL_DATABASE": ORION_DB,
        "ORION_CARGAS_SQL_USER": "Admin1",
        "ORION_CARGAS_SQL_PASSWORD": "1234",
        "ORION_CARGAS_SQL_ENCRYPT": "yes",
        "ORION_CARGAS_SQL_TRUST_SERVER_CERTIFICATE": "yes",
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
        new_lines.append("# ORION DATABASE FINAL - generado por fix_orion_database_name_final.py")
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

    print("\nVariables clave:")
    for key in [
        "SQLSERVER_DATABASE",
        "ORION_SQL_LOCAL_DATABASE",
        "ORION_CARGAS_SQL_DATABASE",
        "ORION_SQL_LOCAL_SERVER",
        "ORION_SQL_LOCAL_USERNAME",
        "ORION_SQL_LOCAL_PASSWORD",
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


def build_final_config_block():
    block = '''
# === FIX_ORION_DATABASE_NAME_FINAL_BEGIN ===
# Override final para separar bases:
# - SQLSERVER_DATABASE / gestioncomercial_dev: ASTER local como reemplazo de MySQL remoto.
# - ORION_SQL_LOCAL_DATABASE / Orion: Gestión Diaria Orion, Causales, Discador y Lotes.
#
# Fecha generación: __TIMESTAMP__


def _orion_final_env_first(*names, default=""):
    for _name in names:
        _value = os.getenv(_name)
        if _value is not None and str(_value).strip() != "":
            return str(_value).strip()
    return default


ORION_CARGAS_SQLSERVER_CONFIG = {
    "driver": _orion_final_env_first(
        "ORION_CARGAS_SQL_DRIVER",
        "ORION_SQL_LOCAL_DRIVER",
        default="ODBC Driver 18 for SQL Server",
    ),
    "server": _orion_final_env_first(
        "ORION_CARGAS_SQL_SERVER",
        "ORION_SQL_LOCAL_SERVER",
        default=r"localhost\\SQL2025DEV",
    ),
    "database": _orion_final_env_first(
        "ORION_CARGAS_SQL_DATABASE",
        "ORION_SQL_LOCAL_DATABASE",
        default="Orion",
    ),
    "username": _orion_final_env_first(
        "ORION_CARGAS_SQL_USER",
        "ORION_SQL_LOCAL_USERNAME",
        default="Admin1",
    ),
    "password": _orion_final_env_first(
        "ORION_CARGAS_SQL_PASSWORD",
        "ORION_SQL_LOCAL_PASSWORD",
        default="1234",
    ),
    "encrypt": _orion_final_env_first(
        "ORION_CARGAS_SQL_ENCRYPT",
        "ORION_SQL_LOCAL_ENCRYPT",
        default="yes",
    ),
    "trust_server_certificate": _orion_final_env_first(
        "ORION_CARGAS_SQL_TRUST_SERVER_CERTIFICATE",
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
        default="yes",
    ),
}


def get_orion_cargas_sqlserver_config():
    return dict(ORION_CARGAS_SQLSERVER_CONFIG)


def get_orion_cargas_connection_string():
    cfg = get_orion_cargas_sqlserver_config()

    return (
        f"DRIVER={{{cfg.get('driver', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={cfg.get('server', r'localhost\\SQL2025DEV')};"
        f"DATABASE={cfg.get('database', 'Orion')};"
        f"UID={cfg.get('username', 'Admin1')};"
        f"PWD={cfg.get('password', '1234')};"
        f"Encrypt={cfg.get('encrypt', 'yes')};"
        f"TrustServerCertificate={cfg.get('trust_server_certificate', 'yes')};"
    )


def _apply_orion_final_database_override():
    """
    Reaplica a la configuración local de Orion la base correcta: Orion.
    Esto evita que Causales, Discador y Lotes busquen en gestioncomercial_dev.
    """

    for _name in [
        "SQL_SERVER_CONFIG",
        "SQLSERVER_CONFIG",
        "ORION_SQLSERVER_CONFIG",
        "ORION_SQL_SERVER_CONFIG",
    ]:
        _cfg = globals().get(_name)

        if not isinstance(_cfg, dict):
            continue

        if isinstance(_cfg.get("local"), dict):
            _cfg["local"].update(ORION_CARGAS_SQLSERVER_CONFIG)

        elif "server" in _cfg or "database" in _cfg or "username" in _cfg:
            _cfg.update(ORION_CARGAS_SQLSERVER_CONFIG)


_apply_orion_final_database_override()

# === FIX_ORION_DATABASE_NAME_FINAL_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(datetime.now()))


def update_config():
    title("2. ACTUALIZANDO app/config.py")

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No existe: {CONFIG_FILE}")

    original = read(CONFIG_FILE)
    text = remove_old_block(original).rstrip() + "\n\n"

    if not re.search(r"^\s*import\s+os\b", text, flags=re.M):
        text = "import os\n" + text

    text += build_final_config_block()

    if text != original:
        backup(CONFIG_FILE)
        write(CONFIG_FILE, text)
        print("OK: app/config.py actualizado.")
    else:
        print("OK: app/config.py ya estaba actualizado.")


def test_orion_db():
    title("3. VALIDANDO BASE ORION Y TABLAS")

    conn_str = (
        r"DRIVER={ODBC Driver 18 for SQL Server};"
        r"SERVER=localhost\SQL2025DEV;"
        f"DATABASE={ORION_DB};"
        r"UID=Admin1;"
        r"PWD=1234;"
        r"Encrypt=yes;"
        r"TrustServerCertificate=yes;"
    )

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cur = conn.cursor()

        print("OK: conexión funcionando.")
        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())
        print("SUSER_SNAME():", cur.execute("SELECT SUSER_SNAME()").fetchval())

        rows = cur.execute(
            """
            SELECT s.name AS esquema, t.name AS tabla
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE LOWER(t.name) LIKE '%causal%'
               OR LOWER(t.name) LIKE '%discador%'
               OR LOWER(t.name) LIKE '%lote%'
            ORDER BY s.name, t.name;
            """
        ).fetchall()

        if not rows:
            print("\nAVISO: No encontré tablas con causal/discador/lote en Orion.")
            print("Listando todas las tablas:")
            rows_all = cur.execute(
                """
                SELECT s.name AS esquema, t.name AS tabla
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                ORDER BY s.name, t.name;
                """
            ).fetchall()

            for r in rows_all:
                print(f"- {r.esquema}.{r.tabla}")

            return False

        print("\nTablas encontradas:")
        for r in rows:
            print(f"- {r.esquema}.{r.tabla}")

    return True


def main():
    title("FIX FINAL - BASE ORION PARA CARGAS")

    update_env()
    update_config()

    title("4. COMPILACION")
    subprocess.run([sys.executable, "-m", "py_compile", str(CONFIG_FILE), str(Path(__file__))], check=True)
    print("OK: compila.")

    test_orion_db()

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria Orion -> Carga Causales -> Verificar Causales")
    print("  Carga Discador -> Verificar Discador")
    print("  Lotes -> Verificar Lotes")


if __name__ == "__main__":
    main()