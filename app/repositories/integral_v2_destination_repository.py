from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.sql_loader import cargar_sql


class IntegralV2DestinationRepository:
    """
    Repositorio de destino para Integral v2.
    Destino esperado: Aster_Integral_Api.Integral.usuarios / comentarios.
    """

    def __init__(self, sqlserver_conn, schema: str = "Integral"):
        self.sqlserver_conn = sqlserver_conn
        self.schema = schema

    def _total_from_row(self, row: Any) -> int:
        if row is None:
            return 0
        return int(row[0] or 0)

    def contar_usuarios(self) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_usuarios.sql")
        cursor = self.sqlserver_conn.cursor()
        try:
            cursor.execute(sql)
            return self._total_from_row(cursor.fetchone())
        finally:
            cursor.close()

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        sql = cargar_sql("integral/v2/sqlserver_destino/count_comentarios.sql")
        cursor = self.sqlserver_conn.cursor()
        try:
            cursor.execute(sql, fecha_sql, entidad)
            return self._total_from_row(cursor.fetchone())
        finally:
            cursor.close()

    def limpiar_usuarios(self) -> int:
        antes = self.contar_usuarios()
        sql = cargar_sql("integral/v2/sqlserver_destino/delete_usuarios.sql")
        cursor = self.sqlserver_conn.cursor()
        try:
            cursor.execute(sql)
            return antes
        finally:
            cursor.close()

    def limpiar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        antes = self.contar_comentarios(fecha_sql, entidad)
        sql = cargar_sql("integral/v2/sqlserver_destino/delete_comentarios.sql")
        cursor = self.sqlserver_conn.cursor()
        try:
            cursor.execute(sql, fecha_sql, entidad)
            return antes
        finally:
            cursor.close()

    def obtener_columnas_tabla(self, tabla: str) -> list[dict[str, Any]]:
        sql = cargar_sql("integral/v2/sqlserver_destino/metadata_columnas.sql")
        cursor = self.sqlserver_conn.cursor()
        try:
            cursor.execute(sql, self.schema, tabla)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, tuple(row))) for row in rows]
        finally:
            cursor.close()

    def insertar_dataframe(self, tabla: str, df_insert: pd.DataFrame, tamano_lote: int = 1000) -> int:
        if df_insert is None or df_insert.empty:
            return 0

        columnas = list(df_insert.columns)
        tabla_sql = self._nombre_tabla_sql(tabla)
        columnas_sql = ", ".join(self._identificador(columna) for columna in columnas)
        placeholders = ", ".join("?" for _ in columnas)

        sql_insert = cargar_sql("integral/v2/sqlserver_destino/insert_generico.sql").format(
            tabla=tabla_sql,
            columnas=columnas_sql,
            placeholders=placeholders,
        )

        cursor = self.sqlserver_conn.cursor()
        total_insertados = 0
        try:
            cursor.fast_executemany = True

            for inicio in range(0, len(df_insert), tamano_lote):
                bloque = df_insert.iloc[inicio : inicio + tamano_lote]
                valores = [
                    tuple(self._limpiar_parametro(row[columna]) for columna in columnas)
                    for _, row in bloque.iterrows()
                ]

                if valores:
                    cursor.executemany(sql_insert, valores)
                    total_insertados += len(valores)

            return total_insertados
        finally:
            cursor.close()

    def _nombre_tabla_sql(self, tabla: str) -> str:
        return f"{self._identificador(self.schema)}.{self._identificador(tabla)}"

    def _identificador(self, nombre: str) -> str:
        return "[" + str(nombre).replace("]", "]]" ) + "]"

    def _limpiar_parametro(self, valor: Any) -> Any:
        if valor is None:
            return None

        try:
            if pd.isna(valor):
                return None
        except Exception:
            pass

        texto = str(valor).strip()
        if texto.lower() in {"nan", "nat", "none", "null"}:
            return None

        return valor
