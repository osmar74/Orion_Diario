# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from app.services.integral_connection_service import construir_contexto_integral_v2


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
        "mes_gestion": dt.strftime("%Y%m"),
    }


def _data_dir() -> Path:
    return Path(os.getenv("INTEGRAL_DATA_DIR") or os.getenv("DATA_DIR") or r"E:\data")


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


def _format_date_value(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    if raw.lower() in {"nan", "nat", "none", "null"}:
        return ""

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%d/%m/%Y")
        except Exception:
            pass

    try:
        dt = pd.to_datetime(raw, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return raw
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return raw


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


class IntegralOficialService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = self.contexto.get("conexion") or form.get("conexion") or "local"
        self.fecha = _fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.mes_gestion = str(form.get("mes_gestion") or self.contexto.get("mes_gestion") or self.fecha["mes_gestion"]).strip()
        if not re.fullmatch(r"\d{6}", self.mes_gestion):
            self.mes_gestion = self.fecha["mes_gestion"]

        self.base_dir = _data_dir() / self.fecha["yyyymmdd"] / "Integral"
        self.clean_dir = self.base_dir / "03_preventivo"
        self.oficial_dir = self.base_dir / "04_oficial"
        self.oficial_dir.mkdir(parents=True, exist_ok=True)

        self.csv_limpio = self.clean_dir / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.csv_oficial = self.oficial_dir / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.xlsx_oficial = self.oficial_dir / f"{self.fecha['yyyymmdd']}_Gestion_excel.xlsx"

        self.tiempos: list[dict[str, Any]] = []
        self.advertencias: list[str] = []
        self.transformaciones: list[dict[str, Any]] = []

    def _add_transformacion(self, regla: str, campo: str, antes: Any, despues: Any, accion: str, detalle: str = "") -> None:
        self.transformaciones.append({
            "regla": regla,
            "campo": campo,
            "antes": antes,
            "despues": despues,
            "accion": accion,
            "detalle": detalle,
        })

    def _leer_csv_limpio(self):
        if not self.csv_limpio.exists():
            raise FileNotFoundError(f"No existe CSV limpio de Fase G: {self.csv_limpio}")

        self.df = pd.read_csv(self.csv_limpio, dtype=str, encoding="utf-8-sig").fillna("")
        return len(self.df), f"Columnas: {len(self.df.columns)}"

    def _aplicar_transformaciones(self):
        df = self.df.copy()
        filas_antes = len(df)

        df["Actividad"] = "PREVENTIVO"
        df["Mes_Gestion"] = self.mes_gestion
        df["Origen_datos"] = "integral"

        self._add_transformacion(
            "Agregar Actividad",
            "Actividad",
            "No existía / valor previo",
            "PREVENTIVO",
            "Crear o reemplazar columna.",
            "Debe quedar en mayúsculas.",
        )
        self._add_transformacion(
            "Agregar Mes_Gestion",
            "Mes_Gestion",
            "No existía / valor previo",
            self.mes_gestion,
            "Crear o reemplazar columna.",
            "Formato YYYYMM de la fecha de proceso.",
        )
        self._add_transformacion(
            "Agregar Origen_datos",
            "Origen_datos",
            "No existía / valor previo",
            "integral",
            "Crear o reemplazar columna.",
            "Debe quedar en minúsculas.",
        )

        for variants, label in [
            (["Fecha De Gestion", "Fecha Gestion", "Fecha_De_Gestion"], "Fecha De Gestion"),
            (["Fecha_Compromiso", "Fecha Compromiso"], "Fecha_Compromiso"),
        ]:
            col = _find_col(df, variants)
            if col:
                no_vacias_antes = int((~_empty(df[col])).sum())
                df[col] = df[col].apply(_format_date_value)
                no_vacias_despues = int((~_empty(df[col])).sum())
                self._add_transformacion(
                    "Formato fecha DD/MM/YYYY",
                    col,
                    no_vacias_antes,
                    no_vacias_despues,
                    "Convertir formato de fecha.",
                    f"Columna normalizada para archivo oficial: {label}.",
                )
            else:
                self._add_transformacion(
                    "Formato fecha DD/MM/YYYY",
                    label,
                    "No encontrada",
                    "No aplicada",
                    "Sin cambios.",
                    "La columna no existe en el CSV limpio.",
                )

        cliente_col = _find_col(df, ["Cliente Nro.", "Cliente Nro", "Cliente_Nro"])
        if cliente_col:
            starts_m = df[cliente_col].astype(str).str.strip().str.upper().str.startswith("M")
            total_m = int(starts_m.sum())
            df.loc[starts_m, cliente_col] = df.loc[starts_m, cliente_col].astype(str).str.strip().str.replace(
                r"^[mM]+",
                "",
                regex=True,
            )

            empty_cliente = int(_empty(df[cliente_col]).sum())
            if empty_cliente:
                self.advertencias.append(f"Cliente Nro. vacío en archivo oficial: {empty_cliente} registros.")

            self._add_transformacion(
                "Quitar prefijo M",
                cliente_col,
                total_m,
                0,
                "Remover M inicial.",
                f"Cliente Nro. vacío posterior: {empty_cliente}.",
            )
        else:
            self.advertencias.append("No se encontró columna Cliente Nro. en CSV limpio.")
            self._add_transformacion(
                "Quitar prefijo M",
                "Cliente Nro.",
                "No encontrada",
                "No aplicada",
                "Sin cambios.",
                "No se encontró columna de cliente.",
            )

        self.df_oficial = df.fillna("")
        return len(self.df_oficial), f"Filas antes: {filas_antes}; filas oficiales: {len(self.df_oficial)}"

    def _guardar_csv(self):
        self.df_oficial.to_csv(self.csv_oficial, index=False, encoding="utf-8-sig")
        return self.csv_oficial.name, str(self.csv_oficial)

    def _guardar_excel(self):
        with pd.ExcelWriter(self.xlsx_oficial, engine="openpyxl") as writer:
            self.df_oficial.to_excel(writer, index=False, sheet_name="Gestion")
        return self.xlsx_oficial.name, str(self.xlsx_oficial)

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        for codigo, paso, entrada, func in [
            ("INT-OFI-READ", "Leer CSV limpio Fase G", str(self.csv_limpio), self._leer_csv_limpio),
            ("INT-OFI-TRF", "Aplicar transformaciones oficiales", self.fecha["yyyymmdd"], self._aplicar_transformaciones),
            ("INT-OFI-CSV", "Guardar CSV oficial", str(self.csv_oficial), self._guardar_csv),
            ("INT-OFI-XLSX", "Guardar Excel oficial", str(self.xlsx_oficial), self._guardar_excel),
        ]:
            if self.advertencias and codigo in {"INT-OFI-CSV", "INT-OFI-XLSX"} and not hasattr(self, "df_oficial"):
                continue

            fila, warn = _step(codigo, paso, entrada, func)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)
                break

        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)
        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "Archivo oficial generado." if estado == "Correcto" else "Archivo oficial generado con observaciones."

        self.tiempos.append({
            "#": None,
            "Código": "INT-OFI-TOTAL",
            "Paso": "Total fase H",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": self.fecha["yyyymmdd"],
            "Salida": f"Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })

        return {
            "codigo": "H",
            "titulo": "Generar archivo oficial",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerar(self.tiempos),
            "advertencias": self.advertencias,
            "transformaciones": self.transformaciones,
            "detalle": {
                "conexion": str(self.conexion).upper(),
                "fecha_proceso": self.fecha["yyyymmdd"],
                "mes_gestion": self.mes_gestion,
                "csv_limpio": str(self.csv_limpio),
                "csv_oficial": str(self.csv_oficial),
                "xlsx_oficial": str(self.xlsx_oficial),
                "filas": len(getattr(self, "df_oficial", [])) if hasattr(self, "df_oficial") else "-",
                "columnas": len(getattr(self, "df_oficial", pd.DataFrame()).columns) if hasattr(self, "df_oficial") else "-",
            },
        }


def generar_oficial_integral_v2(form) -> dict[str, Any]:
    return IntegralOficialService(form).ejecutar()
