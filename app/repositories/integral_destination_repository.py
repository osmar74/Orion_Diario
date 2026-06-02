from __future__ import annotations

from typing import Any

from app.core.sql_loader import SqlLoader
from app.services.integral_connection_service import IntegralConnectionFactory


class IntegralDestinationRepository:
    """
    Repositorio de escritura/validación del destino Integral.
    Destino esperado: SQL Server, base Aster_Integral_Api, esquema Integral.
    """

    def __init__(self, conexion: str, connection_factory: type[IntegralConnectionFactory] = IntegralConnectionFactory):
        self.conexion = connection_factory.normalizar_conexion(conexion)
        self.connection_factory = connection_factory

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

    def limpiar_usuarios(self) -> None:
        sql = SqlLoader.load("integral/sqlserver_destino/delete_usuarios_destino.sql")
        conn = self.connection_factory.connect_destino(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            cursor.close()
        finally:
            conn.close()

    def limpiar_comentarios(self, fecha: str, entidad: str) -> None:
        sql = SqlLoader.load("integral/sqlserver_destino/delete_comentarios_destino.sql")
        conn = self.connection_factory.connect_destino(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fecha, entidad))
            conn.commit()
            cursor.close()
        finally:
            conn.close()

    def contar_usuarios(self) -> int:
        sql = SqlLoader.load("integral/sqlserver_destino/count_usuarios_destino.sql")
        conn = self.connection_factory.connect_destino(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            return self._first_value(row)
        finally:
            conn.close()

    def contar_comentarios(self, fecha: str, entidad: str) -> int:
        sql = SqlLoader.load("integral/sqlserver_destino/count_comentarios_destino.sql")
        conn = self.connection_factory.connect_destino(self.conexion)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fecha, entidad))
            row = cursor.fetchone()
            cursor.close()
            return self._first_value(row)
        finally:
            conn.close()
