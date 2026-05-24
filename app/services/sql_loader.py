"""
Loader centralizado de archivos SQL.

Responsabilidad:
- Leer archivos .sql desde app/sql.
- Evitar rutas inseguras fuera de app/sql.
"""

from __future__ import annotations

from pathlib import Path


SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def cargar_sql(ruta_relativa: str) -> str:
    """
    Carga un archivo SQL desde app/sql.

    Ejemplo:
        cargar_sql("orion/consolidado.sql")
        cargar_sql("orion/columnas_tabla.sql")
    """
    ruta = (SQL_DIR / ruta_relativa).resolve()

    if SQL_DIR.resolve() not in ruta.parents:
        raise ValueError(f"Ruta SQL no permitida: {ruta_relativa}")

    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo SQL: {ruta}")

    return ruta.read_text(encoding="utf-8")
