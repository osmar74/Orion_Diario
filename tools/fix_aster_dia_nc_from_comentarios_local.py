from pathlib import Path
from datetime import datetime
import argparse
import pyodbc
import re

ROOT = Path.cwd()

CONN_GESTION_DEV = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=gestioncomercial_dev;"
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


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def normalizar_fecha(value):
    value = str(value or "").strip()

    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    raise ValueError("Fecha inválida. Usa formato YYYY-MM-DD o YYYYMMDD.")


def validar_tabla_destino():
    title("1. VALIDAR TABLA DESTINO Aster_Api.dbo.aster_dia_nc")

    with pyodbc.connect(CONN_ASTER_API, timeout=10) as conn:
        cur = conn.cursor()

        existe = cur.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='aster_dia_nc';
            """
        ).fetchval()

        if not existe:
            raise RuntimeError("No existe Aster_Api.dbo.aster_dia_nc")

        rows = cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='aster_dia_nc'
            ORDER BY ORDINAL_POSITION;
            """
        ).fetchall()

        print("Columnas destino:")
        for r in rows:
            length = "" if r.CHARACTER_MAXIMUM_LENGTH is None else f"({r.CHARACTER_MAXIMUM_LENGTH})"
            print(f"{r.ORDINAL_POSITION:02d}. {r.COLUMN_NAME} | {r.DATA_TYPE}{length} | nullable={r.IS_NULLABLE}")


def auditar_conteos(fecha):
    title(f"2. AUDITORIA DE CONTEOS PARA FECHA {fecha}")

    with pyodbc.connect(CONN_GESTION_DEV, timeout=10) as conn_src:
        cur = conn_src.cursor()

        total_origen_fecha = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.comentarios
            WHERE CAST(fecha AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        total_origen_fechainicio = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.comentarios
            WHERE CAST(fechainicio AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        print(f"Origen gestioncomercial_dev.dbo.comentarios por fecha: {total_origen_fecha}")
        print(f"Origen gestioncomercial_dev.dbo.comentarios por fechainicio: {total_origen_fechainicio}")

    with pyodbc.connect(CONN_ASTER_API, timeout=10) as conn_dst:
        cur = conn_dst.cursor()

        total_destino = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        print(f"Destino Aster_Api.dbo.aster_dia_nc por Fecha_Hora: {total_destino}")

    return total_origen_fecha, total_destino


def obtener_muestra_origen(fecha, top=10):
    title("3. MUESTRA ORIGEN Y MAPEO PROPUESTO")

    with pyodbc.connect(CONN_GESTION_DEV, timeout=10) as conn:
        cur = conn.cursor()

        rows = cur.execute(
            f"""
            SELECT TOP {int(top)}
                id,
                data,
                fecha,
                comentario,
                resultado1,
                resultado2,
                entidad,
                usuario,
                telefono,
                datafijos,
                datapers
            FROM dbo.comentarios
            WHERE CAST(fecha AS DATE) = ?
            ORDER BY fecha DESC;
            """,
            fecha,
        ).fetchall()

        print("Mapeo propuesto:")
        print("ID            <- id")
        print("Fecha_Hora    <- fecha")
        print("Numero        <- telefono si existe, si no data")
        print("Intentos      <- '1'")
        print("Estado        <- resultado1")
        print("Atendio       <- resultado2")
        print("Duracion      <- '0'")
        print("Atendido_por  <- usuario")
        print("[507]         <- '507'")
        print("Relacion      <- NULL")
        print("Codigo        <- data")
        print("Entidad       <- entidad")
        print("Cartera       <- entidad")

        print("\nMuestra transformada:")
        print("ID | Fecha_Hora | Numero | Intentos | Estado | Atendio | Duracion | Atendido_por | 507 | Relacion | Codigo | Entidad | Cartera")

        for r in rows:
            numero = r.telefono or r.data
            codigo = r.data
            print(
                f"{str(r.id)[:10]} | "
                f"{r.fecha} | "
                f"{str(numero)[:15]} | "
                f"1 | "
                f"{str(r.resultado1 or '')[:20]} | "
                f"{str(r.resultado2 or '')[:20]} | "
                f"0 | "
                f"{str(r.usuario or '')[:20]} | "
                f"507 | "
                f"" + " | "
                f"{str(codigo or '')[:12]} | "
                f"{str(r.entidad or '')[:200]} | "
                f"{str(r.entidad or '')[:50]}"
            )


def eliminar_destino_fecha(cur, fecha):
    cur.execute(
        """
        DELETE FROM dbo.aster_dia_nc
        WHERE CAST(Fecha_Hora AS DATE) = ?;
        """,
        fecha,
    )


def insertar_desde_origen(fecha, chunk_size=5000):
    title(f"4. INSERTANDO EN Aster_Api.dbo.aster_dia_nc PARA FECHA {fecha}")

    select_sql = """
        SELECT
            CAST(id AS nvarchar(10)) AS ID,
            fecha AS Fecha_Hora,
            CAST(COALESCE(NULLIF(telefono, ''), NULLIF(data, '')) AS nvarchar(15)) AS Numero,
            CAST('1' AS nvarchar(10)) AS Intentos,
            CAST(resultado1 AS nvarchar(20)) AS Estado,
            CAST(resultado2 AS nvarchar(20)) AS Atendio,
            CAST('0' AS nvarchar(10)) AS Duracion,
            CAST(usuario AS nvarchar(20)) AS Atendido_por,
            CAST('507' AS nvarchar(50)) AS [507],
            CAST(NULL AS nvarchar(50)) AS Relacion,
            CAST(data AS nvarchar(12)) AS Codigo,
            CAST(entidad AS nvarchar(200)) AS Entidad,
            CAST(entidad AS nvarchar(50)) AS Cartera
        FROM dbo.comentarios
        WHERE CAST(fecha AS DATE) = ?
        ORDER BY fecha;
    """

    insert_sql = """
        INSERT INTO dbo.aster_dia_nc
        (
            [ID],
            [Fecha_Hora],
            [Numero],
            [Intentos],
            [Estado],
            [Atendio],
            [Duracion],
            [Atendido_por],
            [507],
            [Relacion],
            [Codigo],
            [Entidad],
            [Cartera]
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    with pyodbc.connect(CONN_GESTION_DEV, timeout=30) as conn_src, pyodbc.connect(CONN_ASTER_API, timeout=30) as conn_dst:
        cur_src = conn_src.cursor()
        cur_dst = conn_dst.cursor()

        cur_dst.fast_executemany = True

        print("Eliminando registros existentes de la fecha en destino para evitar duplicados...")
        eliminar_destino_fecha(cur_dst, fecha)

        cur_src.execute(select_sql, fecha)

        total = 0

        while True:
            rows = cur_src.fetchmany(chunk_size)

            if not rows:
                break

            valores = [tuple(row) for row in rows]

            cur_dst.executemany(insert_sql, valores)

            total += len(valores)
            print(f"Insertados acumulados: {total}")

        conn_dst.commit()

    print(f"OK: registros insertados en aster_dia_nc: {total}")
    return total


def validar_final(fecha):
    title("5. VALIDACION FINAL")

    with pyodbc.connect(CONN_ASTER_API, timeout=10) as conn:
        cur = conn.cursor()

        total = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fecha,
        ).fetchval()

        print(f"Total final Aster_Api.dbo.aster_dia_nc para {fecha}: {total}")

        print("\nTOP 5 final:")
        rows = cur.execute(
            """
            SELECT TOP 5 *
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?
            ORDER BY Fecha_Hora DESC;
            """,
            fecha,
        ).fetchall()

        if not rows:
            print("Sin registros.")
        else:
            cols = [c[0] for c in cur.description]
            print(" | ".join(cols))

            for row in rows:
                print(" | ".join("" if v is None else str(v)[:80] for v in row))

    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", help="Fecha en formato YYYY-MM-DD o YYYYMMDD")
    parser.add_argument("--execute", action="store_true", help="Ejecuta DELETE+INSERT real. Sin esto solo audita.")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)

    title("FIX / CARGA SEGURA ASTER_DIA_NC DESDE COMENTARIOS LOCAL")
    print("Fecha:", fecha)
    print("Modo:", "EJECUCION REAL" if args.execute else "DRY RUN / SOLO AUDITORIA")

    validar_tabla_destino()
    origen, destino = auditar_conteos(fecha)
    obtener_muestra_origen(fecha, top=args.top)

    if not args.execute:
        title("DRY RUN FINALIZADO")
        print("No se insertó nada.")
        print("Si el mapeo se ve correcto, ejecuta:")
        print(f"  python tools\\fix_aster_dia_nc_from_comentarios_local.py {fecha} --execute")
        return

    if origen <= 0:
        raise RuntimeError("No hay registros origen para esa fecha. No se ejecuta insert.")

    insertados = insertar_desde_origen(fecha)
    total_final = validar_final(fecha)

    title("RESUMEN")
    print(f"Origen comentarios por fecha: {origen}")
    print(f"Insertados reportados:        {insertados}")
    print(f"Destino final por fecha:      {total_final}")

    if total_final != insertados:
        print("AVISO: El total final no coincide exactamente con insertados.")
    else:
        print("OK: Total destino coincide con insertados.")


if __name__ == "__main__":
    main()