from pathlib import Path
from datetime import datetime
import sys
import pyodbc
import inspect

ROOT = Path.cwd()

FECHA = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

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


def count_query(cur, sql, params=None):
    try:
        return cur.execute(sql, params or []).fetchval()
    except Exception as e:
        return f"ERROR: {e}"


def audit_target_aster_dia_nc():
    title(f"1. Aster_Api.dbo.aster_dia_nc - conteos para fecha {FECHA}")

    with pyodbc.connect(CONN_ASTER_API, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())

        total = count_query(cur, "SELECT COUNT(*) FROM dbo.aster_dia_nc")
        print("Total tabla:", total)

        por_fecha = count_query(
            cur,
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?
            """,
            [FECHA],
        )
        print(f"Total Fecha_Hora = {FECHA}:", por_fecha)

        print("\nÚltimas 10 fechas en aster_dia_nc:")
        rows = cur.execute(
            """
            SELECT TOP 10
                CAST(Fecha_Hora AS DATE) AS fecha,
                COUNT(*) AS total
            FROM dbo.aster_dia_nc
            GROUP BY CAST(Fecha_Hora AS DATE)
            ORDER BY CAST(Fecha_Hora AS DATE) DESC
            """
        ).fetchall()

        for r in rows:
            print(f"- {r.fecha}: {r.total}")

        print("\nTOP 5 para fecha indicada:")
        rows = cur.execute(
            """
            SELECT TOP 5 *
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?
            ORDER BY Fecha_Hora DESC
            """,
            [FECHA],
        ).fetchall()

        if not rows:
            print("Sin registros para esa fecha.")
        else:
            cols = [c[0] for c in cur.description]
            print(" | ".join(cols))
            for row in rows:
                print(" | ".join("" if v is None else str(v)[:80] for v in row))


def audit_aster_api_other_tables():
    title("2. Aster_Api - verificar si Fase I insertó en otras tablas")

    with pyodbc.connect(CONN_ASTER_API, timeout=10) as conn:
        cur = conn.cursor()

        rows = cur.execute(
            """
            SELECT s.name AS esquema, t.name AS tabla
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id=s.schema_id
            WHERE LOWER(t.name) IN ('usuarios', 'comentarios', 'aster_dia_nc')
               OR LOWER(t.name) LIKE '%usuario%'
               OR LOWER(t.name) LIKE '%coment%'
               OR LOWER(t.name) LIKE '%aster%dia%nc%'
            ORDER BY s.name, t.name
            """
        ).fetchall()

        for r in rows:
            full = f"[{r.esquema}].[{r.tabla}]"
            total = count_query(cur, f"SELECT COUNT(*) FROM {full}")
            print(f"{r.esquema}.{r.tabla}: {total}")


def audit_source_local():
    title(f"3. gestioncomercial_dev - origen local para fecha {FECHA}")

    with pyodbc.connect(CONN_GESTION_DEV, timeout=10) as conn:
        cur = conn.cursor()

        print("DB_NAME():", cur.execute("SELECT DB_NAME()").fetchval())

        print("\nConteos generales:")
        for table in ["usuarios", "crm", "comentarios"]:
            total = count_query(cur, f"SELECT COUNT(*) FROM dbo.{table}")
            print(f"dbo.{table}: {total}")

        print("\nConteos dbo.comentarios por posibles columnas de fecha:")
        for col in ["fecha", "fechaagenda", "fechainicio"]:
            total = count_query(
                cur,
                f"""
                SELECT COUNT(*)
                FROM dbo.comentarios
                WHERE CAST([{col}] AS DATE) = ?
                """,
                [FECHA],
            )
            print(f"dbo.comentarios WHERE CAST({col} AS DATE) = {FECHA}: {total}")

        print("\nTOP 5 dbo.comentarios para fecha en columna fecha:")
        try:
            rows = cur.execute(
                """
                SELECT TOP 5 *
                FROM dbo.comentarios
                WHERE CAST(fecha AS DATE) = ?
                ORDER BY fecha DESC
                """,
                [FECHA],
            ).fetchall()

            if not rows:
                print("Sin registros por columna fecha.")
            else:
                cols = [c[0] for c in cur.description]
                print(" | ".join(cols))
                for row in rows:
                    print(" | ".join("" if v is None else str(v)[:80] for v in row))

        except Exception as e:
            print("No se pudo leer TOP 5:", e)


def audit_python_services():
    title("4. Auditoría de servicios Python usados por Fase I")

    try:
        from app.services import aster_source_service as src

        for name in [
            "leer_comentarios_origen_fase_i",
            "leer_usuarios_origen_fase_i",
            "contar_comentarios_origen_fase_i",
            "contar_usuarios_origen_fase_i",
        ]:
            fn = getattr(src, name, None)
            if fn:
                print(f"{name}{inspect.signature(fn)}")
            else:
                print(f"{name}: NO EXISTE")

    except Exception as e:
        print("No se pudo importar aster_source_service:", e)

    try:
        from app.services import aster_phase_i_execution_service as exe

        for name in [
            "ejecutar_fase_i_aster",
            "insertar_dataframe_sql_fase_i",
            "preparar_columnas_insert_fase_i",
            "construir_dataframe_insert_fase_i",
        ]:
            fn = getattr(exe, name, None)
            if fn:
                print(f"{name}{inspect.signature(fn)}")
            else:
                print(f"{name}: NO EXISTE")

    except Exception as e:
        print("No se pudo importar aster_phase_i_execution_service:", e)


def main():
    title("AUDITORIA ASTER_DIA_NC POR FECHA Y FASE I")
    print("Fecha auditada:", FECHA)

    audit_target_aster_dia_nc()
    audit_aster_api_other_tables()
    audit_source_local()
    audit_python_services()

    title("FIN")
    print("Si Aster_Api.dbo.aster_dia_nc por fecha da 0, pero el origen local da 41240,")
    print("entonces Fase I no está insertando en aster_dia_nc para esa fecha.")


if __name__ == "__main__":
    main()