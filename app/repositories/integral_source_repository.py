from app.core.sql_loader import SqlLoader


class IntegralSourceRepository:
    """
    Repositorio de lectura para el origen Integral.
    Origen esperado:
    - MySQL usuarios.crm
    - MySQL gestioncomercial.comentarios
    """

    def __init__(self, mysql_connection):
        self.mysql_connection = mysql_connection

    def contar_usuarios(self) -> int:
        sql = SqlLoader.load("integral/mysql/count_usuarios_origen.sql")

        cursor = self.mysql_connection.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()

        return int(row[0] or 0)

    def contar_comentarios(self, fecha: str, entidad: str) -> int:
        sql = SqlLoader.load("integral/mysql/count_comentarios_origen.sql")

        cursor = self.mysql_connection.cursor()
        cursor.execute(sql, (fecha, entidad))
        row = cursor.fetchone()
        cursor.close()

        return int(row[0] or 0)

    def obtener_usuarios(self):
        sql = SqlLoader.load("integral/mysql/select_usuarios_origen.sql")

        cursor = self.mysql_connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        cursor.close()

        return columns, rows

    def obtener_comentarios(self, fecha: str, entidad: str):
        sql = SqlLoader.load("integral/mysql/select_comentarios_origen.sql")

        cursor = self.mysql_connection.cursor()
        cursor.execute(sql, (fecha, entidad))
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        cursor.close()

        return columns, rows