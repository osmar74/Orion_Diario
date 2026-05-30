from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

EXECUTION_SERVICE = ROOT / "app" / "services" / "aster_phase_i_execution_service.py"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

ERROR_TEXT = "Faltan columnas requeridas para usuarios"


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


def audit_context(text):
    title("1. AUDITORIA CONTEXTO DEL ERROR")

    lines = text.splitlines()
    found = False

    for i, line in enumerate(lines):
        if ERROR_TEXT in line or ("faltan columnas" in line.lower() and "usuarios" in line.lower()):
            found = True
            start = max(0, i - 15)
            end = min(len(lines), i + 8)

            print(f"\nContexto cerca de línea {i + 1}:")
            for n in range(start, end):
                print(f"{n + 1:04d}: {lines[n]}")

    if not found:
        print("No se encontró el texto exacto del error en execution_service.")
        print("Si el error sigue, está en otro archivo.")

    return found


def patch_error_block(text):
    lines = text.splitlines()
    inserts = []

    for i, line in enumerate(lines):
        if ERROR_TEXT not in line and not ("faltan columnas" in line.lower() and "usuarios" in line.lower()):
            continue

        # Buscar hacia arriba la variable faltantes más cercana:
        # if faltantes_usuarios:
        # if faltantes:
        for j in range(i, max(-1, i - 25), -1):
            m = re.match(r'^(\s*)if\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$', lines[j])

            if not m:
                continue

            indent = m.group(1)
            var_name = m.group(2)

            if "falt" not in var_name.lower() and "missing" not in var_name.lower():
                continue

            previous = "\n".join(lines[max(0, j - 5):j + 1])

            if "col for col in" in previous and '"id"' in previous:
                break

            # Insertar antes del if:
            # faltantes = [col for col in faltantes if col != "id"]
            inserts.append(
                (
                    j,
                    f'{indent}{var_name} = [col for col in {var_name} if str(col).strip().lower() != "id"]'
                )
            )
            break

    if not inserts:
        return text, False

    for index, new_line in reversed(inserts):
        lines.insert(index, new_line)

    return "\n".join(lines).rstrip() + "\n", True


def patch_required_lists(text):
    """
    Quita 'id' de listas evidentes de columnas requeridas para usuarios.
    """

    def repl(match):
        prefix = match.group("prefix")
        body = match.group("body")

        items = re.findall(r'["\']([^"\']+)["\']', body)

        if not items:
            return match.group(0)

        lower = [x.lower() for x in items]

        if "id" not in lower:
            return match.group(0)

        if "usuario" not in lower and "usuarios" not in prefix.lower():
            return match.group(0)

        cleaned = []

        for item in items:
            if item.strip().lower() == "id":
                continue

            if item not in cleaned:
                cleaned.append(item)

        if "usuario" not in [x.lower() for x in cleaned]:
            cleaned.insert(0, "usuario")

        return f'{prefix}[{", ".join(repr(x) for x in cleaned)}]'

    patterns = [
        r'(?P<prefix>\bcolumnas_requeridas_usuarios\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\bcolumnas_usuarios_requeridas\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\brequeridas_usuarios\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\busuarios_requeridas\s*=\s*)\[(?P<body>[^\]]+)\]',
        r'(?P<prefix>\brequired_user_columns\s*=\s*)\[(?P<body>[^\]]+)\]',
    ]

    changed = False

    for pattern in patterns:
        new_text = re.sub(pattern, repl, text, flags=re.I | re.S)

        if new_text != text:
            changed = True
            text = new_text

    return text, changed


def main():
    title("FIX SAFE V2 - ASTER FASE I id NO REQUERIDO EN USUARIOS")

    if not EXECUTION_SERVICE.exists():
        raise FileNotFoundError(f"No existe: {EXECUTION_SERVICE}")

    title("0. COMPILACION PREVIA")
    subprocess.run([sys.executable, "-m", "py_compile", str(EXECUTION_SERVICE)], check=True)
    print("OK: execution_service compila antes del fix.")

    original = read(EXECUTION_SERVICE)
    text = original

    audit_context(text)

    text, changed_lists = patch_required_lists(text)
    text, changed_guard = patch_error_block(text)

    if text != original:
        backup(EXECUTION_SERVICE)
        write(EXECUTION_SERVICE, text)
        print("\nOK: execution_service modificado.")
        print(f"- Listas corregidas: {changed_lists}")
        print(f"- Guardia antes del error: {changed_guard}")
    else:
        print("\nNo se modificó execution_service.")
        print("Necesitamos revisar el contexto exacto mostrado arriba.")

    title("2. COMPILACION POSTERIOR")
    subprocess.run([sys.executable, "-m", "py_compile", str(EXECUTION_SERVICE)], check=True)
    print("OK: execution_service compila después del fix.")

    title("3. VALIDACION IMPORT")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.services.aster_phase_i_execution_service import ejecutar_fase_i_aster; print('OK ejecutar_fase_i_aster importado')",
        ],
        check=True,
    )

    title("4. AUDITORIA FINAL")
    final_text = read(EXECUTION_SERVICE)

    for i, line in enumerate(final_text.splitlines(), start=1):
        if (
            ERROR_TEXT in line
            or 'str(col).strip().lower() != "id"' in line
            or "columnas_requeridas_usuarios" in line
            or "requeridas_usuarios" in line
        ):
            print(f"{i:04d}: {line[:240]}")

    title("FINALIZADO")
    print("Reinicia Flask:")
    print("  Ctrl + C")
    print("  python run.py")
    print("")
    print("Luego prueba Fase I completa.")


if __name__ == "__main__":
    main()