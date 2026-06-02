from pathlib import Path


class SqlLoader:
    """
    Carga instrucciones SQL desde archivos dentro de app/sql.
    Evita tener SQL duro dentro de services, repositories o controllers.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent / "sql"

    @classmethod
    def load(cls, relative_path: str) -> str:
        sql_path = cls.BASE_DIR / relative_path

        if not sql_path.exists():
            raise FileNotFoundError(f"No existe el archivo SQL: {sql_path}")

        return sql_path.read_text(encoding="utf-8")