import sys
from pathlib import Path

import pandas as pd
import pyodbc


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import DATA_DIR, SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import construir_cadena_conexion


FECHA = "2026-05-12"
MESES = "202605"


def obtener_configuracion():
    conexion = "local"

    if len(sys.argv) >= 2:
        conexion = sys.argv[1].strip().lower()

    if conexion == "remoto":
        return "remoto", SQL_REMOTO

    return "local", SQL_LOCAL


def main():
    nombre_conexion, cfg = obtener_configuracion()

    sql_path = ROOT_DIR / "app" / "sql" / "consolidado.sql"

    print("====================================================")
    print("PRUEBA DE CONSULTA CONSOLIDADO")
    print("====================================================")
    print(f"Conexión: {nombre_conexion}")
    print(f"Servidor: {cfg['server']}")
    print(f"Base: {cfg['database']}")
    print(f"Fecha: {FECHA}")
    print(f"Meses: {MESES}")
    print(f"SQL: {sql_path}")
    print("====================================================")

    if not sql_path.exists():
        raise FileNotFoundError(f"No existe el archivo SQL: {sql_path}")

    sql_template = sql_path.read_text(encoding="utf-8")
    sql_final = sql_template.format(fecha=FECHA, meses=MESES)

    conn_str = construir_cadena_conexion(cfg)

    with pyodbc.connect(conn_str, timeout=60) as conn:
        df = pd.read_sql(sql_final, conn)

    print("====================================================")
    print("RESULTADO")
    print("====================================================")
    print(f"Filas devueltas: {len(df)}")
    print(f"Columnas devueltas: {len(df.columns)}")

    if df.empty:
        print("⚠️ La consulta no devolvió resultados.")
        print("Revisa fecha, datos de prueba y tabla de asesores.")
        return

    print()
    print("Columnas:")
    for col in df.columns:
        print(f" - {col}")

    print()
    print("Primeras filas:")
    print(df.head(10).to_string(index=False))

    columna_descripcion = "Descripcion Codigo De Gestion"
    if columna_descripcion in df.columns:
        valores = (
            df[columna_descripcion]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        print()
        print("Valores únicos de Descripcion Codigo De Gestion:")
        for valor in valores:
            print(f" - {valor}")

    columna_fecha_compromiso = "Fecha_Compromiso"
    if columna_fecha_compromiso in df.columns:
        total_con_fecha = df[
            df[columna_fecha_compromiso].notna()
            & (df[columna_fecha_compromiso].astype(str).str.strip() != "")
        ].shape[0]

        print()
        print(f"Filas con Fecha_Compromiso: {total_con_fecha}")

    salida = Path(DATA_DIR) / "consolidado_test_20260512.xlsx"
    df.to_excel(salida, index=False)

    print()
    print("====================================================")
    print("✅ CONSULTA CONSOLIDADO EJECUTADA")
    print("====================================================")
    print(f"Excel generado: {salida}")


if __name__ == "__main__":
    main()