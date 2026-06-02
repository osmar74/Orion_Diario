from __future__ import annotations

from typing import Any

from app.services.sql_loader import cargar_sql


class IntegralV2SourceRepository:
    """
    Repositorio de origen para Integral v2.
    No contiene SQL duro: todo se carga desde app/sql/integral/v2.
    """

    def __init__(self, conexion: str, usuarios_conn, comentarios_conn):
        self.conexion = str(conexion or "local").strip().lower()
        self.usuarios_conn = usuarios_conn
        self.comentarios_conn = comentarios_conn

    @property
    def es_remoto_mysql(self) -> bool:
        return self.conexion == "remoto"

    def _total_from_row(self, row: Any) -> int:
        if row is None:
            return 0

        if isinstance(row, dict):
            return int(row.get("total") or 0)

        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        ruta = (
            "integral/v2/mysql/count_usuarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/count_usuarios.sql"
        )
        sql = cargar_sql(ruta)

        with self.usuarios_conn.cursor() as cursor:
            cursor.execute(sql)
            return self._total_from_row(cursor.fetchone())

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        ruta = (
            "integral/v2/mysql/count_comentarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/count_comentarios.sql"
        )
        sql = cargar_sql(ruta)

        with self.comentarios_conn.cursor() as cursor:
            cursor.execute(sql, (fecha_sql, entidad))
            return self._total_from_row(cursor.fetchone())
