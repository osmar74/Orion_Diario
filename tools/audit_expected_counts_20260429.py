import argparse
import pyodbc
import re

SERVER_CONN = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=master;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

EXPECTED = {
    ("Aster_Api", "aster_dia_nc"): 41240,
    ("Aster_Api", "comentarios"): 7338,
    ("Aster_Api", "usuarios"): 337,
    ("Orion", "causales"): 590,
    ("Orion", "lote"): 3006,
    ("Orion", "discador"): 2194,
}


def normalizar_fecha(value):
    value = str(value or "").strip()

    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    raise ValueError("Fecha inválida. Usa YYYY-MM-DD o YYYYMMDD.")


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def safe_count(cur, sql, params=None):
    try:
        return cur.execute(sql, params or []).fetchval()
    except Exception as e:
        return f"ERROR: {e}"


def get_date_columns(cur, db, schema, table):
    rows = cur.execute(
        f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM [{db}].INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
          AND (
                DATA_TYPE IN ('date','datetime','datetime2','smalldatetime')
             OR LOWER(COLUMN_NAME) LIKE '%fecha%'
             OR LOWER(COLUMN_NAME) LIKE '%date%'
             OR LOWER(COLUMN_NAME) LIKE '%hora%'
          )
        ORDER BY ORDINAL_POSITION;
        """,
        schema,
        table,
    ).fetchall()

    return [(r.COLUMN_NAME, r.DATA_TYPE) for r in rows]


def audit_expected_tables(cur, fecha):
    title(f"1. VALIDAR CONTEOS ESPERADOS PARA {fecha}")

    for (db, table), expected in EXPECTED.items():
        rows = cur.execute(
            f"""
            SELECT s.name AS schema_name, t.name AS table_name
            FROM [{db}].sys.tables t
            INNER JOIN [{db}].sys.schemas s ON t.schema_id = s.schema_id
            WHERE LOWER(t.name) = LOWER(?)
            ORDER BY s.name, t.name;
            """,
            table,
        ).fetchall()

        if not rows:
            print(f"{db}.dbo.{table}: NO EXISTE | esperado={expected}")
            continue

        for r in rows:
            date_cols = get_date_columns(cur, db, r.schema_name, r.table_name)

            print(f"\n{db}.{r.schema_name}.{r.table_name} | esperado={expected}")

            if not date_cols:
                total = safe_count(cur, f"SELECT COUNT(*) FROM [{db}].[{r.schema_name}].[{r.table_name}]")
                print(f"  Sin columna fecha detectada. Total general: {total}")
                continue

            for col, dtype in date_cols:
                count = safe_count(
                    cur,
                    f"""
                    SELECT COUNT(*)
                    FROM [{db}].[{r.schema_name}].[{r.table_name}]
                    WHERE TRY_CAST([{col}] AS DATE) = ?;
                    """,
                    [fecha],
                )

                ok = "OK" if count == expected else "NO"
                print(f"  {col} ({dtype}) = {count} | esperado={expected} | {ok}")


def audit_possible_sources_for_aster_dia_nc(cur, fecha):
    title("2. BUSCAR ORIGEN QUE DA 41.240")

    target_count = 41240

    dbs = [
        "after_no_contactados",
        "Aster_Api",
        "gestioncomercial_dev",
        "gestioncomercial",
        "usuarios",
    ]

    for db in dbs:
        try:
            tables = cur.execute(
                f"""
                SELECT s.name AS schema_name, t.name AS table_name
                FROM [{db}].sys.tables t
                INNER JOIN [{db}].sys.schemas s ON t.schema_id = s.schema_id
                ORDER BY s.name, t.name;
                """
            ).fetchall()
        except Exception as e:
            print(f"No se pudo leer {db}: {e}")
            continue

        print(f"\n--- DB {db} ---")

        for t in tables:
            date_cols = get_date_columns(cur, db, t.schema_name, t.table_name)

            if not date_cols:
                continue

            for col, dtype in date_cols:
                count = safe_count(
                    cur,
                    f"""
                    SELECT COUNT(*)
                    FROM [{db}].[{t.schema_name}].[{t.table_name}]
                    WHERE TRY_CAST([{col}] AS DATE) = ?;
                    """,
                    [fecha],
                )

                if isinstance(count, int) and (count == target_count or count > 0):
                    marker = "<<< MATCH 41240" if count == target_count else ""
                    print(f"{db}.{t.schema_name}.{t.table_name}.{col} = {count} {marker}")


def audit_breakdown_gestion_dev(cur, fecha):
    title("3. DESGLOSE gestioncomercial_dev.dbo.comentarios PARA ENTENDER 57.396 VS 41.240")

    db = "gestioncomercial_dev"

    total = safe_count(
        cur,
        f"""
        SELECT COUNT(*)
        FROM [{db}].dbo.comentarios
        WHERE TRY_CAST(fecha AS DATE)=?;
        """,
        [fecha],
    )

    print("Total por fecha:", total)

    distincts = [
        "id",
        "data",
        "telefono",
        "uniqueid",
        "linkedid",
        "unico",
    ]

    for col in distincts:
        count = safe_count(
            cur,
            f"""
            SELECT COUNT(DISTINCT [{col}])
            FROM [{db}].dbo.comentarios
            WHERE TRY_CAST(fecha AS DATE)=?;
            """,
            [fecha],
        )
        marker = "<<< MATCH 41240" if count == 41240 else ""
        print(f"DISTINCT {col}: {count} {marker}")

    print("\nPor entidad:")
    rows = cur.execute(
        f"""
        SELECT TOP 100 entidad, COUNT(*) total
        FROM [{db}].dbo.comentarios
        WHERE TRY_CAST(fecha AS DATE)=?
        GROUP BY entidad
        ORDER BY total DESC;
        """,
        fecha,
    ).fetchall()

    for r in rows:
        print(f"{r.entidad} | {r.total}")

    print("\nPor resultado1 / resultado2:")
    rows = cur.execute(
        f"""
        SELECT TOP 100 resultado1, resultado2, COUNT(*) total
        FROM [{db}].dbo.comentarios
        WHERE TRY_CAST(fecha AS DATE)=?
        GROUP BY resultado1, resultado2
        ORDER BY total DESC;
        """,
        fecha,
    ).fetchall()

    for r in rows:
        print(f"{r.resultado1} | {r.resultado2} | {r.total}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha")
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)

    print("Fecha:", fecha)

    with pyodbc.connect(SERVER_CONN, timeout=30) as conn:
        cur = conn.cursor()

        audit_expected_tables(cur, fecha)
        audit_possible_sources_for_aster_dia_nc(cur, fecha)
        audit_breakdown_gestion_dev(cur, fecha)

    title("FIN")
    print("Busca en la salida la línea que diga <<< MATCH 41240.")
    print("Ese será el origen/filtro correcto para aster_dia_nc.")


if __name__ == "__main__":
    main()