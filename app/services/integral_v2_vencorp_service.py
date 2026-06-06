# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from app.services.integral_connection_service import construir_contexto_integral_v2

VENCORP_SCHEMA = "gestion"
VENCORP_TABLE = "gestion_integral"
VENCORP_DATABASE = "Vencorp_Integral"


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _normalizar_conexion(value: str | None) -> str:
    raw = str(value or "local").strip().lower()
    return raw if raw in {"local", "remoto"} else "local"


def _parse_fecha(value: str) -> datetime:
    raw = str(value or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    raise ValueError(f"Fecha no válida: {value}")


def _fecha_tokens(value: str) -> dict[str, str]:
    dt = _parse_fecha(value)
    return {
        "yyyymmdd": dt.strftime("%Y%m%d"),
        "sql": dt.strftime("%Y-%m-%d"),
        "visual": dt.strftime("%d/%m/%Y"),
        "mes_gestion": dt.strftime("%Y%m"),
    }


def _data_dir() -> Path:
    return Path(os.getenv("INTEGRAL_DATA_DIR") or os.getenv("DATA_DIR") or r"E:\data")


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def _vencorp_header_aliases() -> dict[str, str]:
    # Alias explícitos entre encabezados del archivo oficial y campos SQL fijos.
    # No modifica el CSV/Excel ni la tabla SQL.
    return {
        # Cliente del archivo oficial -> campo SQL fijo Vencorp.
        "clientenro": "ClienteNro_Contrato",
        "clientenrocontrato": "ClienteNro_Contrato",
        "nrocliente": "ClienteNro_Contrato",
        "numerocliente": "ClienteNro_Contrato",
        "clientecontrato": "ClienteNro_Contrato",
    }


def _resolver_campo_sql_por_alias(file_col: str, sql_lookup: dict) -> tuple[dict | None, str, str]:
    key = _normalize(file_col)
    sql_item = sql_lookup.get(key)

    if sql_item:
        return sql_item, "OK", "Match normalizado."

    alias_sql_name = _vencorp_header_aliases().get(key)
    if alias_sql_name:
        sql_item = sql_lookup.get(_normalize(alias_sql_name))
        if sql_item:
            return sql_item, "OK ALIAS", f"Match por alias: {file_col} -> {sql_item['name']}."

    return None, "SIN MATCH", "El encabezado no existe en gestion.gestion_integral ni en alias permitidos."


def _sql_ident(value: str) -> str:
    return "[" + str(value).replace("]", "]]" ) + "]"


def _empty_value(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "nat", "none", "null"}


def _format_value_for_display(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None:
        return ""
    return str(value)


def _convert_value(value: Any, sql_type: str) -> Any:
    sql_type = str(sql_type or "").lower()
    if _empty_value(value):
        if sql_type in {"varchar", "nvarchar", "char", "nchar", "text", "ntext"}:
            return ""
        return None
    raw = str(value).strip()
    if sql_type == "date":
        dt = pd.to_datetime(raw, errors="coerce", dayfirst=True)
        return None if pd.isna(dt) else dt.date()
    if sql_type in {"datetime", "datetime2", "smalldatetime"}:
        dt = pd.to_datetime(raw, errors="coerce", dayfirst=True)
        return None if pd.isna(dt) else dt.to_pydatetime()
    if sql_type in {"int", "bigint", "smallint", "tinyint"}:
        try:
            return int(float(raw.replace(",", "")))
        except Exception:
            return None
    if sql_type in {"decimal", "numeric", "float", "real", "money", "smallmoney"}:
        try:
            return float(raw.replace(",", ""))
        except Exception:
            return None
    if sql_type == "bit":
        lowered = raw.lower()
        if lowered in {"1", "true", "si", "sí", "yes", "y"}:
            return 1
        if lowered in {"0", "false", "no", "n"}:
            return 0
        return None
    return raw


def _cfg_vencorp(conexion: str) -> dict[str, str]:
    modo = _normalizar_conexion(conexion)
    if modo == "remoto":
        return {
            "driver": _env_first("INTEGRAL_VENCORP_REMOTO_DRIVER", "INTEGRAL_SQL_REMOTO_DRIVER", "ORION_SQL_REMOTO_DRIVER", default="ODBC Driver 18 for SQL Server"),
            "server": _env_first("INTEGRAL_VENCORP_REMOTO_SERVER", "INTEGRAL_SQL_REMOTO_SERVER", "ORION_SQL_REMOTO_SERVER", default="172.24.80.32"),
            "database": _env_first("INTEGRAL_VENCORP_REMOTO_DATABASE", "INTEGRAL_VENCORP_DATABASE", default=VENCORP_DATABASE),
            "username": _env_first("INTEGRAL_VENCORP_REMOTO_USERNAME", "INTEGRAL_SQL_REMOTO_USERNAME", "ORION_SQL_REMOTO_USERNAME", default="Admin1"),
            "password": _env_first("INTEGRAL_VENCORP_REMOTO_PASSWORD", "INTEGRAL_SQL_REMOTO_PASSWORD", "ORION_SQL_REMOTO_PASSWORD", default=""),
            "encrypt": _env_first("INTEGRAL_VENCORP_REMOTO_ENCRYPT", "INTEGRAL_SQL_REMOTO_ENCRYPT", "ORION_SQL_REMOTO_ENCRYPT", default="yes"),
            "trust": _env_first("INTEGRAL_VENCORP_REMOTO_TRUST_SERVER_CERTIFICATE", "INTEGRAL_SQL_REMOTO_TRUST_SERVER_CERTIFICATE", "ORION_SQL_REMOTO_TRUST_SERVER_CERTIFICATE", default="yes"),
        }
    return {
        "driver": _env_first("INTEGRAL_VENCORP_LOCAL_DRIVER", "INTEGRAL_SQL_LOCAL_DRIVER", "ORION_SQL_LOCAL_DRIVER", "SQLSERVER_DRIVER", default="ODBC Driver 18 for SQL Server"),
        "server": _env_first("INTEGRAL_VENCORP_LOCAL_SERVER", "INTEGRAL_SQL_LOCAL_SERVER", "ORION_SQL_LOCAL_SERVER", "SQLSERVER_SERVER", default=r"localhost\SQL2025DEV"),
        "database": _env_first("INTEGRAL_VENCORP_LOCAL_DATABASE", "INTEGRAL_VENCORP_DATABASE", default=VENCORP_DATABASE),
        "username": _env_first("INTEGRAL_VENCORP_LOCAL_USERNAME", "INTEGRAL_SQL_LOCAL_USERNAME", "ORION_SQL_LOCAL_USERNAME", "SQLSERVER_USER", default="Admin1"),
        "password": _env_first("INTEGRAL_VENCORP_LOCAL_PASSWORD", "INTEGRAL_SQL_LOCAL_PASSWORD", "ORION_SQL_LOCAL_PASSWORD", "SQLSERVER_PASSWORD", default=""),
        "encrypt": _env_first("INTEGRAL_VENCORP_LOCAL_ENCRYPT", "INTEGRAL_SQL_LOCAL_ENCRYPT", "ORION_SQL_LOCAL_ENCRYPT", default="yes"),
        "trust": _env_first("INTEGRAL_VENCORP_LOCAL_TRUST_SERVER_CERTIFICATE", "INTEGRAL_SQL_LOCAL_TRUST_SERVER_CERTIFICATE", "ORION_SQL_LOCAL_TRUST_SERVER_CERTIFICATE", "SQLSERVER_TRUST_CERTIFICATE", default="yes"),
    }


def _connect_vencorp(conexion: str):
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("No está instalado pyodbc. Ejecute: pip install pyodbc") from exc
    cfg = _cfg_vencorp(conexion)
    parts = [
        f"DRIVER={{{cfg['driver']}}}",
        f"SERVER={cfg['server']}",
        f"DATABASE={cfg['database']}",
        f"Encrypt={cfg['encrypt']}",
        f"TrustServerCertificate={cfg['trust']}",
    ]
    if cfg.get("username"):
        parts.append(f"UID={cfg['username']}")
        parts.append(f"PWD={cfg.get('password', '')}")
    else:
        parts.append("Trusted_Connection=yes")
    return pyodbc.connect(";".join(parts) + ";", timeout=15)


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
    for i, row in enumerate(rows, start=1):
        row["#"] = i
    return rows


class VencorpRepo:
    def __init__(self, conexion: str):
        self.conexion = _normalizar_conexion(conexion)
        self.cfg = _cfg_vencorp(self.conexion)

    def connect(self):
        return _connect_vencorp(self.conexion)

    def test_connection(self) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT @@SERVERNAME AS servidor, DB_NAME() AS base_datos")
            row = cur.fetchone()
            return {"servidor_sql": str(row[0] or ""), "base_datos": str(row[1] or ""), "server_config": self.cfg["server"], "database_config": self.cfg["database"]}

    def table_exists(self) -> bool:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME=?", VENCORP_SCHEMA, VENCORP_TABLE)
            row = cur.fetchone()
            return bool(row and int(row[0] or 0) > 0)

    def columns_metadata(self) -> list[dict[str, Any]]:
        sql = """
        SELECT c.COLUMN_NAME, c.DATA_TYPE, c.IS_NULLABLE, c.COLUMN_DEFAULT,
               COLUMNPROPERTY(OBJECT_ID(QUOTENAME(c.TABLE_SCHEMA)+'.'+QUOTENAME(c.TABLE_NAME)), c.COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY,
               c.ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
        ORDER BY c.ORDINAL_POSITION
        """
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, VENCORP_SCHEMA, VENCORP_TABLE)
            return [{"name": str(r[0]), "type": str(r[1]), "nullable": str(r[2]).upper() == "YES", "default": r[3], "identity": bool(r[4]), "ordinal": int(r[5])} for r in cur.fetchall()]

    def scalar(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0

    def sample(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> tuple[list[str], list[dict[str, str]]]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            data = []
            for row in rows[:3]:
                item = {}
                for idx, col in enumerate(cols[:10]):
                    item[col] = _format_value_for_display(row[idx])
                data.append(item)
            return cols[:10], data

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            affected = cur.rowcount
            conn.commit()
            return affected

    def insert_dataframe(self, df: pd.DataFrame, column_map: list[dict[str, Any]]) -> int:
        if df.empty:
            return 0
        sql_columns = [item["sql_col"] for item in column_map]
        source_columns = [item["file_col"] for item in column_map]
        sql_types = [item["sql_type"] for item in column_map]
        sql = f"INSERT INTO {_sql_ident(VENCORP_SCHEMA)}.{_sql_ident(VENCORP_TABLE)} ({', '.join(_sql_ident(c) for c in sql_columns)}) VALUES ({', '.join('?' for _ in sql_columns)})"
        rows = []
        for _, row in df.iterrows():
            rows.append(tuple(_convert_value(row[src], typ) for src, typ in zip(source_columns, sql_types)))
        with self.connect() as conn:
            try:
                cur = conn.cursor()
                cur.fast_executemany = True
                total = 0
                for i in range(0, len(rows), 1000):
                    batch = rows[i:i + 1000]
                    cur.executemany(sql, batch)
                    total += len(batch)
                conn.commit()
                return total
            except Exception:
                conn.rollback()
                raise


class IntegralVencorpService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = _normalizar_conexion(self.contexto.get("conexion") or form.get("conexion") or "local")
        self.fecha = _fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.mes_gestion = str(form.get("mes_gestion") or self.contexto.get("mes_gestion") or self.fecha["mes_gestion"]).strip()
        if not re.fullmatch(r"\d{6}", self.mes_gestion):
            self.mes_gestion = self.fecha["mes_gestion"]
        self.base_dir = _data_dir() / self.fecha["yyyymmdd"] / "Integral"
        self.oficial_dir = self.base_dir / "04_oficial"
        self.csv_oficial = self.oficial_dir / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.xlsx_oficial = self.oficial_dir / f"{self.fecha['yyyymmdd']}_Gestion_excel.xlsx"
        self.repo = VencorpRepo(self.conexion)
        self.tiempos: list[dict[str, Any]] = []
        self.advertencias: list[str] = []
        self.conexion_info: dict[str, Any] = {}
        self.archivo_info: dict[str, Any] = {}
        self.validacion_columnas: list[dict[str, Any]] = []
        self.duplicidad: dict[str, Any] = {"existe": False, "total": 0, "columnas": [], "muestra": [], "criterio": ""}
        self.insercion: dict[str, Any] = {"registros_archivo": 0, "registros_preparados": 0, "registros_insertados": 0, "registros_rechazados": 0}
        self.cubo: dict[str, Any] = {"estado": "Stand by", "mensaje": "Actualización de cubo Excel suspendida hasta nuevo aviso."}

    def _validar_archivo(self):
        if self.csv_oficial.exists():
            self.archivo_path = self.csv_oficial
            self.df = pd.read_csv(self.archivo_path, dtype=str, encoding="utf-8-sig").fillna("")
            tipo = "CSV oficial"
        elif self.xlsx_oficial.exists():
            self.archivo_path = self.xlsx_oficial
            self.df = pd.read_excel(self.archivo_path, dtype=str).fillna("")
            tipo = "Excel oficial"
        else:
            raise FileNotFoundError("No existe archivo oficial de Fase H. Ejecute primero H — Generar oficiales. Buscado: " + str(self.csv_oficial) + " / " + str(self.xlsx_oficial))
        self.archivo_info = {"tipo": tipo, "ruta": str(self.archivo_path), "registros": len(self.df), "columnas": len(self.df.columns)}
        self.insercion["registros_archivo"] = len(self.df)
        return len(self.df), f"{tipo}: {self.archivo_path}"

    def _probar_conexion(self):
        self.conexion_info = self.repo.test_connection()
        return self.conexion_info.get("database_config", ""), f"Servidor: {self.conexion_info.get('server_config')}"

    def _validar_tabla(self):
        if not self.repo.table_exists():
            raise ValueError(f"No existe la tabla destino {VENCORP_DATABASE}.{VENCORP_SCHEMA}.{VENCORP_TABLE}")
        self.sql_columns_meta = self.repo.columns_metadata()
        return len(self.sql_columns_meta), f"Tabla destino: {VENCORP_SCHEMA}.{VENCORP_TABLE}"

    def _validar_columnas(self):
        sql_lookup = {_normalize(item["name"]): item for item in self.sql_columns_meta}

        self.column_map: list[dict[str, Any]] = []
        file_unmatched: list[str] = []

        for file_col in self.df.columns:
            sql_item, estado_match, detalle_match = _resolver_campo_sql_por_alias(file_col, sql_lookup)

            if sql_item:
                self.column_map.append({
                    "file_col": file_col,
                    "sql_col": sql_item["name"],
                    "sql_type": sql_item["type"],
                })
                self.validacion_columnas.append({
                    "encabezado_archivo": file_col,
                    "campo_sql": sql_item["name"],
                    "tipo_sql": sql_item["type"],
                    "estado": estado_match,
                    "detalle": detalle_match,
                })
            else:
                file_unmatched.append(file_col)
                self.validacion_columnas.append({
                    "encabezado_archivo": file_col,
                    "campo_sql": "-",
                    "tipo_sql": "-",
                    "estado": "SIN MATCH",
                    "detalle": detalle_match,
                })

        required_missing = []
        mapped_sql = {_normalize(item["sql_col"]) for item in self.column_map}

        for sql_item in self.sql_columns_meta:
            key = _normalize(sql_item["name"])

            if key in mapped_sql:
                continue

            is_optional = bool(sql_item["identity"]) or bool(sql_item["nullable"]) or sql_item["default"] is not None

            if not is_optional:
                required_missing.append(sql_item["name"])

            self.validacion_columnas.append({
                "encabezado_archivo": "-",
                "campo_sql": sql_item["name"],
                "tipo_sql": sql_item["type"],
                "estado": "FALTANTE REQUERIDO" if not is_optional else "SQL EXTRA OPCIONAL",
                "detalle": "Columna SQL sin encabezado equivalente en archivo oficial.",
            })

        if file_unmatched:
            raise ValueError(
                "Hay encabezados del archivo oficial sin campo SQL equivalente: "
                + ", ".join(file_unmatched[:10])
            )

        if required_missing:
            raise ValueError(
                "Hay campos SQL requeridos sin encabezado en el archivo oficial: "
                + ", ".join(required_missing[:10])
            )

        if not self.column_map:
            raise ValueError("No existen columnas comunes entre archivo oficial y tabla destino.")

        self.insercion["registros_preparados"] = len(self.df)
        return len(self.column_map), "Validación de encabezados vs SQL correcta."


    def _find_mapped_sql_col(self, variants: list[str]) -> str | None:
        wanted = {_normalize(v) for v in variants}
        for item in self.column_map:
            if _normalize(item["sql_col"]) in wanted or _normalize(item["file_col"]) in wanted:
                return item["sql_col"]
        sql_lookup = {_normalize(item["name"]): item["name"] for item in self.sql_columns_meta}
        for variant in variants:
            key = _normalize(variant)
            if key in sql_lookup:
                return sql_lookup[key]
        return None

    def _build_duplicate_where(self) -> tuple[str, list[Any], str]:
        parts = []
        params: list[Any] = []
        fecha_col = self._find_mapped_sql_col(["Fecha De Gestion", "Fecha_De_Gestion", "Fecha Gestion", "FechaGestion", "Fecha_Proceso", "FECHA_PROCESO"])
        mes_col = self._find_mapped_sql_col(["Mes_Gestion", "MES_GESTION"])
        origen_col = self._find_mapped_sql_col(["Origen_datos", "ORIGEN_DATOS", "Origen Datos"])
        if fecha_col:
            parts.append("COALESCE(" + f"TRY_CONVERT(date, {_sql_ident(fecha_col)}, 103), " + f"TRY_CONVERT(date, {_sql_ident(fecha_col)}, 120), " + f"TRY_CONVERT(date, {_sql_ident(fecha_col)})" + ") = ?")
            params.append(self.fecha["sql"])
        if mes_col:
            parts.append(f"CAST({_sql_ident(mes_col)} AS varchar(20)) = ?")
            params.append(self.mes_gestion)
        if origen_col:
            parts.append(f"LOWER(LTRIM(RTRIM(CAST({_sql_ident(origen_col)} AS varchar(100))))) = ?")
            params.append("integral")
        if not parts:
            raise ValueError("No se pudo construir criterio de duplicidad. La tabla debe tener Fecha De Gestion/Fecha_Proceso o Mes_Gestion/Origen_datos.")
        criterio = " AND ".join(parts)
        return criterio, params, f"Fecha={self.fecha['sql']} / Mes={self.mes_gestion} / Origen=integral"

    def _verificar_duplicidad(self):
        where, params, criterio_texto = self._build_duplicate_where()
        self.duplicidad["criterio"] = criterio_texto
        table = f"{_sql_ident(VENCORP_SCHEMA)}.{_sql_ident(VENCORP_TABLE)}"
        total = self.repo.scalar(f"SELECT COUNT_BIG(1) FROM {table} WHERE {where}", params)
        self.duplicidad["total"] = total
        self.duplicidad["existe"] = total > 0
        if total > 0:
            cols, muestra = self.repo.sample(f"SELECT TOP (3) * FROM {table} WHERE {where}", params)
            self.duplicidad["columnas"] = cols
            self.duplicidad["muestra"] = muestra
            return total, "Duplicidad detectada. Se muestran máximo 3 registros. No se insertó información."
        return 0, "Sin duplicidad en Vencorp_Integral."

    def _insertar(self):
        if self.duplicidad.get("existe"):
            raise ValueError("Hay duplicidad. Elimine los datos existentes antes de insertar.")
        insertados = self.repo.insert_dataframe(self.df, self.column_map)
        self.insercion["registros_insertados"] = insertados
        self.insercion["registros_rechazados"] = max(int(self.insercion["registros_preparados"]) - insertados, 0)
        return insertados, f"Insertado en {VENCORP_SCHEMA}.{VENCORP_TABLE}"

    def _validacion_final(self):
        where, params, _ = self._build_duplicate_where()
        table = f"{_sql_ident(VENCORP_SCHEMA)}.{_sql_ident(VENCORP_TABLE)}"
        total_bd = self.repo.scalar(f"SELECT COUNT_BIG(1) FROM {table} WHERE {where}", params)
        self.validacion_final = {
            "archivo_oficial": int(self.insercion["registros_archivo"]),
            "insertados": int(self.insercion["registros_insertados"]),
            "registros_bd": total_bd,
            "diferencia_archivo_vs_insertado": int(self.insercion["registros_archivo"]) - int(self.insercion["registros_insertados"]),
            "diferencia_insertado_vs_bd": int(self.insercion["registros_insertados"]) - total_bd,
        }
        if self.validacion_final["diferencia_archivo_vs_insertado"] != 0:
            self.advertencias.append("Diferencia entre archivo oficial e insertados.")
        if self.validacion_final["diferencia_insertado_vs_bd"] != 0:
            self.advertencias.append("Diferencia entre registros insertados y registros consultados en BD.")
        return total_bd, "Validación posterior realizada."

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()
        pasos = [
            ("INT-VEN-FILE", "Validar archivo oficial Fase H", "04_oficial", self._validar_archivo),
            ("INT-VEN-CONN", "Conectar a Vencorp_Integral", self.conexion.upper(), self._probar_conexion),
            ("INT-VEN-TABLE", "Validar tabla destino", f"{VENCORP_SCHEMA}.{VENCORP_TABLE}", self._validar_tabla),
            ("INT-VEN-COLS", "Validar encabezados archivo vs SQL", "match encabezados", self._validar_columnas),
            ("INT-VEN-DUP", "Verificar duplicidad", self.fecha["sql"], self._verificar_duplicidad),
        ]
        for codigo, paso, entrada, func in pasos:
            fila, warn = _step(codigo, paso, entrada, func)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)
                return self._build("Revisar", "Fase I detenida por observaciones. No se insertó información.", inicio_total, total_t0)
        if self.duplicidad.get("existe"):
            return self._build("Revisar", "Ya existen datos en Vencorp para el criterio indicado. No se insertó información.", inicio_total, total_t0)
        for codigo, paso, entrada, func in [
            ("INT-VEN-INS", "Insertar datos en Vencorp", f"{len(self.df)} registros", self._insertar),
            ("INT-VEN-VAL", "Validar conteos post inserción", self.mes_gestion, self._validacion_final),
        ]:
            fila, warn = _step(codigo, paso, entrada, func)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)
                return self._build("Revisar", "Fase I finalizada con observaciones.", inicio_total, total_t0)
        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "Carga a Vencorp_Integral finalizada. Cubo Excel en stand by."
        return self._build(estado, mensaje, inicio_total, total_t0)

    def _build(self, estado: str, mensaje: str, inicio_total: str, total_t0: float) -> dict[str, Any]:
        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)
        self.tiempos.append({"#": None, "Código": "INT-VEN-TOTAL", "Paso": "Total fase I", "Estado": estado, "Inicio": inicio_total, "Fin": fin_total, "Seg.": f"{total_seg:.2f}", "Entrada": f"{self.fecha['yyyymmdd']} / {self.mes_gestion}", "Salida": f"Insertados {self.insercion.get('registros_insertados', 0)} / Advertencias {len(self.advertencias)}", "Mensaje": mensaje})
        return {
            "codigo": "I",
            "titulo": "Vencorp / Cubo",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerar(self.tiempos),
            "advertencias": self.advertencias,
            "conexion": self.conexion_info,
            "archivo": self.archivo_info,
            "validacion_columnas": self.validacion_columnas,
            "duplicidad": self.duplicidad,
            "insercion": self.insercion,
            "cubo": self.cubo,
            "validacion_final": getattr(self, "validacion_final", {}),
            "detalle": {
                "conexion": self.conexion.upper(),
                "servidor": _cfg_vencorp(self.conexion).get("server"),
                "base": _cfg_vencorp(self.conexion).get("database"),
                "tabla": f"{VENCORP_SCHEMA}.{VENCORP_TABLE}",
                "fecha_sql": self.fecha["sql"],
                "fecha_visual": self.fecha["visual"],
                "mes_gestion": self.mes_gestion,
                "origen_datos": "integral",
                "archivo_oficial_csv": str(self.csv_oficial),
                "archivo_oficial_excel": str(self.xlsx_oficial),
            },
        }


class IntegralVencorpDeleteDuplicidadService:
    def __init__(self, form):
        self.base = IntegralVencorpService(form)

    def ejecutar(self) -> dict[str, Any]:
        inicio = _now()
        t0 = perf_counter()
        advertencias: list[str] = []
        try:
            self.base._validar_archivo()
            self.base._probar_conexion()
            self.base._validar_tabla()
            self.base._validar_columnas()
            where, params, criterio = self.base._build_duplicate_where()
            table = f"{_sql_ident(VENCORP_SCHEMA)}.{_sql_ident(VENCORP_TABLE)}"
            total_antes = self.base.repo.scalar(f"SELECT COUNT_BIG(1) FROM {table} WHERE {where}", params)
            eliminados = self.base.repo.execute(f"DELETE FROM {table} WHERE {where}", params)
            total_despues = self.base.repo.scalar(f"SELECT COUNT_BIG(1) FROM {table} WHERE {where}", params)
            estado = "Correcto"
            mensaje = "Datos existentes eliminados. Vuelva a ejecutar la Fase I."
        except Exception as exc:
            criterio = "-"
            total_antes = "-"
            eliminados = "-"
            total_despues = "-"
            estado = "Error"
            mensaje = str(exc)
            advertencias.append(mensaje)
        fin = _now()
        seg = round(perf_counter() - t0, 2)
        return {"estado": estado, "mensaje": mensaje, "tiempos": [{"#": 1, "Código": "INT-VEN-DEL-DUP", "Paso": "Eliminar duplicidad Fase I", "Estado": estado, "Inicio": inicio, "Fin": fin, "Seg.": f"{seg:.2f}", "Entrada": criterio, "Salida": f"Antes {total_antes} / Eliminados {eliminados} / Después {total_despues}", "Mensaje": mensaje}], "advertencias": advertencias}


def cargar_vencorp_integral_v2(form) -> dict[str, Any]:
    return IntegralVencorpService(form).ejecutar()


def eliminar_duplicidad_fase_i_integral_v2(form) -> dict[str, Any]:
    return IntegralVencorpDeleteDuplicidadService(form).ejecutar()
