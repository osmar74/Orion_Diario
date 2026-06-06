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

from app.services.integral_connection_service import construir_contexto_integral_v2, IntegralConnectionFactory


ROOT = Path(__file__).resolve().parents[2]


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


def _fecha_tokens(value: str) -> dict[str, str]:
    dt = _parse_fecha(value)
    return {
        "yyyymmdd": dt.strftime("%Y%m%d"),
        "sql": dt.strftime("%Y-%m-%d"),
        "visual": dt.strftime("%d/%m/%Y"),
    }


def _data_dir() -> Path:
    return Path(os.getenv("INTEGRAL_DATA_DIR") or os.getenv("DATA_DIR") or r"E:\data")


def _split_entidades(raw: str) -> list[str]:
    out = []
    seen = set()
    for item in str(raw or "").split(","):
        clean = item.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out


def _detect_tipo(form) -> str:
    raw = str(form.get("tipo_proceso") or form.get("tipo") or form.get("integral_tipo") or "discador").lower()
    return "manual" if "manual" in raw else "discador"


def _sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def _find_col(df: pd.DataFrame, variants: list[str]) -> str | None:
    lookup = {_normalize(c): c for c in df.columns}
    for variant in variants:
        key = _normalize(variant)
        if key in lookup:
            return lookup[key]
    return None


def _empty(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def _agreement(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({
        "acuerdo de pago",
        "acuerdo de pagos",
        "acuerdo pago",
    })


def _sql_path(tipo: str) -> Path:
    folders = [ROOT / "app" / "sql" / "integral"]
    names = (
        ["SQL-Para Integral MANUAL.txt", "fase_g_manual.sql"]
        if tipo == "manual"
        else ["SQL-Para Integral DISCADOR.txt", "fase_g_discador.sql"]
    )
    for folder in folders:
        for name in names:
            path = folder / name
            if path.exists():
                return path
    raise FileNotFoundError(f"No se encontró SQL para {tipo} en app/sql/integral.")


def _render_sql(raw: str, fecha_sql: str, entidades: list[str]) -> str:
    entidades_csv = ",".join(entidades)
    entidades_sql = ", ".join(_sql_quote(e) for e in entidades) if entidades else "''"
    sql = raw.replace("{fecha_sql}", fecha_sql)
    sql = sql.replace("{FECHA_SQL}", fecha_sql)
    sql = sql.replace("{entidades_csv}", entidades_csv)
    sql = sql.replace("{ENTIDADES_CSV}", entidades_csv)
    sql = sql.replace("{entidades_sql}", entidades_sql)
    sql = sql.replace("{ENTIDADES_SQL}", entidades_sql)
    sql = re.sub(r"(DECLARE\s+@FechaFiltro\s+DATE\s*=\s*)'[^']*'", rf"\1'{fecha_sql}'", sql, flags=re.I)
    sql = re.sub(r"(DECLARE\s+@Fecha\s+DATE\s*=\s*)'[^']*'", rf"\1'{fecha_sql}'", sql, flags=re.I)
    sql = re.sub(r"(DECLARE\s+@EntidadesLista\s+NVARCHAR\s*\(\s*MAX\s*\)\s*=\s*)'[^']*'", rf"\1'{entidades_csv}'", sql, flags=re.I)
    return sql


def _split_go(sql: str) -> list[str]:
    return [part.strip() for part in re.split(r"^\s*GO\s*;?\s*$", sql, flags=re.I | re.M) if part.strip()]


def _safe_cell(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


class SqlResultExecutor:
    def __init__(self, conexion: str):
        self.conexion = conexion

    def execute_dataframe(self, sql: str) -> pd.DataFrame:
        last_cols: list[str] = []
        last_rows: list[tuple] = []

        with IntegralConnectionFactory.connect_destino(self.conexion) as conn:
            cur = conn.cursor()

            for statement in _split_go(sql):
                cur.execute(statement)

                while True:
                    if cur.description:
                        last_cols = [col[0] for col in cur.description]
                        fetched = cur.fetchall()
                        last_rows = [tuple(_safe_cell(v) for v in row) for row in fetched]

                    try:
                        has_next = cur.nextset()
                    except Exception:
                        has_next = False

                    if not has_next:
                        break

            conn.commit()

        if not last_cols:
            return pd.DataFrame()

        return pd.DataFrame(last_rows, columns=last_cols)


# === Fase G: resumen tabular de limpieza aplicada ===

def _col_or_none(df: pd.DataFrame, variants: list[str]) -> str | None:
    if df is None or df.empty:
        return None
    return _find_col(df, variants)


def _count_non_empty(df: pd.DataFrame, col: str | None) -> int:
    if not col or col not in df.columns:
        return 0
    return int((~_empty(df[col])).sum())


def _count_empty(df: pd.DataFrame, col: str | None) -> int:
    if not col or col not in df.columns:
        return 0
    return int(_empty(df[col]).sum())


def _count_total_null_cells(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    return int(df.isna().sum().sum())


def _count_total_blank_cells(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    normalized = df.where(pd.notna(df), "")
    return int((normalized.astype(str).apply(lambda col: col.str.strip() == "")).sum().sum())


def construir_resumen_limpieza_integral_v2(tipo: str, df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> list[dict[str, Any]]:
    # Construye una tabla de auditoría de limpieza para mostrar en pantalla.
    # Esta función no vuelve a limpiar datos; compara crudo contra limpio.

    tipo = str(tipo or "discador").lower()
    resumen: list[dict[str, Any]] = []

    def add(regla: str, campo: str, antes: Any, despues: Any, accion: str, detalle: str = "") -> None:
        resumen.append({
            "regla": regla,
            "campo": campo,
            "antes": antes,
            "despues": despues,
            "accion": accion,
            "detalle": detalle,
        })

    raw_rows = len(df_raw) if df_raw is not None else 0
    clean_rows = len(df_clean) if df_clean is not None else 0

    add(
        "Cantidad de registros",
        "archivo completo",
        raw_rows,
        clean_rows,
        "Control de registros",
        f"Registros eliminados por reglas válidas: {max(raw_rows - clean_rows, 0)}",
    )

    add(
        "Celdas nulas / vacías",
        "todas las columnas",
        _count_total_null_cells(df_raw),
        _count_total_blank_cells(df_clean),
        "Nulos convertidos a vacío",
        "No se eliminan registros por nulos generales.",
    )

    desc_col_raw = _col_or_none(df_raw, [
        "Descripcion Codigo De Gestion",
        "Descripción Código De Gestión",
        "Desc_Gestion",
    ])
    desc_col_clean = _col_or_none(df_clean, [
        "Descripcion Codigo De Gestion",
        "Descripción Código De Gestión",
        "Desc_Gestion",
    ])

    fecha_col_raw = _col_or_none(df_raw, ["Fecha_Compromiso", "Fecha Compromiso"])
    fecha_col_clean = _col_or_none(df_clean, ["Fecha_Compromiso", "Fecha Compromiso"])

    if desc_col_raw and fecha_col_raw:
        agreement_raw = _agreement(df_raw[desc_col_raw])
        fecha_empty_raw = _empty(df_raw[fecha_col_raw])
        fecha_no_empty_raw = ~fecha_empty_raw

        compromiso_fuera_acuerdo_raw = int(((~agreement_raw) & fecha_no_empty_raw).sum())
        acuerdo_sin_fecha_raw = int((agreement_raw & fecha_empty_raw).sum())
    else:
        compromiso_fuera_acuerdo_raw = 0
        acuerdo_sin_fecha_raw = 0

    if desc_col_clean and fecha_col_clean:
        agreement_clean = _agreement(df_clean[desc_col_clean])
        fecha_empty_clean = _empty(df_clean[fecha_col_clean])
        fecha_no_empty_clean = ~fecha_empty_clean
        compromiso_fuera_acuerdo_clean = int(((~agreement_clean) & fecha_no_empty_clean).sum())
        no_hubo_acuerdo_clean = int(
            df_clean[desc_col_clean].astype(str).str.strip().str.lower().eq("no hubo acuerdo").sum()
        )
    else:
        compromiso_fuera_acuerdo_clean = 0
        no_hubo_acuerdo_clean = 0

    add(
        "Fecha compromiso solo con Acuerdo de Pago",
        fecha_col_raw or fecha_col_clean or "Fecha_Compromiso",
        compromiso_fuera_acuerdo_raw,
        compromiso_fuera_acuerdo_clean,
        "Se vacía Fecha_Compromiso cuando no corresponde.",
        "Solo debe quedar fecha cuando la gestión es Acuerdo de Pago.",
    )

    add(
        "Acuerdo de Pago sin fecha",
        desc_col_raw or desc_col_clean or "Descripcion Codigo De Gestion",
        acuerdo_sin_fecha_raw,
        no_hubo_acuerdo_clean,
        "Se cambia a No Hubo Acuerdo.",
        "Aplica cuando Descripcion Codigo De Gestion es Acuerdo de Pago y Fecha_Compromiso está vacía.",
    )

    tipo_cartera_raw = _col_or_none(df_raw, ["Tipo Cartera"])
    tipo_cartera_clean = _col_or_none(df_clean, ["Tipo Cartera"])

    home_raw = 0
    home_clean = 0

    if tipo_cartera_raw:
        home_raw = int(df_raw[tipo_cartera_raw].astype(str).str.strip().str.lower().eq("home").sum())

    if tipo_cartera_clean:
        home_clean = int(df_clean[tipo_cartera_clean].astype(str).str.strip().str.lower().eq("home").sum())

    add(
        "Tipo Cartera Home",
        tipo_cartera_raw or tipo_cartera_clean or "Tipo Cartera",
        home_raw,
        home_clean,
        "Reemplazar Home por vacío.",
        "Regla común para Discador y Manual.",
    )

    antig_raw = _col_or_none(df_raw, ["Antiguedad De La Cartera", "Antigüedad De La Cartera"])
    antig_clean = _col_or_none(df_clean, ["Antiguedad De La Cartera", "Antigüedad De La Cartera"])

    add(
        "Antigüedad de la cartera",
        antig_raw or antig_clean or "Antiguedad De La Cartera",
        _count_non_empty(df_raw, antig_raw),
        _count_non_empty(df_clean, antig_clean),
        "Vaciar todos los registros.",
        "Regla común para Discador y Manual.",
    )

    cliente_raw = _col_or_none(df_raw, ["Cliente Nro.", "Cliente Nro", "Cliente_Nro"])
    cliente_clean = _col_or_none(df_clean, ["Cliente Nro.", "Cliente Nro", "Cliente_Nro"])

    add(
        "Cliente Nro. vacío",
        cliente_raw or cliente_clean or "Cliente Nro.",
        _count_empty(df_raw, cliente_raw),
        _count_empty(df_clean, cliente_clean),
        "Reportar y avisar.",
        "No se eliminan registros por Cliente Nro. vacío; se informa en reporte.",
    )

    if tipo == "manual":
        tel_raw = _col_or_none(df_raw, ["Telefono", "Telefonos", "Teléfono", "Teléfonos"])
        tel2_raw = _col_or_none(df_raw, ["Telefono_2", "Telefonos_2", "Teléfono_2", "Teléfonos_2"])
        tel_clean = _col_or_none(df_clean, ["Telefono", "Telefonos", "Teléfono", "Teléfonos"])

        add(
            "Columnas de teléfono Manual",
            "Telefono / Telefono_2",
            f"Telefono={'Sí' if tel_raw else 'No'}; Telefono_2={'Sí' if tel2_raw else 'No'}",
            f"Telefono final={'Sí' if tel_clean else 'No'}",
            "Si existen ambas, eliminar Telefono y renombrar Telefono_2.",
            "Regla específica para Manual.",
        )
    else:
        phone_raw = _col_or_none(df_raw, ["Telefonos", "Telefono", "Teléfonos", "Teléfono"])
        phone_clean = _col_or_none(df_clean, ["Telefonos", "Telefono", "Teléfonos", "Teléfono"])

        add(
            "Telefono/Telefonos vacío",
            phone_raw or phone_clean or "Telefonos",
            _count_empty(df_raw, phone_raw),
            _count_empty(df_clean, phone_clean),
            "Eliminar registros con teléfono vacío.",
            f"Registros eliminados: {max(raw_rows - clean_rows, 0)}",
        )

    return resumen


class IntegralCleaner:
    def __init__(self, tipo: str):
        self.tipo = tipo
        self.reportes: list[dict[str, Any]] = []
        self.advertencias: list[str] = []

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.where(pd.notna(df), "")

        desc_col = _find_col(df, [
            "Descripcion Codigo De Gestion",
            "Descripción Código De Gestión",
            "Desc_Gestion",
        ])
        fecha_col = _find_col(df, ["Fecha_Compromiso", "Fecha Compromiso"])
        tipo_cartera_col = _find_col(df, ["Tipo Cartera"])
        antiguedad_col = _find_col(df, ["Antiguedad De La Cartera", "Antigüedad De La Cartera"])
        cliente_col = _find_col(df, ["Cliente Nro.", "Cliente Nro", "Cliente_Nro"])

        if desc_col and fecha_col:
            agreement = _agreement(df[desc_col])
            empty_fecha = _empty(df[fecha_col])
            df.loc[~agreement, fecha_col] = ""
            df.loc[agreement & empty_fecha, desc_col] = "No Hubo Acuerdo"
            df.loc[agreement & empty_fecha, fecha_col] = ""

        if tipo_cartera_col:
            df[tipo_cartera_col] = df[tipo_cartera_col].astype(str).replace(
                to_replace=r"^\s*Home\s*$",
                value="",
                regex=True,
            )

        if antiguedad_col:
            df[antiguedad_col] = ""

        if cliente_col:
            empty_cliente = _empty(df[cliente_col])
            count = int(empty_cliente.sum())
            if count:
                self.reportes.append({
                    "regla": "Cliente Nro. vacío",
                    "cantidad": count,
                    "accion": "Avisar. No se eliminaron registros.",
                    "muestra": df.loc[empty_cliente].head(3).to_dict(orient="records"),
                })
                self.advertencias.append(f"Cliente Nro. vacío: {count} registros.")

        if self.tipo == "manual":
            df = self._manual(df)
        else:
            df = self._discador(df)

        return df.where(pd.notna(df), "")

    def _discador(self, df: pd.DataFrame) -> pd.DataFrame:
        phone_col = _find_col(df, ["Telefonos", "Telefono", "Teléfonos", "Teléfono"])
        if not phone_col:
            self.advertencias.append("No se encontró columna Telefono/Telefonos para Discador.")
            return df

        empty_phone = _empty(df[phone_col])
        count = int(empty_phone.sum())
        if count:
            df = df.loc[~empty_phone].copy()
            self.reportes.append({
                "regla": "Telefono/Telefonos vacío",
                "cantidad": count,
                "accion": "Registros eliminados.",
                "muestra": [],
            })
        return df

    def _manual(self, df: pd.DataFrame) -> pd.DataFrame:
        tel = _find_col(df, ["Telefono", "Telefonos"])
        tel2 = _find_col(df, ["Telefono_2", "Telefonos_2", "Teléfonos_2"])
        if tel and tel2:
            df = df.drop(columns=[tel])
            df = df.rename(columns={tel2: "Telefono"})
            self.reportes.append({
                "regla": "Telefono y Telefono_2",
                "cantidad": 1,
                "accion": "Se eliminó Telefono y se renombró Telefono_2 a Telefono.",
                "muestra": [],
            })
        elif tel2 and not tel:
            df = df.rename(columns={tel2: "Telefono"})
        return df


class IntegralSqlLimpiezaService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = self.contexto.get("conexion") or form.get("conexion") or "local"
        self.fecha = _fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.tipo = _detect_tipo(form)
        self.entidades = _split_entidades(form.get("entidades_csv") or "")
        self.base_dir = _data_dir() / self.fecha["yyyymmdd"] / "Integral"
        self.tmp_dir = self.base_dir / "07_temporal"
        self.out_dir = self.base_dir / "03_preventivo"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.tiempos: list[dict[str, Any]] = []
        self.advertencias: list[str] = []
        self.reportes: list[dict[str, Any]] = []

    def _step(self, codigo: str, paso: str, entrada: Any, func):
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
        self.tiempos.append({
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
        })
        if warn:
            self.advertencias.append(warn)

    def _prepare_sql(self):
        self.sql_source_path = _sql_path(self.tipo)
        raw = self.sql_source_path.read_text(encoding="utf-8", errors="ignore")
        self.sql_rendered = _render_sql(raw, self.fecha["sql"], self.entidades)
        self.sql_rendered_path = self.tmp_dir / f"{self.fecha['yyyymmdd']}_fase_g_{self.tipo}_rendered.sql"
        self.sql_rendered_path.write_text(self.sql_rendered, encoding="utf-8")
        return self.sql_source_path.name, f"SQL renderizado: {self.sql_rendered_path}"

    def _execute_sql(self):
        self.df_raw = SqlResultExecutor(self.conexion).execute_dataframe(self.sql_rendered)
        if self.df_raw.empty:
            self.advertencias.append(
                "SQL ejecutado correctamente, pero no devolvió filas. Revise fecha, entidades, Fase E/F y SQL renderizado."
            )
        return len(self.df_raw), f"Columnas resultado: {len(self.df_raw.columns)}"

    def _export_raw(self):
        self.raw_path = self.tmp_dir / f"{self.fecha['yyyymmdd']}_Gestion_raw.csv"
        self.df_raw.to_csv(self.raw_path, index=False, encoding="utf-8-sig")
        return self.raw_path.name, str(self.raw_path)

    def _clean(self):
        cleaner = IntegralCleaner(self.tipo)
        self.df_clean = cleaner.clean(self.df_raw)

        # Tabla de auditoría visual de limpieza aplicada.
        self.resumen_limpieza = construir_resumen_limpieza_integral_v2(
            self.tipo,
            self.df_raw,
            self.df_clean,
        )

        self.reportes.extend(cleaner.reportes)
        self.advertencias.extend(cleaner.advertencias)
        return len(self.df_clean), f"Columnas limpias: {len(self.df_clean.columns)}"

    def _export_clean(self):
        self.clean_path = self.out_dir / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.df_clean.to_csv(self.clean_path, index=False, encoding="utf-8-sig")
        return self.clean_path.name, str(self.clean_path)

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        self._step("INT-SQL-PREP", "Preparar SQL externo", self.tipo.upper(), self._prepare_sql)

        if not self.advertencias:
            self._step("INT-SQL-EXEC", "Ejecutar SQL", "Aster_Integral_Api", self._execute_sql)

        if not self.advertencias or hasattr(self, "df_raw"):
            self._step("INT-SQL-RAW", "Exportar resultado crudo", "CSV temporal", self._export_raw)

        if not self.advertencias and hasattr(self, "df_raw"):
            self._step("INT-SQL-CLEAN", "Aplicar limpieza", self.tipo.upper(), self._clean)

        if not self.advertencias and hasattr(self, "df_clean"):
            self._step("INT-SQL-CSV", "Guardar CSV limpio", "03_preventivo", self._export_clean)

        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)
        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "SQL y limpieza finalizados." if estado == "Correcto" else "SQL y limpieza finalizados con observaciones."

        self.tiempos.append({
            "#": None,
            "Código": "INT-SQL-TOTAL",
            "Paso": "Total fase G",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": f"{self.tipo.upper()} / {self.fecha['sql']}",
            "Salida": f"Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })

        for i, row in enumerate(self.tiempos, start=1):
            row["#"] = i

        return {
            "codigo": "G",
            "titulo": "SQL + Limpieza",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "registros_entrada": len(getattr(self, "df_raw", [])) if hasattr(self, "df_raw") else "-",
            "registros_salida": len(getattr(self, "df_clean", [])) if hasattr(self, "df_clean") else "-",
            "tiempos": self.tiempos,
            "advertencias": self.advertencias,
            "reportes": self.reportes,
            "resumen_limpieza": getattr(self, "resumen_limpieza", []),
            "detalle": {
                "conexion": str(self.conexion).upper(),
                "tipo": self.tipo.upper(),
                "fecha_sql": self.fecha["sql"],
                "entidades": len(self.entidades),
                "sql_usado": str(getattr(self, "sql_source_path", "")),
                "sql_renderizado": str(getattr(self, "sql_rendered_path", "")),
                "csv_crudo": str(getattr(self, "raw_path", "")),
                "csv_limpio": str(getattr(self, "clean_path", "")),
            },
        }


def ejecutar_sql_limpieza_integral_v2(form) -> dict[str, Any]:
    return IntegralSqlLimpiezaService(form).ejecutar()
