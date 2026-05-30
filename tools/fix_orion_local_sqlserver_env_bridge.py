from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import os
import re
import pyodbc

ROOT = Path.cwd()

# Permite importar app.config cuando el script se ejecuta desde tools/
sys.path.insert(0, str(ROOT))

ENV_FILE = ROOT / ".env"
CONFIG_FILE = ROOT / "app" / "config.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

MARKER_BEGIN = "# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_BEGIN ==="
MARKER_END = "# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_END ==="


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


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def mask_value(key, value):
    if "PASSWORD" in key.upper() or key.lower() == "password":
        return "***"
    return value


def parse_env_text(text):
    data = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")

    return data


def ensure_env_values():
    title("1. VERIFICANDO .env")

    required = {
        "SQLSERVER_DRIVER": "ODBC Driver 18 for SQL Server",
        "SQLSERVER_SERVER": r"localhost\SQL2025DEV",
        "SQLSERVER_DATABASE": "gestioncomercial_dev",
        "SQLSERVER_USER": "Admin1",
        "SQLSERVER_PASSWORD": "1234",

        "ORION_SQL_LOCAL_DRIVER": "ODBC Driver 18 for SQL Server",
        "ORION_SQL_LOCAL_SERVER": r"localhost\SQL2025DEV",
        "ORION_SQL_LOCAL_DATABASE": "gestioncomercial_dev",
        "ORION_SQL_LOCAL_USERNAME": "Admin1",
        "ORION_SQL_LOCAL_PASSWORD": "1234",
        "ORION_SQL_LOCAL_ENCRYPT": "yes",
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE": "yes",

        "GESTION_SQL_DRIVER": "ODBC Driver 18 for SQL Server",
        "GESTION_SQL_LOCAL_SERVER": r"localhost\SQL2025DEV",
        "GESTION_SQL_DATABASE": "gestioncomercial_dev",
        "GESTION_SQL_USER": "Admin1",
        "GESTION_SQL_PASSWORD": "1234",
    }

    original = read(ENV_FILE) if ENV_FILE.exists() else ""
    existing = parse_env_text(original)

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

    missing = [k for k in required if k not in written]

    if missing:
        new_lines.append("")
        new_lines.append("# ORION SQL SERVER LOCAL - generado por fix_orion_local_sqlserver_env_bridge_v2.py")

        for key in missing:
            new_lines.append(f"{key}={required[key]}")

    new_text = "\n".join(new_lines).rstrip() + "\n"

    if new_text != original:
        backup(ENV_FILE)
        write(ENV_FILE, new_text)
        print("OK: .env actualizado.")
    else:
        print("OK: .env ya estaba correcto.")

    final_env = parse_env_text(new_text)

    for key in [
        "SQLSERVER_SERVER",
        "SQLSERVER_DATABASE",
        "SQLSERVER_USER",
        "SQLSERVER_PASSWORD",
        "ORION_SQL_LOCAL_SERVER",
        "ORION_SQL_LOCAL_DATABASE",
        "ORION_SQL_LOCAL_USERNAME",
        "ORION_SQL_LOCAL_PASSWORD",
        "GESTION_SQL_LOCAL_SERVER",
        "GESTION_SQL_USER",
        "GESTION_SQL_PASSWORD",
    ]:
        print(f"- {key}={mask_value(key, final_env.get(key, ''))}")


def remove_old_bridge_block(text):
    if MARKER_BEGIN not in text:
        return text

    before = text.split(MARKER_BEGIN, 1)[0].rstrip()
    rest = text.split(MARKER_BEGIN, 1)[1]

    if MARKER_END in rest:
        after = rest.split(MARKER_END, 1)[1].lstrip()
        return before + "\n\n" + after

    return before + "\n"


def build_bridge_block():
    timestamp = datetime.now()

    block = '''
# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_BEGIN ===
# Puente de configuración SQL Server local para Gestión Diaria Orion.
#
# Motivo:
#   Algunos módulos usan variables ORION_SQL_LOCAL_*.
#   Otros scripts/servicios ya usaban SQLSERVER_*.
#   Este bloque unifica ambas familias de variables para evitar Login failed
#   por password vacío o variable no encontrada.
#
# Fecha generación: __TIMESTAMP__


def _orion_env_first(*names, default=""):
    for _name in names:
        _value = os.getenv(_name)
        if _value is not None and str(_value).strip() != "":
            return str(_value).strip()
    return default


_ORION_LOCAL_SQLSERVER_CONFIG = {
    "driver": _orion_env_first(
        "ORION_SQL_LOCAL_DRIVER",
        "SQLSERVER_DRIVER",
        default="ODBC Driver 18 for SQL Server",
    ),
    "server": _orion_env_first(
        "ORION_SQL_LOCAL_SERVER",
        "SQLSERVER_SERVER",
        default=r"localhost\\SQL2025DEV",
    ),
    "database": _orion_env_first(
        "ORION_SQL_LOCAL_DATABASE",
        "SQLSERVER_DATABASE",
        default="gestioncomercial_dev",
    ),
    "username": _orion_env_first(
        "ORION_SQL_LOCAL_USERNAME",
        "SQLSERVER_USER",
        default="Admin1",
    ),
    "password": _orion_env_first(
        "ORION_SQL_LOCAL_PASSWORD",
        "SQLSERVER_PASSWORD",
        default="1234",
    ),
    "encrypt": _orion_env_first(
        "ORION_SQL_LOCAL_ENCRYPT",
        default="yes",
    ),
    "trust_server_certificate": _orion_env_first(
        "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE",
        default="yes",
    ),
}


def _orion_apply_local_sqlserver_bridge():
    """
    Aplica la conexión local correcta sobre los diccionarios de configuración
    que existan en este módulo, sin tocar configuración remota.
    """

    _candidate_names = [
        "SQL_SERVER_CONFIG",
        "SQLSERVER_CONFIG",
        "ORION_SQLSERVER_CONFIG",
        "ORION_SQL_SERVER_CONFIG",
    ]

    for _name in _candidate_names:
        _cfg = globals().get(_name)

        if not isinstance(_cfg, dict):
            continue

        # Caso típico: {"local": {...}, "remoto": {...}}
        if isinstance(_cfg.get("local"), dict):
            _cfg["local"].update(_ORION_LOCAL_SQLSERVER_CONFIG)

        # Caso alternativo: {"server": ..., "database": ...}
        elif "server" in _cfg or "database" in _cfg or "username" in _cfg:
            _cfg.update(_ORION_LOCAL_SQLSERVER_CONFIG)


_orion_apply_local_sqlserver_bridge()

# === FIX_ORION_LOCAL_SQLSERVER_ENV_BRIDGE_END ===
'''.strip() + "\n"

    return block.replace("__TIMESTAMP__", str(timestamp))


def update_config():
    title("2. ACTUALIZANDO app/config.py")

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No existe: {CONFIG_FILE}")

    original = read(CONFIG_FILE)
    text = remove_old_bridge_block(original).rstrip() + "\n\n"

    if not re.search(r"^\s*import\s+os\b", text, flags=re.M):
        text = "import os\n" + text

    text += build_bridge_block()

    if text != original:
        backup(CONFIG_FILE)
        write(CONFIG_FILE, text)
        print("OK: app/config.py actualizado.")
    else:
        print("OK: app/config.py ya estaba actualizado.")


def load_env_into_process():
    if not ENV_FILE.exists():
        return {}

    env = parse_env_text(read(ENV_FILE))

    for k, v in env.items():
        os.environ[k] = v

    return env


def build_conn_from_env(env):
    driver = env.get("ORION_SQL_LOCAL_DRIVER") or env.get("SQLSERVER_DRIVER") or "ODBC Driver 18 for SQL Server"
    server = env.get("ORION_SQL_LOCAL_SERVER") or env.get("SQLSERVER_SERVER") or r"localhost\SQL2025DEV"
    database = env.get("ORION_SQL_LOCAL_DATABASE") or env.get("SQLSERVER_DATABASE") or "gestioncomercial_dev"
    user = env.get("ORION_SQL_LOCAL_USERNAME") or env.get("SQLSERVER_USER") or "Admin1"
    password = env.get("ORION_SQL_LOCAL_PASSWORD") or env.get("SQLSERVER_PASSWORD") or "1234"

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


def validate_direct_connection():
    title("3. VALIDANDO CONEXION DIRECTA DESDE .env")

    env = load_env_into_process()
    conn_str = build_conn_from_env(env)
    safe = re.sub(r"PWD=[^;]*", "PWD=***", conn_str)

    print("Cadena usada:")
    print(safe)

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cur = conn.cursor()
        print("OK: conexión SQL Server funcionando.")
        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())
        print("SUSER_SNAME():", cur.execute("SELECT SUSER_SNAME()").fetchval())


def validate_config_import():
    title("4. VALIDANDO app.config")

    load_env_into_process()

    import importlib
    cfg_module = importlib.import_module("app.config")

    found = False

    for name in [
        "SQL_SERVER_CONFIG",
        "SQLSERVER_CONFIG",
        "ORION_SQLSERVER_CONFIG",
        "ORION_SQL_SERVER_CONFIG",
    ]:
        cfg = getattr(cfg_module, name, None)

        if not isinstance(cfg, dict):
            continue

        found = True

        local_cfg = cfg.get("local") if isinstance(cfg.get("local"), dict) else cfg

        print(f"\n{name}:")
        for k in ["driver", "server", "database", "username", "password", "encrypt", "trust_server_certificate"]:
            if k in local_cfg:
                print(f"- {k}: {mask_value(k, str(local_cfg[k]))}")

    if not found:
        print("AVISO: No encontré diccionario SQL Server conocido en app.config.")
        print("Si la app sigue fallando, revisaremos el archivo exacto que arma conn_str.")


def main():
    title("FIX ORION LOCAL SQL SERVER ENV BRIDGE V2")

    print("Root:", ROOT)

    ensure_env_values()
    update_config()

    title("5. COMPILACION")
    subprocess.run([sys.executable, "-m", "py_compile", str(CONFIG_FILE), str(Path(__file__))], check=True)
    print("OK: py_compile correcto.")

    validate_direct_connection()
    validate_config_import()

    title("FINALIZADO")
    print("Ahora reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria Orion -> Carga Causales -> Verificar Causales")
    print("  Gestión Diaria Orion -> Carga Discador -> Verificar Discador")
    print("  Gestión Diaria Orion -> Lotes -> Verificar Lotes")


if __name__ == "__main__":
    main()