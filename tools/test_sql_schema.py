import sys
from pathlib import Path

import pyodbc


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import SQL_LOCAL, SQL_REMOTO
from app.controllers.helpers import construir_cadena_conexion


TABLAS_REQUERIDAS = {
    "Causales": [
        "FechayHora",
        "Tipo_de_evento",
        "NroDeAgente",
        "Telefono_utilizado",
        "Campana",
        "Subcategoria",
        "Codigo",
        "Categoria",
        "Fecha_de_compromiso",
        "Usuario",
        "Comentario",
        "Causal_de_mora",
    ],
    "Lote": [
        "Fecha",
        "phone_number",
        "Nombre_Lote",
        "codigo_cliente",
        "segmento",
    ],
    "Discador": [
        "NroCliente_Contrato",
        "FechayHora",
        "DuracionTotal",
        "Categoria",
        "Subcategoria",
        "Resultado",
        "NumeroTelefonico",
        "Lote",
        "Campana",
        "Agente",
        "EstadoActualContacto",
    ],
}


TABLA_ASESORES = {
    "database": "Vencorp_V2",
    "schema": "gestion",
    "table": "gestion_adminfo_onedrive",
    "columns": [
        "Grabador",
        "Asesor",
        "Mes_Gestion",
    ],
}


def obtener_columnas_tabla(cursor, tabla, esquema="dbo", database=None):
    if database:
        consulta = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM [{database}].INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
    else:
        consulta = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """

    cursor.execute(consulta, esquema, tabla)
    filas = cursor.fetchall()

    return {
        row.COLUMN_NAME: row.DATA_TYPE
        for row in filas
    }


def contar_registros(cursor, tabla, esquema="dbo", database=None):
    if database:
        consulta = f"SELECT COUNT(*) FROM [{database}].[{esquema}].[{tabla}]"
    else:
        consulta = f"SELECT COUNT(*) FROM [{esquema}].[{tabla}]"

    cursor.execute(consulta)
    return cursor.fetchone()[0]


def validar_tabla(cursor, tabla, columnas_requeridas, esquema="dbo", database=None):
    columnas_sql = obtener_columnas_tabla(
        cursor=cursor,
        tabla=tabla,
        esquema=esquema,
        database=database,
    )

    nombre_completo = (
        f"{database}.{esquema}.{tabla}"
        if database
        else f"{esquema}.{tabla}"
    )

    print("----------------------------------------------------")
    print(f"Tabla: {nombre_completo}")
    print("----------------------------------------------------")

    if not columnas_sql:
        print("❌ NO EXISTE TABLA O NO TIENE COLUMNAS")
        return False

    columnas_existentes_norm = {col.lower(): col for col in columnas_sql}
    faltantes = []

    for columna in columnas_requeridas:
        if columna.lower() not in columnas_existentes_norm:
            faltantes.append(columna)

    print(f"Columnas encontradas: {len(columnas_sql)}")

    try:
        total = contar_registros(
            cursor=cursor,
            tabla=tabla,
            esquema=esquema,
            database=database,
        )
        print(f"Registros actuales: {total}")
    except Exception as exc:
        print(f"⚠️ No se pudo contar registros: {exc}")

    if faltantes:
        print("❌ FALTAN COLUMNAS:")
        for columna in faltantes:
            print(f"   - {columna}")
        return False

    print("✅ ESTRUCTURA OK")
    return True


def validar_base(nombre_conexion, config):
    print("====================================================")
    print(f"VALIDANDO ESQUEMA SQL: {nombre_conexion}")
    print(f"Servidor: {config['server']}")
    print(f"Base: {config['database']}")
    print("====================================================")

    try:
        conn_str = construir_cadena_conexion(config)

        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    @@SERVERNAME AS servidor,
                    DB_NAME() AS base_actual,
                    SUSER_SNAME() AS usuario
                """
            )
            row = cursor.fetchone()

            print(f"Servidor SQL: {row.servidor}")
            print(f"Base actual: {row.base_actual}")
            print(f"Usuario: {row.usuario}")
            print()

            resultados = []

            for tabla, columnas in TABLAS_REQUERIDAS.items():
                ok = validar_tabla(
                    cursor=cursor,
                    tabla=tabla,
                    columnas_requeridas=columnas,
                    esquema="dbo",
                    database=None,
                )
                resultados.append(ok)

            print()
            print("Validando tabla externa de asesores...")
            ok_asesores = validar_tabla(
                cursor=cursor,
                tabla=TABLA_ASESORES["table"],
                columnas_requeridas=TABLA_ASESORES["columns"],
                esquema=TABLA_ASESORES["schema"],
                database=TABLA_ASESORES["database"],
            )
            resultados.append(ok_asesores)

            print()
            print("====================================================")
            print(f"RESUMEN {nombre_conexion}")
            print("====================================================")
            print(f"Resultado general: {'OK' if all(resultados) else 'REVISAR'}")
            print()

            return all(resultados)

    except Exception as exc:
        print("❌ ERROR GENERAL DE VALIDACIÓN")
        print(str(exc))
        print()
        return False


def main():
    local_ok = validar_base("SQL_LOCAL", SQL_LOCAL)
    remoto_ok = validar_base("SQL_REMOTO", SQL_REMOTO)

    print("====================================================")
    print("RESUMEN FINAL")
    print("====================================================")
    print(f"SQL_LOCAL: {'OK' if local_ok else 'REVISAR'}")
    print(f"SQL_REMOTO: {'OK' if remoto_ok else 'REVISAR'}")

    if not local_ok or not remoto_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()