from pathlib import Path
import re
from collections import Counter, defaultdict


RUTAS = [
    Path("app/templates"),
]

PATRON_STYLE = re.compile(r'style="([^"]*)"', re.IGNORECASE)


def main() -> None:
    hallazgos = []
    contador_estilos = Counter()
    archivos_por_estilo = defaultdict(list)

    for raiz in RUTAS:
        if not raiz.exists():
            continue

        for archivo in raiz.rglob("*.html"):
            texto = archivo.read_text(encoding="utf-8", errors="ignore")
            lineas = texto.splitlines()

            for num_linea, linea in enumerate(lineas, start=1):
                for match in PATRON_STYLE.finditer(linea):
                    estilo = match.group(1).strip()
                    contador_estilos[estilo] += 1
                    archivos_por_estilo[estilo].append(f"{archivo}:{num_linea}")
                    hallazgos.append(
                        {
                            "archivo": archivo,
                            "linea": num_linea,
                            "estilo": estilo,
                            "texto": linea.strip(),
                        }
                    )

    print("=" * 100)
    print("AUDITORÍA DE ESTILOS INLINE")
    print("=" * 100)

    if not hallazgos:
        print("✅ No se encontraron estilos inline en templates HTML.")
        return

    print(f"Total style= encontrados: {len(hallazgos)}")
    print(f"Estilos únicos: {len(contador_estilos)}")

    print("\n" + "=" * 100)
    print("ESTILOS REPETIDOS")
    print("=" * 100)

    repetidos = [
        (estilo, total)
        for estilo, total in contador_estilos.most_common()
        if total > 1
    ]

    if not repetidos:
        print("✅ No hay estilos inline repetidos.")
    else:
        for estilo, total in repetidos:
            print(f"\n[{total} veces] {estilo}")
            for ref in archivos_por_estilo[estilo][:10]:
                print(f"  - {ref}")

            if len(archivos_por_estilo[estilo]) > 10:
                print(f"  ... y {len(archivos_por_estilo[estilo]) - 10} más")

    print("\n" + "=" * 100)
    print("TODOS LOS HALLAZGOS")
    print("=" * 100)

    for item in hallazgos:
        print(f"{item['archivo']}:{item['linea']}")
        print(f"  style=\"{item['estilo']}\"")
        print()

    print("=" * 100)
    print("Recomendación:")
    print("- Repetidos: mover a clases CSS reutilizables.")
    print("- Únicos y muy específicos: pueden quedar temporalmente.")
    print("=" * 100)


if __name__ == "__main__":
    main()