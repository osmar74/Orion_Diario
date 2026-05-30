from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

BACKUP_BASE = ROOT / ".git" / "orion_patch_backups"

TARGETS = [
    Path("app/services/aster_phase_i_execution_service.py"),
    Path("app/services/aster_phase_i_prepare_service.py"),
    Path("app/services/aster_source_service.py"),
]

SAFETY_BACKUP = BACKUP_BASE / ("manual_restore_safety_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def compile_file(path: Path):
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stderr


def backup_current_files():
    title("1. BACKUP DE SEGURIDAD DEL ESTADO ACTUAL")

    for rel in TARGETS:
        src = ROOT / rel

        if not src.exists():
            print(f"NO EXISTE: {rel}")
            continue

        dest = SAFETY_BACKUP / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"Backup actual: {rel} -> {dest}")


def find_candidate_dirs():
    if not BACKUP_BASE.exists():
        raise FileNotFoundError(f"No existe carpeta de backups: {BACKUP_BASE}")

    dirs = [p for p in BACKUP_BASE.iterdir() if p.is_dir()]
    dirs.sort(reverse=True, key=lambda p: p.name)

    candidates = []

    for d in dirs:
        ok = True

        for rel in TARGETS:
            if not (d / rel).exists():
                ok = False
                break

        if ok:
            candidates.append(d)

    return candidates


def choose_valid_backup():
    title("2. BUSCANDO BACKUP VALIDO")

    candidates = find_candidate_dirs()

    if not candidates:
        raise RuntimeError("No encontré backup que contenga los 3 servicios ASTER Fase I.")

    for d in candidates:
        print(f"\nProbando backup: {d}")

        all_ok = True

        for rel in TARGETS:
            candidate_file = d / rel
            ok, err = compile_file(candidate_file)

            if ok:
                print(f"  OK compile: {rel}")
            else:
                print(f"  FAIL compile: {rel}")
                print(err)
                all_ok = False
                break

        if all_ok:
            print(f"\nBackup seleccionado: {d}")
            return d

    raise RuntimeError("Encontré backups, pero ninguno compila correctamente.")


def restore_backup(backup_dir: Path):
    title("3. RESTAURANDO SERVICIOS ASTER FASE I")

    for rel in TARGETS:
        src = backup_dir / rel
        dest = ROOT / rel

        shutil.copy2(src, dest)
        print(f"Restaurado: {rel}")


def compile_restored():
    title("4. COMPILACION DESPUES DE RESTAURAR")

    subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(ROOT / rel) for rel in TARGETS]],
        check=True,
    )

    print("OK: servicios restaurados compilan.")


def main():
    title("RESTAURAR ASTER FASE I DESDE BACKUP VALIDO")

    backup_current_files()
    backup_dir = choose_valid_backup()
    restore_backup(backup_dir)
    compile_restored()

    title("FINALIZADO")
    print("Ahora ejecuta:")
    print("  python tools\\fix_aster_phase_i_required_id_safe_v2.py")


if __name__ == "__main__":
    main()