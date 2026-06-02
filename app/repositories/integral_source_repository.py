from __future__ import annotations

from typing import Any

from app.core.sql_loader import SqlLoader
from app.services.integral_connection_service import IntegralConnectionFactory


class IntegralSourceRepository:
    """
    Repositorio de lectura del origen Integral.
    No renderiza HTML y no conoce Flask.
    """

    def __init__(self, conexion: str, connection_factory: type[IntegralConnectionFactory] = IntegralConnectionFactory):
        self.conexion = connection_factory.normalizar_conexion(conexion)
        self.connection_factory = connection_factory

    def _sql_folder(self) -> str:
        if self.connection_factory.source_engine(self.conexion) == "mysql":
            return "integral/mysql"
        return "integral/sqlserver_origen"

    @staticmethod
    def _first_value(row: Any, key: str = "total") -> int:
        if row is None:
            return 0

        if isinstance(row, dict):
            value = row.get(key)
            if value is None and row:
                value = next(iter(row.values()))
            return int(value or 0)

        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        sql = SqlLoader.load(f"{self._sql_folder()}/count_usuarios_origen.sql")
        conn = self.connection_factory.connect_source_usuarios(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            return self._first_value(row)
        finally:
            conn.close()

    def contar_comentarios(self, fecha: str, entidad: str) -> int:
        sql = SqlLoader.load(f"{self._sql_folder()}/count_comentarios_origen.sql")
        conn = self.connection_factory.connect_source_comentarios(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fecha, entidad))
            row = cursor.fetchone()
            cursor.close()
            return self._first_value(row)
        finally:
            conn.close()

    def obtener_usuarios(self):
        sql = SqlLoader.load(f"{self._sql_folder()}/select_usuarios_origen.sql")
        conn = self.connection_factory.connect_source_usuarios(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            cursor.close()
            return columns, rows
        finally:
            conn.close()

    def obtener_comentarios(self, fecha: str, entidad: str):
        sql = SqlLoader.load(f"{self._sql_folder()}/select_comentarios_origen.sql")
        conn = self.connection_factory.connect_source_comentarios(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fecha, entidad))
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            cursor.close()
            return columns, rows
        finally:
            conn.close()
