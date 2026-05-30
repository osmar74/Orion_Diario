from pathlib import Path
from datetime import datetime
import argparse
import shutil
import re
import sys

import pandas as pd
import pyodbc


ROOT = Path.cwd()

CONN_ASTER_API = (
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=localhost\SQL2025DEV;"
    r"DATABASE=Aster_Api;"
    r"UID=Admin1;"
    r"PWD=1234;"
    r"Encrypt=yes;"
    r"TrustServerCertificate=yes;"
)

COLUMNAS_DESTINO = [
    "ID",
    "Fecha_Hora",
    "Numero",
    "Intentos",
    "Estado",
    "Atendio",
    "Duracion",
    "Atendido_por",
    "507",
    "Relacion",
    "Codigo",
    "Entidad",
    "Cartera",
]

LIMITES = {
    "ID": 10,
    "Numero": 15,
    "Intentos": 10,
    "Estado": 20,
    "Atendio": 20,
    "Duracion": 10,
    "Atendido_por": 20,
    "507": 50,
    "Relacion": 50,
    "Codigo": 12,
    "Entidad": 200,
    "Cartera": 50,
}


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def normalizar_fecha(value):
    value = str(value or "").strip().replace("-", "")

    if not re.fullmatch(r"\d{8}", value):
        raise ValueError("Fecha inválida. Usa YYYYMMDD o YYYY-MM-DD.")

    return value


def fecha_sql(fecha_yyyymmdd):
    return f"{fecha_yyyymmdd[:4]}-{fecha_yyyymmdd[4:6]}-{fecha_yyyymmdd[6:8]}"


def normalizar_col_name(value):
    return str(value or "").strip().lower().replace(" ", "_")


def leer_excel(path):
    df = pd.read_excel(path)
    df = df.dropna(how="all")
    return df


def preparar_dataframe(df):
    columnas_map = {
        normalizar_col_name(c): c
        for c in df.columns
    }

    faltantes = []

    for col in COLUMNAS_DESTINO:
        if normalizar_col_name(col) not in columnas_map:
            faltantes.append(col)

    if faltantes:
        raise RuntimeError(
            "El Excel normalizado no tiene columnas requeridas para aster_dia_nc: "
            + ", ".join(faltantes)
        )

    salida = pd.DataFrame()

    for col in COLUMNAS_DESTINO:
        salida[col] = df[columnas_map[normalizar_col_name(col)]]

    salida["Fecha_Hora"] = pd.to_datetime(salida["Fecha_Hora"], errors="coerce")

    invalidas_fecha = salida["Fecha_Hora"].isna().sum()

    if invalidas_fecha:
        raise RuntimeError(f"Hay {invalidas_fecha} registros con Fecha_Hora inválida.")

    for col, max_len in LIMITES.items():
        salida[col] = salida[col].fillna("").astype(str).str.slice(0, max_len)

    return salida


def rutas(fecha):
    base = ROOT / "data" / fecha / "Aster" / f"aster_{fecha}"

    normalizado = base / "Normalizado" / f"After{fecha}_normalizado.xlsx"
    gestion_dir = base / "Gestion"
    gestion = gestion_dir / f"{fecha}_Gestion_aster.xlsx"

    return base, normalizado, gestion_dir, gestion


def auditar_sql(fecha):
    fsql = fecha_sql(fecha)

    with pyodbc.connect(CONN_ASTER_API, timeout=20) as conn:
        cur = conn.cursor()

        total_fecha = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fsql,
        ).fetchval()

        total_general = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc;
            """
        ).fetchval()

        print(f"SQL Aster_Api.dbo.aster_dia_nc total general: {total_general}")
        print(f"SQL Aster_Api.dbo.aster_dia_nc fecha {fsql}: {total_fecha}")

        return total_fecha


def escribir_gestion_excel(df, gestion_path):
    gestion_path.parent.mkdir(parents=True, exist_ok=True)

    if gestion_path.exists():
        backup = gestion_path.with_suffix(
            gestion_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy2(gestion_path, backup)
        print("Backup archivo Gestión anterior:", backup)

    df.to_excel(gestion_path, index=False)

    validacion = leer_excel(gestion_path)

    print("Archivo Gestión escrito:", gestion_path)
    print("Filas validación Gestión:", len(validacion))

    return len(validacion)


def cargar_sql(df, fecha):
    fsql = fecha_sql(fecha)

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

    valores = [
        tuple(row[col] for col in COLUMNAS_DESTINO)
        for _, row in df.iterrows()
    ]

    with pyodbc.connect(CONN_ASTER_API, timeout=30) as conn:
        cur = conn.cursor()
        cur.fast_executemany = True

        antes = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fsql,
        ).fetchval()

        print(f"Registros destino antes para {fsql}: {antes}")

        print("Eliminando registros existentes de esa fecha...")
        cur.execute(
            """
            DELETE FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fsql,
        )

        print("Insertando registros...")
        chunk_size = 5000
        total = 0

        for i in range(0, len(valores), chunk_size):
            chunk = valores[i:i + chunk_size]
            cur.executemany(insert_sql, chunk)
            total += len(chunk)
            print(f"Insertados acumulados: {total}")

        conn.commit()

        despues = cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.aster_dia_nc
            WHERE CAST(Fecha_Hora AS DATE) = ?;
            """,
            fsql,
        ).fetchval()

        print(f"Registros destino después para {fsql}: {despues}")

    return total, despues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", help="Fecha YYYYMMDD o YYYY-MM-DD")
    parser.add_argument("--esperado", type=int, default=41240)
    parser.add_argument("--execute", action="store_true", help="Escribe Excel Gestión y carga SQL Server")
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)
    esperado = args.esperado

    base, normalizado, gestion_dir, gestion = rutas(fecha)

    title("PROMOVER ASTER NORMALIZADO A GESTION Y CARGAR SQL")
    print("Fecha:", fecha)
    print("Fecha SQL:", fecha_sql(fecha))
    print("Modo:", "EJECUCION REAL" if args.execute else "DRY RUN")
    print("Base:", base)
    print("Normalizado:", normalizado)
    print("Gestion final:", gestion)
    print("Esperado:", esperado)

    if not normalizado.exists():
        raise FileNotFoundError(f"No existe archivo normalizado: {normalizado}")

    df_origen = leer_excel(normalizado)

    print("\nFilas normalizado:", len(df_origen))
    print("Columnas normalizado:")
    for col in df_origen.columns:
        print("-", col)

    if len(df_origen) != esperado:
        raise RuntimeError(
            f"El normalizado tiene {len(df_origen)} filas, pero se esperaban {esperado}."
        )

    df = preparar_dataframe(df_origen)

    print("\nFilas preparadas:", len(df))
    print("Columnas preparadas:")
    for col in df.columns:
        print("-", col)

    print("\nMuestra preparada:")
    print(df.head(10).to_string(index=False))

    title("AUDITORIA SQL ANTES")
    auditar_sql(fecha)

    if not args.execute:
        title("DRY RUN FINALIZADO")
        print("No se escribió Excel y no se cargó SQL Server.")
        print("Si la muestra está correcta, ejecuta:")
        print(f"  python tools\\promote_aster_normalizado_to_gestion_and_load.py {fecha} --execute")
        return

    title("ESCRIBIENDO ARCHIVO GESTION")
    filas_excel = escribir_gestion_excel(df, gestion)

    if filas_excel != esperado:
        raise RuntimeError(
            f"El archivo Gestión quedó con {filas_excel} filas, esperado {esperado}."
        )

    title("CARGANDO SQL SERVER")
    insertados, total_final = cargar_sql(df, fecha)

    title("RESUMEN FINAL")
    print("Filas origen normalizado:", len(df_origen))
    print("Filas archivo Gestión:", filas_excel)
    print("Insertados reportados:", insertados)
    print("Total SQL final fecha:", total_final)

    if total_final != esperado:
        raise RuntimeError(
            f"ERROR: SQL final tiene {total_final}, esperado {esperado}."
        )

    print("OK: Excel Gestión y Aster_Api.dbo.aster_dia_nc quedaron con el total esperado.")


if __name__ == "__main__":
    main()