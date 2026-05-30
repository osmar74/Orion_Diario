import argparse
import pyodbc
from datetime import datetime
import re

CONN_ASTER_API = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=Aster_Api;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)


def normalizar_fecha(value):
    value = str(value or "").strip()

    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    raise ValueError("Fecha inválida. Usa YYYY-MM-DD o YYYYMMDD.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", help="Fecha YYYY-MM-DD o YYYYMMDD")
    parser.add_argument("--execute", action="store_true", help="Ejecuta DELETE real")
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)

    print("=" * 100)
    print("ROLLBACK Aster_Api.dbo.aster_dia_nc")
    print("=" * 100)
    print("Fecha:", fecha)
    print("Modo:", "EJECUCION REAL" if args.execute else "DRY RUN")

    with pyodbc.connect(CONN_ASTER_API, timeout=20) as conn:
        cur = conn.cursor()

        antes = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        print("Registros antes:", antes)

        if not args.execute:
            print("\nDRY RUN. No se borró nada.")
            print(f"Para borrar la carga incorrecta ejecuta:")
            print(f"  python tools\\rollback_aster_dia_nc_fecha.py {fecha} --execute")
            return

        cur.execute(
            """
            DELETE FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fecha,
        )

        conn.commit()

        despues = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        print("Registros después:", despues)

        if despues == 0:
            print("OK: fecha limpiada correctamente.")
        else:
            print("AVISO: todavía quedan registros para esa fecha.")


if __name__ == "__main__":
    main()