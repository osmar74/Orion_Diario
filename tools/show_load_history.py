import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.services.load_registry import LOAD_REGISTRY_DB, inicializar_load_registry


def obtener_filtro_conexion():
    if len(sys.argv) >= 2:
        conexion = sys.argv[1].strip().lower()

        if conexion in ("local", "remoto"):
            return conexion

    return None


def imprimir_fila(row):
    print("----------------------------------------------------")
    print(f"ID: {row['id']}")
    print(f"Tipo: {row['tipo']}")
    print(f"Conexión: {row['conexion']}")
    print(f"Tabla destino: {row['tabla_destino']}")
    print(f"Archivo: {row['nombre_archivo']}")
    print(f"Ruta: {row['ruta_archivo']}")
    print(f"Hash: {row['archivo_hash']}")
    print(f"Registros archivo: {row['registros_archivo']}")
    print(f"Registros insertados: {row['registros_insertados']}")
    print(f"Fecha carga: {row['fecha_carga']}")


def main():
    print("====================================================")
    print("HISTORIAL DE CARGAS - ORION DIARIO")
    print("====================================================")
    print(f"Base local: {LOAD_REGISTRY_DB}")

    inicializar_load_registry()

    filtro_conexion = obtener_filtro_conexion()

    with sqlite3.connect(LOAD_REGISTRY_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if filtro_conexion:
            cursor.execute(
                """
                SELECT
                    id,
                    tipo,
                    conexion,
                    tabla_destino,
                    nombre_archivo,
                    ruta_archivo,
                    archivo_hash,
                    registros_archivo,
                    registros_insertados,
                    fecha_carga
                FROM load_history
                WHERE conexion = ?
                ORDER BY id DESC
                """,
                (filtro_conexion,),
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    tipo,
                    conexion,
                    tabla_destino,
                    nombre_archivo,
                    ruta_archivo,
                    archivo_hash,
                    registros_archivo,
                    registros_insertados,
                    fecha_carga
                FROM load_history
                ORDER BY id DESC
                """
            )

        rows = cursor.fetchall()

    print(f"Filtro conexión: {filtro_conexion or 'todos'}")
    print(f"Total registros: {len(rows)}")

    if not rows:
        print()
        print("⚠️ No hay cargas registradas todavía.")
        return

    for row in rows:
        imprimir_fila(row)

    print("----------------------------------------------------")
    print("✅ HISTORIAL CONSULTADO CORRECTAMENTE")


if __name__ == "__main__":
    main()