from pathlib import Path
from datetime import datetime


DOCS = Path("docs")
DOCS.mkdir(exist_ok=True)

fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

estado = """# Estado estable ORION / ASTER Workflow v1

Fecha de documentación: {fecha}

## Rama estable

```text
orion-workflow-engine-v1