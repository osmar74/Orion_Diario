from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.sql_loader import cargar_sql


class IntegralV2SourceRepository:
    """
    Repositorio de origen para Integral v2.

    Reglas:
    - No contiene SQL duro; todo se carga desde app/sql/integral/v2.
    - LOCAL: SQL Server gestioncomercial_dev.
    - REMOTO: MySQL usuarios / gestioncomercial.
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

    def _execute_cursor(self, cursor, sql: str, params: tuple | list | None = None) -> None:
        params_tuple = tuple(params or ())
        module_name = type(cursor).__module__.lower()

        if "pyodbc" in module_name:
            if params_tuple:
                cursor.execute(sql, *params_tuple)
            else:
                cursor.execute(sql)
            return

        cursor.execute(sql, params_tuple)

    def _fetchone_total(self, conn, sql: str, params: tuple | list | None = None) -> int:
        cursor = conn.cursor()
        try:
            self._execute_cursor(cursor, sql, params)
            return self._total_from_row(cursor.fetchone())
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _read_dataframe(self, conn, sql: str, params: tuple | list | None = None) -> pd.DataFrame:
        cursor = conn.cursor()
        try:
            self._execute_cursor(cursor, sql, params)
            rows = cursor.fetchall()

            if not rows:
                columns = [column[0] for column in (cursor.description or [])]
                return pd.DataFrame(columns=columns)

            first = rows[0]

            if isinstance(first, dict):
                return pd.DataFrame(rows)

            columns = [column[0] for column in cursor.description]
            values = [tuple(row) for row in rows]
            return pd.DataFrame(values, columns=columns)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _rutas_usuarios(self, tipo: str) -> list[str]:
        if self.es_remoto_mysql:
            return [f"integral/v2/mysql/{tipo}_usuarios.sql"]

        # LOCAL: primero dbo.usuarios, alternativa dbo.crm por compatibilidad.
        return [
            f"integral/v2/sqlserver_origen/{tipo}_usuarios.sql",
            f"integral/v2/sqlserver_origen/{tipo}_usuarios_crm.sql",
        ]

    def _ejecutar_con_fallback(self, conn, rutas: list[str], executor):
        ultimo_error: Exception | None = None

        for ruta in rutas:
            try:
                sql = cargar_sql(ruta)
                return executor(sql)
            except Exception as exc:
                ultimo_error = exc
                continue

        if ultimo_error:
            raise ultimo_error

        raise RuntimeError("No hay rutas SQL configuradas para ejecutar la operación.")

    def contar_usuarios(self) -> int:
        return int(
            self._ejecutar_con_fallback(
                self.usuarios_conn,
                self._rutas_usuarios("count"),
                lambda sql: self._fetchone_total(self.usuarios_conn, sql),
            )
        )

    def contar_comentarios(self, fecha_sql: str, entidad: str) -> int:
        ruta = (
            "integral/v2/mysql/count_comentarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/count_comentarios.sql"
        )
        sql = cargar_sql(ruta)
        return self._fetchone_total(self.comentarios_conn, sql, (fecha_sql, entidad))

    def leer_usuarios(self) -> pd.DataFrame:
        return self._ejecutar_con_fallback(
            self.usuarios_conn,
            self._rutas_usuarios("select"),
            lambda sql: self._read_dataframe(self.usuarios_conn, sql),
        )

    def leer_comentarios(self, fecha_sql: str, entidad: str) -> pd.DataFrame:
        ruta = (
            "integral/v2/mysql/select_comentarios.sql"
            if self.es_remoto_mysql
            else "integral/v2/sqlserver_origen/select_comentarios.sql"
        )
        sql = cargar_sql(ruta)
        return self._read_dataframe(self.comentarios_conn, sql, (fecha_sql, entidad))
