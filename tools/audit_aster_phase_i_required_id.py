from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()
APP_DIR = ROOT / "app"

PATTERNS = [
    "Faltan columnas requeridas",
    "columnas requeridas",
    "faltantes",
    "faltan",
    "usuarios",
    "required",
    "missing",
    "id",
]


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def print_context(path, line_no, lines, radius=8):
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)

    print(f"\n--- {path.relative_to(ROOT)} | contexto línea {line_no} ---")

    for n in range(start, end + 1):
        marker = ">>" if n == line_no else "  "
        print(f"{marker} {n:04d}: {lines[n - 1][:260]}")


def search_exact_error():
    title("1. BUSQUEDA EXACTA DEL MENSAJE")

    exact_terms = [
        "Faltan columnas requeridas para usuarios",
        "Faltan columnas requeridas",
        "columnas requeridas para usuarios",
    ]

    found = False

    for path in APP_DIR.rglob("*.py"):
        text = read(path)
        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            if any(term in line for term in exact_terms):
                found = True
                print_context(path, i, lines, radius=12)

    if not found:
        print("No se encontró el texto exacto en app/*.py")

    return found


def search_related_logic():
    title("2. BUSQUEDA AMPLIA DE VALIDACION usuarios / id / faltantes")

    candidate_files = []

    for path in APP_DIR.rglob("*.py"):
        text = read(path)
        lower = text.lower()

        score = 0

        if "usuarios" in lower:
            score += 1
        if "faltantes" in lower:
            score += 3
        if "columnas" in lower and "requer" in lower:
            score += 4
        if '"id"' in text or "'id'" in text:
            score += 2
        if "fase_i" in lower or "fase i" in lower:
            score += 2
        if "aster" in str(path).lower():
            score += 1

        if score >= 5:
            candidate_files.append((score, path))

    candidate_files.sort(reverse=True, key=lambda x: x[0])

    for score, path in candidate_files:
        print(f"\n### {path.relative_to(ROOT)} | score={score}")

        lines = read(path).splitlines()

        for i, line in enumerate(lines, start=1):
            lower = line.lower()

            hit = False

            if "faltantes" in lower:
                hit = True
            if "columnas" in lower and "requer" in lower:
                hit = True
            if ("'id'" in line or '"id"' in line) and "usuario" in lower:
                hit = True
            if "usuarios" in lower and "id" in lower and ("requer" in lower or "falt" in lower):
                hit = True

            if hit:
                print(f"{i:04d}: {line[:260]}")


def search_routes():
    title("3. RUTAS FASE I ASTER")

    for path in APP_DIR.rglob("*.py"):
        text = read(path)

        if "aster-fase-i" not in text and "fase-i" not in text and "fase_i" not in text:
            continue

        print(f"\n--- {path.relative_to(ROOT)} ---")

        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            lower = line.lower()

            if (
                "aster-fase-i" in lower
                or "fase_i" in lower
                or "fase i" in lower
                or "ejecutar_fase_i_aster" in lower
            ):
                print(f"{i:04d}: {line[:260]}")


def compile_check():
    title("4. COMPILACION ACTUAL")

    files = [str(p) for p in APP_DIR.rglob("*.py")]

    result = subprocess.run(
        [sys.executable, "-m", "py_compile", *files],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("OK: todo app/ compila.")
    else:
        print("ERROR: app/ no compila.")
        print(result.stderr)


def main():
    title("AUDITORIA ASTER FASE I - ERROR id USUARIOS")

    compile_check()
    search_exact_error()
    search_related_logic()
    search_routes()

    title("FIN")
    print("Copia y pégame la salida completa, especialmente las secciones 1 y 2.")


if __name__ == "__main__":
    main()