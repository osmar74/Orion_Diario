import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

from app.services.sql_loader import cargar_sql


class LogService:
    """Servicio para registrar y consultar logs del proceso Orion/Aister."""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: Ruta del archivo SQLite de logs.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Crea la tabla de logs si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(cargar_sql("local/log_create_table.sql"))
            conn.commit()

    def log(
        self,
        fase: str,
        accion: str,
        resultado: str,
        detalle: str = "",
        datos_extra: Optional[str] = None,
    ):
        """
        Inserta un registro de log.

        Args:
            fase: Identificador de la fase (ej. '2.1', 'Discador').
            accion: Descripción de la acción (ej. 'Creación de carpetas').
            resultado: 'éxito', 'error', 'info' o 'advertencia'.
            detalle: Texto explicativo.
            datos_extra: JSON opcional con información adicional.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                cargar_sql("local/log_insert.sql"),
                (fase, accion, resultado, detalle, datos_extra),
            )
            conn.commit()

    def obtener_logs(
        self,
        fase: Optional[str] = None,
        resultado: Optional[str] = None,
        limite: int = 200,
    ) -> List[Dict]:
        """
        Recupera los logs, con filtros opcionales.

        Args:
            fase: Filtrar por fase específica.
            resultado: Filtrar por resultado ('éxito', 'error', etc.).
            limite: Máximo número de registros.

        Returns:
            Lista de diccionarios con los campos de la tabla.
        """
        query = cargar_sql("local/log_select_base.sql").strip()
        params = []

        if fase:
            query += " " + cargar_sql("local/log_filter_fase.sql").strip()
            params.append(fase)
        if resultado:
            query += " " + cargar_sql("local/log_filter_resultado.sql").strip()
            params.append(resultado)

        query += " " + cargar_sql("local/log_select_order_limit.sql").strip()
        params.append(limite)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
