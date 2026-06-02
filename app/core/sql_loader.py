from __future__ import annotations

from pathlib import Path


class SqlLoader:
    """
    Carga instrucciones SQL desde app/sql.
    Evita SQL duro dentro de controllers, services o repositories.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent / "sql"

    @classmethod
    def load(cls, relative_path: str) -> str:
        sql_path = (cls.BASE_DIR / relative_path).resolve()
        base_path = cls.BASE_DIR.resolve()

        if base_path not in sql_path.parents:
            raise ValueError(f"Ruta SQL no permitida: {relative_path}")

        if not sql_path.exists():
            raise FileNotFoundError(f"No existe el archivo SQL: {sql_path}")

        return sql_path.read_text(encoding="utf-8")
