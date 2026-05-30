from pathlib import Path
import re
import pyodbc
from datetime import datetime

ROOT = Path.cwd()

LOCAL_CONN_STR = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=gestioncomercial_dev;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def should_skip(path: Path):
    parts = set(path.parts)
    return bool(parts & EXCLUDE_DIRS)


def read_text(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore")


def audit_connection_test():
    title("AUDITORIA 1 - PRUEBA DIRECTA CON CONEXION LOCAL CORRECTA")

    print("Fecha:", datetime.now())
    print("Servidor: localhost\\SQL2025DEV")
    print("Base: gestioncomercial_dev")
    print("Usuario: Admin1")
    print("Password: 1234")

    try:
        conn = pyodbc.connect(LOCAL_CONN_STR, timeout=10)
        cur = conn.cursor()
        db = cur.execute("SELECT DB_NAME()").fetchval()
        user = cur.execute("SELECT SUSER_SNAME()").fetchval()
        version = cur.execute("SELECT @@VERSION").fetchval()

        print("\nOK: conexión directa funcionando.")
        print("DB_NAME():", db)
        print("SUSER_SNAME():", user)
        print("VERSION:", str(version).splitlines()[0])

        conn.close()

    except Exception as e:
        print("\nERROR: La conexión directa falló.")
        print(e)
        raise


def audit_files():
    title("AUDITORIA 2 - BUSQUEDA DE CONEXIONES SQL SERVER EN ARCHIVOS")

    patterns = [
        "pyodbc.connect",
        "ODBC Driver",
        "SQL Server",
        "SQL2025DEV",
        "SQLEXPRESS",
        "gestioncomercial_dev",
        "Admin1",
        "PWD=",
        "UID=",
        "SQLALCHEMY_DATABASE_URI",
    ]

    files = []

    for ext in ["*.py", "*.env", "*.ini", "*.cfg", "*.txt", "*.bat", "*.cmd"]:
        for path in ROOT.rglob(ext):
            if should_skip(path):
                continue

            text = read_text(path)

            if any(p.lower() in text.lower() for p in patterns):
                files.append(path)

    if not files:
        print("No se encontraron archivos con patrones de conexión.")
        return

    for path in sorted(files):
        rel = path.relative_to(ROOT)
        print(f"\n--- {rel} ---")

        lines = read_text(path).splitlines()

        for i, line in enumerate(lines, start=1):
            lower = line.lower()

            if any(p.lower() in lower for p in patterns):
                safe_line = line

                # Enmascarar passwords para auditoría
                safe_line = re.sub(r"(PWD\s*=\s*)[^;'\"]+", r"\1***", safe_line, flags=re.I)
                safe_line = re.sub(r"(PASSWORD\s*=\s*)[^;'\"]+", r"\1***", safe_line, flags=re.I)
                safe_line = re.sub(r"('password'\s*:\s*)['\"][^'\"]*['\"]", r"\1'***'", safe_line, flags=re.I)
                safe_line = re.sub(r'("password"\s*:\s*)["\"][^"\"]*["\"]', r'\1"***"', safe_line, flags=re.I)

                print(f"{i:04d}: {safe_line}")


def audit_possible_bad_strings():
    title("AUDITORIA 3 - POSIBLES CADENAS MAL CONFIGURADAS")

    bad_hits = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        if path.suffix.lower() not in [".py", ".env", ".ini", ".cfg", ".txt", ".bat", ".cmd"]:
            continue

        text = read_text(path)

        suspicious = False

        if "Admin1" in text and "PWD=1234" not in text:
            suspicious = True

        if "ODBC Driver 18 for SQL Server" in text and "TrustServerCertificate=yes" not in text:
            suspicious = True

        if "localhost\\SQL2025DEV" in text and "gestioncomercial_dev" not in text:
            suspicious = True

        if suspicious:
            bad_hits.append(path.relative_to(ROOT))

    if not bad_hits:
        print("No se encontraron cadenas sospechosas evidentes.")
    else:
        print("Archivos sospechosos:")
        for p in bad_hits:
            print("-", p)


def main():
    audit_connection_test()
    audit_files()
    audit_possible_bad_strings()

    title("FIN AUDITORIA")
    print("Si la prueba directa funciona pero la app falla, el problema está en alguna cadena usada por el módulo Orion.")


if __name__ == "__main__":
    main()