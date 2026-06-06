# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, date
from decimal import Decimal
from time import perf_counter
from typing import Any

from app.services.integral_connection_service import construir_contexto_integral_v2, IntegralConnectionFactory
from app.services.integral_v2_common_service import fecha_tokens, resolve_file_from_form, read_table


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def _split_entidades(raw: str) -> list[str]:
    out = []
    seen = set()
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
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("0001-01-01"):
        return datetime.now()
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


def _enumerate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, row in enumerate(rows, start=1):
        row["#"] = i
    return rows


def _detect_tipo(form) -> str:
    raw = str(form.get("tipo_proceso") or form.get("tipo") or form.get("integral_tipo") or "discador").lower()
    return "manual" if "manual" in raw else "discador"


class _DestRepo:
    def __init__(self, conexion: str):
        self.conexion = conexion

    def connect(self):
        return IntegralConnectionFactory.connect_destino(self.conexion)

    def table_exists(self, schema: str, table: str) -> bool:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(1) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME=?",
                schema,
                table,
            )
            row = cur.fetchone()
            return bool(row and int(row[0] or 0) > 0)

    def columns(self, schema: str, table: str) -> list[str]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                schema,
                table,
            )
            return [str(row[0]) for row in cur.fetchall()]

    def scalar(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            affected = cur.rowcount
            conn.commit()
            return affected

    def sample(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> tuple[list[str], list[dict[str, Any]]]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [col[0] for col in cur.description]
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

    def insert_rows(self, schema: str, table: str, columns: list[str], rows: list[tuple]) -> int:
        if not rows:
            return 0

        sql = (
            f"INSERT INTO [{schema}].[{table}] "
            f"({', '.join('[' + c + ']' for c in columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})"
        )

        with self.connect() as conn:
            cur = conn.cursor()
            cur.fast_executemany = True
            total = 0
            for i in range(0, len(rows), 1000):
                batch = rows[i:i + 1000]
                cur.executemany(sql, batch)
                total += len(batch)
            conn.commit()
            return total


class IntegralCargaInicialService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = self.contexto.get("conexion") or form.get("conexion") or "local"
        self.fecha = fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.tipo = _detect_tipo(form)
        self.entidades = _split_entidades(form.get("entidades_csv") or "")
        self.repo = _DestRepo(self.conexion)
        self.schema, self.table = self._resolve_table()
        self.dest_cols = self.repo.columns(self.schema, self.table)
        self.date_col = self._resolve_col([
            "Fecha_Hora",
            "fecha_hora",
            "fecha",
            "Fecha",
            "Fecha_Gestion",
            "Fecha De Gestion",
            "fechainicio",
        ])
        self.entity_col = self._resolve_col(["entidad", "Entidad", "ENTIDAD"], required=False)
        self.file_path = resolve_file_from_form(form, self.fecha["yyyymmdd"])
        self.tiempos = []
        self.advertencias = []
        self.duplicidad = {
            "existe": False,
            "total": 0,
            "columnas": [],
            "muestra": [],
            "fecha_sql": self.fecha["sql"],
            "tabla": f"{self.schema}.{self.table}",
        }

    def _resolve_table(self) -> tuple[str, str]:
        if self.tipo == "manual":
            candidates = [("integral", "detalle_duracion")]
        else:
            candidates = [
                ("integral", "aster_ida_nc"),
                ("integral", "aster_dia_nc"),
            ]

        for schema, table in candidates:
            if self.repo.table_exists(schema, table):
                return schema, table

        raise ValueError(f"No se encontró tabla destino para tipo {self.tipo}.")

    def _resolve_col(self, variants: list[str], required: bool = True) -> str | None:
        lookup = {_normalize(c): c for c in self.dest_cols}
        for variant in variants:
            key = _normalize(variant)
            if key in lookup:
                return lookup[key]

        if required:
            raise ValueError(f"No se encontró columna requerida en {self.schema}.{self.table}: {variants}")

        return None

    def _where_dup(self) -> tuple[str, list[Any]]:
        where = f"CAST([{self.date_col}] AS date)=?"
        params = [self.fecha["sql"]]

        if self.entity_col and self.entidades:
            where += f" AND [{self.entity_col}] IN (" + _qmarks(self.entidades) + ")"
            params.extend(self.entidades)

        return where, params

    def _verificar_duplicidad(self):
        where, params = self._where_dup()
        total = self.repo.scalar(f"SELECT COUNT_BIG(1) FROM [{self.schema}].[{self.table}] WHERE {where}", params)
        self.duplicidad["total"] = total
        self.duplicidad["existe"] = total > 0

        if total > 0:
            cols, sample = self.repo.sample(
                f"SELECT TOP (3) * FROM [{self.schema}].[{self.table}] WHERE {where} ORDER BY [{self.date_col}] DESC",
                params,
            )
            self.duplicidad["columnas"] = cols
            self.duplicidad["muestra"] = sample
            return total, "Duplicidad detectada. Se muestran máximo 3 registros."

        return 0, "Sin duplicidad en tabla inicial."

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        fila, warn = _step("INT-CAR-DUP", "Verificar duplicidad tabla inicial", self.fecha["sql"], self._verificar_duplicidad)
        self.tiempos.append(fila)
        if warn:
            self.advertencias.append(warn)

        if self.advertencias:
            return self._build("Revisar", "No se pudo verificar duplicidad. No se insertó información.", inicio_total, total_t0)

        if self.duplicidad["existe"]:
            return self._build("Revisar", "Ya existen datos de la fecha proceso. Elimine o revise antes de insertar.", inicio_total, total_t0)

        file_cols = []
        file_rows_dict = []

        def read_file():
            nonlocal file_cols, file_rows_dict
            file_cols, file_rows_dict = read_table(self.file_path)
            return len(file_rows_dict), f"Columnas archivo: {len(file_cols)}"

        fila, warn = _step("INT-CAR-READ", "Leer archivo", str(self.file_path), read_file)
        self.tiempos.append(fila)
        if warn:
            self.advertencias.append(warn)

        common_source = []
        common_dest = []
        rows = []

        if not self.advertencias:
            def map_cols():
                nonlocal common_source, common_dest, rows
                dest_lookup = {_normalize(c): c for c in self.dest_cols}

                for source_col in file_cols:
                    key = _normalize(source_col)
                    if key in dest_lookup:
                        common_source.append(source_col)
                        common_dest.append(dest_lookup[key])

                if not common_dest:
                    raise ValueError(
                        "No hay columnas comunes entre archivo y tabla destino. "
                        "Revise encabezados del archivo y columnas SQL."
                    )

                for item in file_rows_dict:
                    rows.append(tuple(_safe_value(item.get(src)) for src in common_source))

                return len(common_dest), f"Filas preparadas: {len(rows)}"

            fila, warn = _step("INT-CAR-MAP", "Mapear columnas comunes", f"{len(file_cols)} columnas archivo", map_cols)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        if not self.advertencias:
            def insert():
                total = self.repo.insert_rows(self.schema, self.table, common_dest, rows)
                return total, f"Insertado en {self.schema}.{self.table}"

            fila, warn = _step("INT-CAR-INS", "Insertar tabla inicial", f"{self.schema}.{self.table}", insert)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "Carga inicial finalizada." if estado == "Correcto" else "Carga inicial finalizada con observaciones."
        return self._build(estado, mensaje, inicio_total, total_t0)

    def _build(self, estado: str, mensaje: str, inicio_total: str, total_t0: float) -> dict[str, Any]:
        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)

        self.tiempos.append({
            "#": None,
            "Código": "INT-CAR-TOTAL",
            "Paso": "Total fase F",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": self.file_path.name,
            "Salida": f"Duplicados {self.duplicidad.get('total', 0)} / Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })

        return {
            "codigo": "F",
            "titulo": "Cargar tabla inicial",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerate(self.tiempos),
            "advertencias": self.advertencias,
            "duplicidad": self.duplicidad,
            "detalle": {
                "conexion": str(self.conexion).upper(),
                "tipo": self.tipo.upper(),
                "tabla": f"{self.schema}.{self.table}",
                "fecha_sql": self.fecha["sql"],
                "archivo": str(self.file_path),
                "columna_fecha": self.date_col,
                "columna_entidad": self.entity_col or "-",
            },
        }


class IntegralCargaInicialDeleteService:
    def __init__(self, form):
        self.base = IntegralCargaInicialService(form)

    def ejecutar(self) -> dict[str, Any]:
        inicio = _now()
        t0 = perf_counter()
        advertencias = []

        try:
            where, params = self.base._where_dup()
            total_antes = self.base.repo.scalar(
                f"SELECT COUNT_BIG(1) FROM [{self.base.schema}].[{self.base.table}] WHERE {where}",
                params,
            )
            eliminados = self.base.repo.execute(
                f"DELETE FROM [{self.base.schema}].[{self.base.table}] WHERE {where}",
                params,
            )
            total_despues = self.base.repo.scalar(
                f"SELECT COUNT_BIG(1) FROM [{self.base.schema}].[{self.base.table}] WHERE {where}",
                params,
            )
            estado = "Correcto"
            mensaje = "Datos existentes eliminados. Vuelva a ejecutar la Fase F."
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
                "Código": "INT-CAR-DEL-DUP",
                "Paso": "Eliminar duplicidad Fase F",
                "Estado": estado,
                "Inicio": inicio,
                "Fin": fin,
                "Seg.": f"{seg:.2f}",
                "Entrada": f"{self.base.fecha['sql']} / antes {total_antes}",
                "Salida": f"Eliminados {eliminados} / después {total_despues}",
                "Mensaje": mensaje,
            }],
            "advertencias": advertencias,
        }


def cargar_tabla_inicial_integral_v2(form) -> dict[str, Any]:
    return IntegralCargaInicialService(form).ejecutar()


def eliminar_duplicidad_fase_f_integral_v2(form) -> dict[str, Any]:
    return IntegralCargaInicialDeleteService(form).ejecutar()
