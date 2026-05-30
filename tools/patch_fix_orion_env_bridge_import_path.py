from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path.cwd()
SCRIPT = ROOT / "tools" / "fix_orion_local_sqlserver_env_bridge.py"

BACKUP = SCRIPT.with_suffix(
    SCRIPT.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError(f"No existe: {SCRIPT}")

    text = SCRIPT.read_text(encoding="utf-8", errors="ignore")

    if "sys.path.insert(0, str(ROOT))" in text:
        print("OK: el script ya tiene ROOT en sys.path.")
        return

    shutil.copy2(SCRIPT, BACKUP)
    print(f"Backup creado: {BACKUP}")

    marker = "ROOT = Path.cwd()"

    if marker not in text:
        raise RuntimeError("No encontré ROOT = Path.cwd() en el script.")

    text = text.replace(
        marker,
        marker + "\n\n# Permite importar app.config cuando el script se ejecuta desde tools/\nsys.path.insert(0, str(ROOT))",
        1
    )

    SCRIPT.write_text(text, encoding="utf-8")
    print("OK: script corregido para importar app.config.")


if __name__ == "__main__":
    main()