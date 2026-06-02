from __future__ import annotations

from typing import Any

from app.services.sql_loader import cargar_sql


class IntegralV2DestinationRepository:
    """
    Repositorio de destino para Integral v2.
    Destino esperado: Aster_Integral_Api.Integral.usuarios / comentarios.
    """

    def __init__(self, sqlserver_conn):
        self.sqlserver_conn = sqlserver_conn

    def _total_from_row(self, row: Any) -> int:
        if row is None:
            return 0
        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_usuarios.sql")

        with self.sqlserver_conn.cursor() as cursor:
            cursor.execute(sql)
            return self._total_from_row(cursor.fetchone())

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_comentarios.sql")

        with self.sqlserver_conn.cursor() as cursor:
            cursor.execute(sql, (fecha_sql, entidad))
            return self._total_from_row(cursor.fetchone())
