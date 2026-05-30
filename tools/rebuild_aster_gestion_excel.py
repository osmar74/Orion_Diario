from pathlib import Path
from datetime import datetime
import argparse
import shutil
import pandas as pd
import re
import sys

ROOT = Path.cwd()

DESTINO_COLUMNAS = [
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


ALIASES = {
    "ID": ["id", "ID", "Id"],
    "Fecha_Hora": ["Fecha_Hora", "Fecha Hora", "fecha_hora", "fecha", "Fecha", "FECHA"],
    "Numero": ["Numero", "Número", "numero", "telefono", "Teléfono", "data", "Data"],
    "Intentos": ["Intentos", "intentos"],
    "Estado": ["Estado", "estado", "resultado1", "Resultado1"],
    "Atendio": ["Atendio", "Atendió", "atendio", "resultado2", "Resultado2"],
    "Duracion": ["Duracion", "Duración", "duracion"],
    "Atendido_por": ["Atendido_por", "Atendido Por", "atendido_por", "usuario", "Usuario"],
    "507": ["507"],
    "Relacion": ["Relacion", "Relación", "relacion"],
    "Codigo": ["Codigo", "Código", "codigo", "data", "Data"],
    "Entidad": ["Entidad", "entidad"],
    "Cartera": ["Cartera", "cartera", "Relacion", "Relación", "relacion", "Entidad", "entidad"],
}


def normalizar_fecha(value: str) -> str:
    value = str(value or "").strip().replace("-", "")

    if len(value) != 8 or not value.isdigit():
        raise ValueError("Fecha inválida. Usa YYYYMMDD o YYYY-MM-DD.")

    return value


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def normalizar_nombre_columna(value):
    value = str(value or "").strip()
    value = value.lower()
    value = value.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    value = value.replace("ñ", "n")
    value = re.sub(r"\s+", "_", value)
    return value


def buscar_columna(df, destino):
    columnas_normalizadas = {
        normalizar_nombre_columna(col): col
        for col in df.columns
    }

    for alias in ALIASES[destino]:
        alias_norm = normalizar_nombre_columna(alias)

        if alias_norm in columnas_normalizadas:
            return columnas_normalizadas[alias_norm]

    return None


def leer_excel(path: Path):
    df = pd.read_excel(path)
    df = df.dropna(how="all")
    return df


def encontrar_candidato(fecha, esperado):
    base = ROOT / "data" / fecha / "Aster" / f"aster_{fecha}"
    gestion_file = base / "Gestion" / f"{fecha}_Gestion_aster.xlsx"

    candidatos = []

    for path in sorted(base.rglob("*.xlsx")):
        if path.name.startswith("~$"):
            continue

        if path.resolve() == gestion_file.resolve():
            continue

        try:
            df = leer_excel(path)
        except Exception:
            continue

        if len(df) == esperado:
            candidatos.append(path)

    if not candidatos:
        return None

    return candidatos[0]


def transformar(df, fecha):
    salida = pd.DataFrame()

    for destino in DESTINO_COLUMNAS:
        origen = buscar_columna(df, destino)

        if origen is not None:
            salida[destino] = df[origen]
        else:
            if destino == "ID":
                salida[destino] = range(1, len(df) + 1)

            elif destino == "Fecha_Hora":
                salida[destino] = pd.to_datetime(f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}")

            elif destino == "Intentos":
                salida[destino] = "1"

            elif destino == "Duracion":
                salida[destino] = "0"

            elif destino == "507":
                salida[destino] = "507"

            elif destino == "Relacion":
                salida[destino] = ""

            else:
                salida[destino] = ""

    salida["Fecha_Hora"] = pd.to_datetime(salida["Fecha_Hora"], errors="coerce")

    # Ajustar largos según SQL Server.
    limites = {
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

    for col, max_len in limites.items():
        salida[col] = salida[col].fillna("").astype(str).str.slice(0, max_len)

    return salida


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", help="Fecha YYYYMMDD o YYYY-MM-DD")
    parser.add_argument("--source", help="Excel origen exacto. Si no se envía, busca uno con 41.240 filas.")
    parser.add_argument("--esperado", type=int, default=41240)
    parser.add_argument("--execute", action="store_true", help="Escribe el archivo final.")
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)
    esperado = args.esperado

    base = ROOT / "data" / fecha / "Aster" / f"aster_{fecha}"
    gestion_dir = base / "Gestion"
    output = gestion_dir / f"{fecha}_Gestion_aster.xlsx"

    title("REBUILD GESTION ASTER EXCEL")
    print("Fecha:", fecha)
    print("Esperado:", esperado)
    print("Output:", output)
    print("Modo:", "EJECUCION REAL" if args.execute else "DRY RUN")

    if args.source:
        source = Path(args.source)
    else:
        source = encontrar_candidato(fecha, esperado)

    if not source or not source.exists():
        print("\nERROR: No se encontró Excel origen con", esperado, "filas.")
        print("Ejecuta primero:")
        print(f"  python tools\\audit_aster_excels_fecha.py {fecha}")
        sys.exit(1)

    print("\nExcel origen:", source)

    df = leer_excel(source)
    print("Filas origen:", len(df))
    print("Columnas origen:")
    for col in df.columns:
        print("-", col)

    if len(df) != esperado:
        raise RuntimeError(f"El origen tiene {len(df)} filas, pero se esperaban {esperado}.")

    salida = transformar(df, fecha)

    print("\nFilas salida:", len(salida))
    print("Columnas salida:")
    for col in salida.columns:
        print("-", col)

    print("\nMuestra salida:")
    print(salida.head(10).to_string(index=False))

    if not args.execute:
        title("DRY RUN FINALIZADO")
        print("No se escribió el archivo.")
        print("Si la muestra está bien, ejecuta:")
        print(f"  python tools\\rebuild_aster_gestion_excel.py {fecha} --execute")
        return

    gestion_dir.mkdir(parents=True, exist_ok=True)

    if output.exists():
        backup = output.with_suffix(
            output.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy2(output, backup)
        print("\nBackup archivo anterior:", backup)

    salida.to_excel(output, index=False)

    df_validacion = leer_excel(output)

    print("\nArchivo escrito:", output)
    print("Filas validación:", len(df_validacion))

    if len(df_validacion) != esperado:
        raise RuntimeError(
            f"ERROR: el archivo final quedó con {len(df_validacion)} filas, esperado {esperado}."
        )

    title("OK")
    print(f"Archivo {output.name} reconstruido con {len(df_validacion)} registros.")


if __name__ == "__main__":
    main()