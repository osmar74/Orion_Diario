from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

FILES = [
    ROOT / "app" / "services" / "aster_phase_i_execution_service.py",
    ROOT / "app" / "services" / "aster_phase_i_prepare_service.py",
    ROOT / "app" / "services" / "aster_source_service.py",
]

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

BAD_BLOCKS = [
    (
        "# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_BEGIN ===",
        "# === FIX_ASTER_PHASE_I_REQUIRED_ID_DEEP_END ===",
    ),
]


def title(value):
    print("\n" + "=" * 100)
    print(value)
    print("=" * 100)


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path, text):
    path.write_text(text, encoding="utf-8")


def backup(path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def remove_block(text, begin, end):
    count = 0

    while begin in text:
        before = text.split(begin, 1)[0].rstrip()
        rest = text.split(begin, 1)[1]

        if end in rest:
            after = rest.split(end, 1)[1].lstrip()
            text = before + "\n\n" + after
            count += 1
        else:
            text = before + "\n"
            count += 1

    return text, count


def main():
    title("REPAIR - QUITAR FIX PROFUNDO MAL INSERTADO")

    changed = []

    for path in FILES:
        if not path.exists():
            continue

        original = read(path)
        text = original
        total_removed = 0

        for begin, end in BAD_BLOCKS:
            text, count = remove_block(text, begin, end)
            total_removed += count

        if text != original:
            backup(path)
            write(path, text)
            changed.append(path)
            print(f"OK: removidos {total_removed} bloques en {path.relative_to(ROOT)}")
        else:
            print(f"Sin cambios: {path.relative_to(ROOT)}")

    title("COMPILACION")

    subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in FILES if p.exists()]],
        check=True,
    )

    print("OK: los servicios ASTER vuelven a compilar.")

    title("FINALIZADO")
    print("Ahora ejecuta el fix final seguro:")
    print("  python tools\\fix_aster_phase_i_required_id_safe.py")


if __name__ == "__main__":
    main()