from app.core.sql_loader import SqlLoader


class IntegralDestinationRepository:
    """
    Repositorio de escritura/validación para destino Integral.
    Destino esperado:
    - SQL Server Aster_Integral_Api.Integral.usuarios
    - SQL Server Aster_Integral_Api.Integral.comentarios
    """

    def __init__(self, sqlserver_connection):
        self.sqlserver_connection = sqlserver_connection

    def limpiar_usuarios(self) -> None:
        sql = SqlLoader.load("integral/sqlserver/delete_usuarios_destino.sql")

        cursor = self.sqlserver_connection.cursor()
        cursor.execute(sql)
        self.sqlserver_connection.commit()
        cursor.close()

    def limpiar_comentarios(self, fecha: str, entidad: str) -> None:
        sql = SqlLoader.load("integral/sqlserver/delete_comentarios_destino.sql")

        cursor = self.sqlserver_connection.cursor()
        cursor.execute(sql, (fecha, entidad))
        self.sqlserver_connection.commit()
        cursor.close()

    def contar_usuarios(self) -> int:
        sql = SqlLoader.load("integral/sqlserver/count_usuarios_destino.sql")

        cursor = self.sqlserver_connection.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()

        return int(row[0] or 0)

    def contar_comentarios(self, fecha: str, entidad: str) -> int:
        sql = SqlLoader.load("integral/sqlserver/count_comentarios_destino.sql")

        cursor = self.sqlserver_connection.cursor()
        cursor.execute(sql, (fecha, entidad))
        row = cursor.fetchone()
        cursor.close()

        return int(row[0] or 0)