from pathlib import Path
import pyodbc
import re

ROOT = Path.cwd()

CONN_MASTER = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=master;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

CONN_ASTER_API = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=Aster_Api;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

CONN_GESTION_DEV = (
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


def audit_find_table():
    title("1. BUSCAR TABLA Aster_dia_nc EN TODAS LAS BASES")

    with pyodbc.connect(CONN_MASTER, timeout=10) as conn:
        cur = conn.cursor()

        dbs = [
            r.name
            for r in cur.execute(
                "SELECT name FROM sys.databases WHERE state_desc='ONLINE' ORDER BY name"
            ).fetchall()
        ]

        encontrados = []

        for db in dbs:
            try:
                rows = cur.execute(
                    f"""
                    SELECT
                        '{db}' AS dbname,
                        s.name AS schema_name,
                        t.name AS table_name
                    FROM [{db}].sys.tables t
                    INNER JOIN [{db}].sys.schemas s ON t.schema_id = s.schema_id
                    WHERE LOWER(t.name) LIKE '%aster%dia%nc%'
                       OR LOWER(t.name) LIKE '%dia%nc%'
                       OR LOWER(t.name) LIKE '%aster%'
                    ORDER BY s.name, t.name;
                    """
                ).fetchall()

                for r in rows:
                    print(f"{r.dbname}.{r.schema_name}.{r.table_name}")
                    if r.table_name.lower() == "aster_dia_nc":
                        encontrados.append((r.dbname, r.schema_name, r.table_name))

            except Exception:
                pass

        if not encontrados:
            print("\nAVISO: No encontré tabla exacta Aster_dia_nc.")
        else:
            print("\nTabla exacta encontrada:")
            for db, schema, table in encontrados:
                print(f"- {db}.{schema}.{table}")

        return encontrados


def audit_target_table(db="Aster_Api", schema="dbo", table="Aster_dia_nc"):
    title(f"2. AUDITAR TABLA DESTINO {db}.{schema}.{table}")

    conn_str = (
        r"DRIVER={ODBC Driver 18 for SQL Server};"
        r"SERVER=localhost\SQL2025DEV;"
        f"DATABASE={db};"
        r"UID=Admin1;"
        r"PWD=1234;"
        r"Encrypt=yes;"
        r"TrustServerCertificate=yes;"
    )

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cur = conn.cursor()

        exists = cur.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?;
            """,
            schema,
            table,
        ).fetchval()

        if not exists:
            print(f"No existe {db}.{schema}.{table}")
            return

        count = cur.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}];").fetchval()
        print(f"Total registros actuales: {count}")

        print("\nColumnas:")
        rows = cur.execute(
            """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION;
            """,
            schema,
            table,
        ).fetchall()

        for r in rows:
            length = "" if r.CHARACTER_MAXIMUM_LENGTH is None else f"({r.CHARACTER_MAXIMUM_LENGTH})"
            print(
                f"{r.ORDINAL_POSITION:02d}. {r.COLUMN_NAME} | "
                f"{r.DATA_TYPE}{length} | nullable={r.IS_NULLABLE}"
            )

        print("\nTOP 5:")
        try:
            rows_top = cur.execute(f"SELECT TOP 5 * FROM [{schema}].[{table}];").fetchall()
            cols = [c[0] for c in cur.description]
            print(" | ".join(cols))

            for row in rows_top:
                print(" | ".join("" if v is None else str(v)[:80] for v in row))

        except Exception as e:
            print("No se pudo leer TOP 5:", e)


def audit_source_counts():
    title("3. AUDITAR ORIGEN LOCAL gestioncomercial_dev")

    with pyodbc.connect(CONN_GESTION_DEV, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())

        for table in ["usuarios", "comentarios", "crm"]:
            try:
                count = cur.execute(f"SELECT COUNT(*) FROM dbo.{table};").fetchval()
                print(f"dbo.{table}: {count}")
            except Exception as e:
                print(f"dbo.{table}: ERROR -> {e}")


def audit_code_references():
    title("4. BUSCAR REFERENCIAS EN CODIGO")

    terms = [
        "Aster_dia_nc",
        "aster_dia_nc",
        "dia_nc",
        "insertar_dataframe_sql_fase_i",
        "rowcount",
        "executemany",
        "usuarios_insertados",
        "comentarios_insertados",
    ]

    for path in list((ROOT / "app").rglob("*.py")) + list((ROOT / "sql").rglob("*.sql")):
        text = path.read_text(encoding="utf-8", errors="ignore")

        if not any(t.lower() in text.lower() for t in terms):
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")

        for i, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()

            if any(t.lower() in lower for t in terms):
                safe = re.sub(r"PWD=[^;]+", "PWD=***", line)
                print(f"{i:04d}: {safe[:260]}")


def main():
    encontrados = audit_find_table()

    if encontrados:
        for db, schema, table in encontrados:
            if table.lower() == "aster_dia_nc":
                audit_target_table(db, schema, table)
    else:
        audit_target_table("Aster_Api", "dbo", "Aster_dia_nc")

    audit_source_counts()
    audit_code_references()

    title("FIN AUDITORIA")
    print("Pega esta salida si todavía no queda claro si el problema es contador o inserción real.")


if __name__ == "__main__":
    main()