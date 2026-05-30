from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

TARGET = ROOT / "app" / "services" / "aster_phase_i_execution_service.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path, text):
    path.write_text(text, encoding="utf-8")


def backup(path):
    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def audit_before(text):
    title("1. AUDITORIA ANTES DEL FIX")

    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if "validar_columnas_minimas_fase_i" in line:
            print(f"{i:04d}: {line}")

    print("\nBuscando listas ['id', 'usuario']:")

    for i, line in enumerate(lines, start=1):
        if '"id"' in line and '"usuario"' in line:
            print(f"{i:04d}: {line}")
        elif "'id'" in line and "'usuario'" in line:
            print(f"{i:04d}: {line}")


def patch_direct(text):
    original = text

    # Caso multilínea típico:
    # error_usuarios = validar_columnas_minimas_fase_i(
    #     columnas_insert_usuarios,
    #     ["id", "usuario"],
    #     "usuarios",
    # )
    text = re.sub(
        r'(?P<prefix>error_usuarios\s*=\s*validar_columnas_minimas_fase_i\(\s*\n\s*columnas_insert_usuarios\s*,\s*\n\s*)\[\s*["\']id["\']\s*,\s*["\']usuario["\']\s*\]',
        r'\g<prefix>["usuario"]',
        text,
        flags=re.S,
    )

    # Caso una línea o variante cercana.
    text = re.sub(
        r'(error_usuarios\s*=\s*validar_columnas_minimas_fase_i\([^)]*)\[\s*["\']id["\']\s*,\s*["\']usuario["\']\s*\]',
        r'\1["usuario"]',
        text,
        flags=re.S,
    )

    # Reemplazo seguro adicional dentro de una ventana cercana a error_usuarios.
    if text == original:
        lines = text.splitlines()
        changed = False

        for i, line in enumerate(lines):
            if "error_usuarios" not in line or "validar_columnas_minimas_fase_i" not in line:
                continue

            for j in range(i, min(i + 8, len(lines))):
                if '["id", "usuario"]' in lines[j]:
                    lines[j] = lines[j].replace('["id", "usuario"]', '["usuario"]')
                    changed = True
                if "['id', 'usuario']" in lines[j]:
                    lines[j] = lines[j].replace("['id', 'usuario']", "['usuario']")
                    changed = True

        if changed:
            text = "\n".join(lines).rstrip() + "\n"

    return text, text != original


def audit_after(text):
    title("2. AUDITORIA DESPUES DEL FIX")

    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if "error_usuarios" in line or "validar_columnas_minimas_fase_i" in line:
            start = max(1, i - 2)
            end = min(len(lines), i + 6)

            print(f"\nContexto línea {i}:")
            for n in range(start, end + 1):
                print(f"{n:04d}: {lines[n - 1]}")

    print("\nListas ['id', 'usuario'] restantes:")

    found = False

    for i, line in enumerate(lines, start=1):
        if '["id", "usuario"]' in line or "['id', 'usuario']" in line:
            found = True
            print(f"{i:04d}: {line}")

    if not found:
        print("OK: no queda ['id', 'usuario'] como requeridas de usuarios.")


def main():
    title("FIX DIRECTO ASTER FASE I - USUARIOS NO REQUIERE id")

    if not TARGET.exists():
        raise FileNotFoundError(f"No existe: {TARGET}")

    title("0. COMPILACION PREVIA")
    subprocess.run([sys.executable, "-m", "py_compile", str(TARGET)], check=True)
    print("OK: archivo compila antes del fix.")

    original = read(TARGET)

    audit_before(original)

    patched, changed = patch_direct(original)

    if not changed:
        print("\nERROR: No se pudo aplicar el reemplazo automático.")
        print("Pega el contexto de error_usuarios para ajustar el patrón.")
        return

    backup(TARGET)
    write(TARGET, patched)

    audit_after(patched)

    title("3. COMPILACION POSTERIOR")
    subprocess.run([sys.executable, "-m", "py_compile", str(TARGET)], check=True)
    print("OK: archivo compila después del fix.")

    title("4. VALIDACION IMPORT")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster; print('OK ejecutar_fase_i_aster importado')",
        ],
        check=True,
    )

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba:")
    print("  Gestión Diaria ASTER -> Fase I -> Ejecutar Fase I completa")


if __name__ == "__main__":
    main()