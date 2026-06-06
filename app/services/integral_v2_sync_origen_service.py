# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from time import perf_counter
from typing import Any

from app.services.integral_connection_service import IntegralConnectionFactory, construir_contexto_integral_v2


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _parse_fecha(value: str) -> datetime:
    raw = str(value or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    raise ValueError(f"Fecha no válida: {value}")


def _fecha_sql(value: str) -> str:
    return _parse_fecha(value).strftime("%Y-%m-%d")


def _split_entidades(raw: str) -> list[str]:
    out, seen = [], set()
    for item in str(raw or "").split(","):
        clean = item.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out


def _qmarks(items: list[str]) -> str:
    return ",".join("?" for _ in items)


def _safe_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        if getattr(value, "year", 9999) <= 1900:
            return datetime.now()
        return value
    if isinstance(value, str) and value.startswith("0001-01-01"):
        return datetime.now()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _step(codigo: str, paso: str, entrada: Any, func):
    inicio = _now()
    t0 = perf_counter()
    try:
        salida, mensaje = func()
        estado = "ok"
        warn = None
    except Exception as exc:
        salida = "-"
        mensaje = str(exc)
        estado = "error"
        warn = f"{paso}: {mensaje}"
    fin = _now()
    return {
        "#": None,
        "Código": codigo,
        "Paso": paso,
        "Estado": estado,
        "Inicio": inicio,
        "Fin": fin,
        "Seg.": f"{perf_counter() - t0:.2f}",
        "Entrada": entrada,
        "Salida": salida,
        "Mensaje": mensaje,
    }, warn


def _enumerar(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, r in enumerate(rows, start=1):
        r["#"] = i
    return rows


def _fetch_all(conn, sql: str, params=None) -> tuple[list[str], list[tuple]]:
    cur = conn.cursor()
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]
    return cols, [tuple(r) for r in rows]


class _DestRepo:
    def __init__(self, conexion: str):
        self.conexion = conexion

    def connect(self):
        return IntegralConnectionFactory.connect_destino(self.conexion)

    def columns(self, schema: str, table: str) -> list[str]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                schema,
                table,
            )
            return [str(r[0]) for r in cur.fetchall()]

    def scalar(self, sql: str, params=None) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0

    def execute(self, sql: str, params=None) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            affected = cur.rowcount
            conn.commit()
            return affected

    def sample(self, sql: str, params=None) -> tuple[list[str], list[dict[str, Any]]]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            data = []
            for row in rows[:3]:
                item = {}
                for i, col in enumerate(cols[:8]):
                    value = row[i]
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat(sep=" ")
                    elif isinstance(value, Decimal):
                        value = float(value)
                    elif value is None:
                        value = ""
                    item[col] = value
                data.append(item)
            return cols[:8], data

    def insert_common(self, schema: str, table: str, source_cols: list[str], rows: list[tuple]) -> tuple[int, int]:
        if not rows:
            return 0, 0

        dest_cols = self.columns(schema, table)
        dest_lookup = {c.lower(): c for c in dest_cols}
        common_src, common_dst = [], []

        for col in source_cols:
            if col.lower() in dest_lookup:
                common_src.append(col)
                common_dst.append(dest_lookup[col.lower()])

        if not common_dst:
            raise ValueError(f"No hay columnas comunes para {schema}.{table}")

        src_index = {c.lower(): i for i, c in enumerate(source_cols)}
        sql = (
            f"INSERT INTO [{schema}].[{table}] "
            f"({', '.join('[' + c + ']' for c in common_dst)}) "
            f"VALUES ({', '.join('?' for _ in common_dst)})"
        )

        data = []
        for row in rows:
            data.append(tuple(_safe_value(row[src_index[c.lower()]]) for c in common_src))

        with self.connect() as conn:
            cur = conn.cursor()
            cur.fast_executemany = True
            total = 0
            for i in range(0, len(data), 1000):
                batch = data[i:i + 1000]
                cur.executemany(sql, batch)
                total += len(batch)
            conn.commit()
            return total, len(common_dst)


def _source_usuarios(conexion: str) -> tuple[list[str], list[tuple]]:
    conn = IntegralConnectionFactory.connect_source_usuarios(conexion)
    try:
        if IntegralConnectionFactory.source_engine(conexion) == "mysql":
            return _fetch_all(conn, "SELECT * FROM crm")
        return _fetch_all(conn, "SELECT * FROM dbo.usuarios")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _source_comentarios(conexion: str, fecha_sql: str, entidades: list[str]) -> tuple[list[str], list[tuple]]:
    if not entidades:
        raise ValueError("No hay entidades seleccionadas. Ejecute Fase D y aplique entidades.")

    conn = IntegralConnectionFactory.connect_source_comentarios(conexion)
    try:
        if IntegralConnectionFactory.source_engine(conexion) == "mysql":
            sql = (
                "SELECT * FROM comentarios WHERE fecha >= %s AND fecha < DATE_ADD(%s, INTERVAL 1 DAY) "
                "AND entidad IN (" + ",".join("%s" for _ in entidades) + ")"
            )
            return _fetch_all(conn, sql, [fecha_sql, fecha_sql] + entidades)

        sql = (
            "SELECT * FROM dbo.comentarios WHERE CAST(fecha AS date)=? "
            "AND entidad IN (" + _qmarks(entidades) + ")"
        )
        return _fetch_all(conn, sql, [fecha_sql] + entidades)
    finally:
        try:
            conn.close()
        except Exception:
            pass


class IntegralOrigenSyncService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = self.contexto.get("conexion") or form.get("conexion") or "local"
        self.fecha_sql = _fecha_sql(self.contexto.get("fecha_sql") or form.get("fecha_proceso") or "2026-04-29")
        self.entidades = _split_entidades(form.get("entidades_csv") or "")
        self.dest = _DestRepo(self.conexion)
        self.tiempos = []
        self.advertencias = []
        self.duplicidad = {
            "existe": False,
            "total": 0,
            "columnas": [],
            "muestra": [],
            "fecha_sql": self.fecha_sql,
            "entidades": self.entidades,
        }

    def _where_dup(self):
        if not self.entidades:
            raise ValueError("No hay entidades seleccionadas.")
        return "CAST(fecha AS date)=? AND entidad IN (" + _qmarks(self.entidades) + ")", [self.fecha_sql] + self.entidades

    def _verificar_duplicidad(self):
        where, params = self._where_dup()
        total = self.dest.scalar("SELECT COUNT_BIG(1) FROM integral.comentarios WHERE " + where, params)
        self.duplicidad["total"] = total
        self.duplicidad["existe"] = total > 0

        if total > 0:
            cols, muestra = self.dest.sample("SELECT TOP (3) * FROM integral.comentarios WHERE " + where + " ORDER BY fecha DESC", params)
            self.duplicidad["columnas"] = cols
            self.duplicidad["muestra"] = muestra
            return total, "Duplicidad detectada. Se muestran máximo 3 registros."

        return 0, "Sin duplicidad para fecha y entidades."

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        fila, warn = _step("INT-SYN-DUP", "Verificar duplicidad", self.fecha_sql, self._verificar_duplicidad)
        self.tiempos.append(fila)
        if warn:
            self.advertencias.append(warn)

        if self.advertencias:
            return self._build("Revisar", "No se pudo verificar duplicidad. No se insertó información.", inicio_total, total_t0)

        if self.duplicidad["existe"]:
            return self._build("Revisar", "Ya existen datos de la fecha proceso. Elimine o revise antes de insertar.", inicio_total, total_t0)

        def delete_users():
            affected = self.dest.execute("DELETE FROM integral.usuarios")
            return affected if affected != -1 else "Ejecutado", "Usuarios destino limpiados."

        fila, warn = _step("INT-SYN-DEL-USR", "DELETE usuarios destino", "integral.usuarios", delete_users)
        self.tiempos.append(fila)
        if warn:
            self.advertencias.append(warn)

        usuarios_cols, usuarios_rows = [], []
        if not self.advertencias:
            def read_users():
                nonlocal usuarios_cols, usuarios_rows
                usuarios_cols, usuarios_rows = _source_usuarios(self.conexion)
                return len(usuarios_rows), f"Columnas: {len(usuarios_cols)}"

            fila, warn = _step("INT-SYN-READ-USR", "Leer usuarios origen", self.conexion, read_users)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        if not self.advertencias:
            def insert_users():
                total, common = self.dest.insert_common("integral", "usuarios", usuarios_cols, usuarios_rows)
                return total, f"Columnas comunes: {common}"

            fila, warn = _step("INT-SYN-INS-USR", "Insertar usuarios destino", "integral.usuarios", insert_users)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        comentarios_cols, comentarios_rows = [], []
        if not self.advertencias:
            def read_comments():
                nonlocal comentarios_cols, comentarios_rows
                comentarios_cols, comentarios_rows = _source_comentarios(self.conexion, self.fecha_sql, self.entidades)
                return len(comentarios_rows), f"Columnas: {len(comentarios_cols)}"

            fila, warn = _step("INT-SYN-READ-COM", "Leer gestiones origen", self.fecha_sql, read_comments)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        if not self.advertencias:
            def insert_comments():
                total, common = self.dest.insert_common("integral", "comentarios", comentarios_cols, comentarios_rows)
                return total, f"Columnas comunes: {common}"

            fila, warn = _step("INT-SYN-INS-COM", "Insertar gestiones destino", "integral.comentarios", insert_comments)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "Sincronización finalizada." if estado == "Correcto" else "Sincronización finalizada con observaciones."
        return self._build(estado, mensaje, inicio_total, total_t0)

    def _build(self, estado: str, mensaje: str, inicio_total: str, total_t0: float) -> dict[str, Any]:
        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)
        self.tiempos.append({
            "#": None,
            "Código": "INT-SYN-TOTAL",
            "Paso": "Total fase E",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": f"{self.fecha_sql} / {len(self.entidades)} entidades",
            "Salida": f"Duplicados {self.duplicidad.get('total', 0)} / Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })
        return {
            "codigo": "E",
            "titulo": "Sincronizar origen",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerar(self.tiempos),
            "advertencias": self.advertencias,
            "duplicidad": self.duplicidad,
            "detalle": {
                "conexion": str(self.conexion).upper(),
                "fecha_sql": self.fecha_sql,
                "entidades": len(self.entidades),
                "destino": "Aster_Integral_Api.integral.comentarios",
            },
        }


class IntegralDuplicidadDeleteService:
    def __init__(self, form):
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = self.contexto.get("conexion") or form.get("conexion") or "local"
        self.fecha_sql = _fecha_sql(self.contexto.get("fecha_sql") or form.get("fecha_proceso") or "2026-04-29")
        self.entidades = _split_entidades(form.get("entidades_csv") or "")
        self.dest = _DestRepo(self.conexion)

    def ejecutar(self) -> dict[str, Any]:
        inicio = _now()
        t0 = perf_counter()
        advertencias = []
        try:
            if not self.entidades:
                raise ValueError("No hay entidades seleccionadas.")
            where = "CAST(fecha AS date)=? AND entidad IN (" + _qmarks(self.entidades) + ")"
            params = [self.fecha_sql] + self.entidades
            total_antes = self.dest.scalar("SELECT COUNT_BIG(1) FROM integral.comentarios WHERE " + where, params)
            eliminados = self.dest.execute("DELETE FROM integral.comentarios WHERE " + where, params)
            total_despues = self.dest.scalar("SELECT COUNT_BIG(1) FROM integral.comentarios WHERE " + where, params)
            estado = "Correcto"
            mensaje = "Datos existentes eliminados. Vuelva a ejecutar la Fase E."
        except Exception as exc:
            total_antes = "-"
            eliminados = "-"
            total_despues = "-"
            estado = "Error"
            mensaje = str(exc)
            advertencias.append(mensaje)

        fin = _now()
        seg = round(perf_counter() - t0, 2)
        return {
            "estado": estado,
            "mensaje": mensaje,
            "tiempos": [{
                "#": 1,
                "Código": "INT-SYN-DEL-DUP",
                "Paso": "Eliminar duplicidad Fase E",
                "Estado": estado,
                "Inicio": inicio,
                "Fin": fin,
                "Seg.": f"{seg:.2f}",
                "Entrada": f"{self.fecha_sql} / antes {total_antes}",
                "Salida": f"Eliminados {eliminados} / después {total_despues}",
                "Mensaje": mensaje,
            }],
            "advertencias": advertencias,
        }


def sincronizar_origen_integral_v2(form) -> dict[str, Any]:
    return IntegralOrigenSyncService(form).ejecutar()


def eliminar_duplicidad_fase_e_integral_v2(form) -> dict[str, Any]:
    return IntegralDuplicidadDeleteService(form).ejecutar()
