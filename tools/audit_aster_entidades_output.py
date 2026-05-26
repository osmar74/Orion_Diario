from pathlib import Path
import sys
import re


ROOT = Path(".")
DATA_DIR = ROOT / "data"

fecha = sys.argv[1] if len(sys.argv) > 1 else ""

if not fecha:
    print("Uso: python tools\\audit_aster_entidades_output.py 20260429")
    raise SystemExit(1)

fecha_limpia = fecha.replace("_", "").replace("-", "")

if not re.fullmatch(r"\d{8}", fecha_limpia):
    print(f"Fecha inválida: {fecha}")
    raise SystemExit(1)

base_aster = DATA_DIR / fecha_limpia / "Aster" / f"aster_{fecha_limpia}"
esperado = base_aster / "Entidades" / f"entidades_aster_{fecha_limpia}.xlsx"

print("=" * 100)
print("AUDITORÍA ASTER - ARCHIVO ENTIDADES")
print("=" * 100)
print(f"Fecha: {fecha_limpia}")
print(f"Ruta base ASTER: {base_aster}")
print(f"Archivo esperado Fase I: {esperado}")
print()

print("[1] Existe ruta base ASTER")
print("✅ OK" if base_aster.exists() else "❌ NO EXISTE")
print()

print("[2] Existe archivo esperado")
print("✅ OK" if esperado.exists() else "❌ NO EXISTE")
print()

print("[3] Archivos encontrados relacionados con entidades")
candidatos = []

if base_aster.exists():
    patrones = [
        "*entidad*.xlsx",
        "*entidades*.xlsx",
        "*Entidad*.xlsx",
        "*Entidades*.xlsx",
        "*concili*.xlsx",
        "*validacion*.xlsx",
    ]

    for patron in patrones:
        candidatos.extend(base_aster.rglob(patron))

candidatos = sorted(set(candidatos))

if candidatos:
    for item in candidatos:
        print(f"✅ {item}")
else:
    print("❌ No se encontraron archivos relacionados con entidades dentro de ASTER.")
print()

print("[4] Carpetas dentro de ASTER")
if base_aster.exists():
    for item in sorted(base_aster.iterdir()):
        if item.is_dir():
            print(f"📁 {item}")
else:
    print("❌ No aplica, no existe ruta base.")
print()

print("[5] Referencias en código")
archivos_codigo = list((ROOT / "app").rglob("*.py")) + list((ROOT / "app").rglob("*.js"))

busquedas = [
    "entidades_aster",
    "No existe el archivo de entidades ASTER",
    "Entidades",
    "analizarEntidadesAster",
    "conciliarEntidadesAster",
]

for busqueda in busquedas:
    print(f"\n--- Buscando: {busqueda}")
    encontrados = 0

    for archivo in archivos_codigo:
        try:
            texto = archivo.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(texto.splitlines(), start=1):
            if busqueda.lower() in line.lower():
                print(f"{archivo}:{i}: {line.strip()}")
                encontrados += 1

    if not encontrados:
        print("Sin coincidencias.")

print()
print("=" * 100)
print("Fin auditoría.")
print("=" * 100)