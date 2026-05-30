from pathlib import Path
import argparse
import pandas as pd
import sys

ROOT = Path.cwd()


def normalizar_fecha(value: str) -> str:
    value = str(value or "").strip().replace("-", "")

    if len(value) != 8 or not value.isdigit():
        raise ValueError("Fecha inválida. Usa YYYYMMDD o YYYY-MM-DD.")

    return value


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def contar_excel(path: Path):
    try:
        excel = pd.ExcelFile(path)
        sheet = excel.sheet_names[0]
        df = pd.read_excel(path, sheet_name=sheet)

        df_real = df.dropna(how="all")

        return {
            "ok": True,
            "sheet": sheet,
            "rows": len(df_real),
            "cols": list(df.columns),
            "error": "",
        }

    except Exception as exc:
        return {
            "ok": False,
            "sheet": "",
            "rows": None,
            "cols": [],
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", help="Fecha YYYYMMDD o YYYY-MM-DD")
    parser.add_argument("--esperado", type=int, default=41240)
    args = parser.parse_args()

    fecha = normalizar_fecha(args.fecha)
    esperado = args.esperado

    base = ROOT / "data" / fecha / "Aster" / f"aster_{fecha}"
    gestion_dir = base / "Gestion"
    gestion_file = gestion_dir / f"{fecha}_Gestion_aster.xlsx"

    title("AUDITORIA EXCEL ASTER")
    print("Fecha:", fecha)
    print("Base:", base)
    print("Archivo gestión esperado:", gestion_file)
    print("Registros esperados:", esperado)

    if not base.exists():
        print("\nERROR: No existe carpeta base:", base)
        sys.exit(1)

    files = sorted(
        [
            p for p in base.rglob("*.xlsx")
            if not p.name.startswith("~$")
        ]
    )

    if not files:
        print("\nNo se encontraron archivos Excel.")
        return

    title("ARCHIVOS ENCONTRADOS")

    candidates = []

    for path in files:
        info = contar_excel(path)
        rel = path.relative_to(ROOT)

        if not info["ok"]:
            print(f"\n{rel}")
            print("ERROR:", info["error"])
            continue

        marker = ""

        if info["rows"] == esperado:
            marker = "<<< CANDIDATO 41240"

        if path.resolve() == gestion_file.resolve():
            marker += " <<< ARCHIVO GESTION FINAL"

        print(f"\n{rel}")
        print(f"Sheet: {info['sheet']}")
        print(f"Filas reales: {info['rows']} {marker}")
        print("Columnas:")
        for col in info["cols"]:
            print(f"  - {col}")

        if info["rows"] == esperado and path.resolve() != gestion_file.resolve():
            candidates.append(path)

    title("RESUMEN")

    if gestion_file.exists():
        info_final = contar_excel(gestion_file)
        print("Archivo final existe:", gestion_file)
        print("Filas archivo final:", info_final["rows"])
    else:
        print("Archivo final NO existe:", gestion_file)

    print("\nCandidatos con registros esperados:")
    if not candidates:
        print("No se encontró ningún Excel origen con", esperado, "filas.")
    else:
        for c in candidates:
            print("-", c.relative_to(ROOT))

    title("FIN")
    print("Si hay un candidato de 41.240, se usará para reconstruir el archivo Gestión ASTER.")


if __name__ == "__main__":
    main()