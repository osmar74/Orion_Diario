# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from app.services.integral_connection_service import construir_contexto_integral_v2
from app.services.integral_v2_vencorp_service import VencorpRepo, VENCORP_SCHEMA, VENCORP_TABLE


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "app" / "config" / "configuracion_global.json"


MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


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
        "mes_nombre": MESES_ES[dt.month],
        "yy": dt.strftime("%y"),
        "yyyy": dt.strftime("%Y"),
    }


def _data_dir() -> Path:
    return Path(os.getenv("INTEGRAL_DATA_DIR") or os.getenv("DATA_DIR") or r"E:\data")


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def _format_value(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None:
        return ""
    return str(value)


def _file_info(path: Path) -> dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "ruta": str(path),
        "existe": exists,
        "tamano_bytes": int(stat.st_size) if stat else 0,
        "modificado": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S") if stat else "-",
    }


def _read_csv_count(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    return len(df), len(df.columns)


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


class IntegralValidacionFinalService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = _normalizar_conexion(self.contexto.get("conexion") or form.get("conexion") or "local")
        self.fecha = _fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.mes_gestion = str(form.get("mes_gestion") or self.contexto.get("mes_gestion") or self.fecha["mes_gestion"]).strip()
        if not re.fullmatch(r"\d{6}", self.mes_gestion):
            self.mes_gestion = self.fecha["mes_gestion"]

        self.tipo_proceso = str(form.get("tipo_proceso") or form.get("tipo") or "discador").strip().lower()
        self.subcarpeta_integral = "Churn" if "manual" in self.tipo_proceso else "Preventivo"

        self.base_dir = _data_dir() / self.fecha["yyyymmdd"] / "Integral"
        self.consolidado_dir = _data_dir() / self.fecha["yyyymmdd"] / "Consolidado" / "Gestion" / "04_compromiso"

        self.clean_csv = self.base_dir / "03_preventivo" / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.official_csv = self.base_dir / "04_oficial" / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.official_xlsx = self.base_dir / "04_oficial" / f"{self.fecha['yyyymmdd']}_Gestion_excel.xlsx"
        self.raw_csv = self.base_dir / "07_temporal" / f"{self.fecha['yyyymmdd']}_Gestion_raw.csv"
        self.consolidado_csv = self.consolidado_dir / f"{self.fecha['yyyymmdd']}_Gestion.csv"
        self.final_dir = self.base_dir / "06_final"

        self.tiempos: list[dict[str, Any]] = []
        self.advertencias: list[str] = []
        self.archivos: list[dict[str, Any]] = []
        self.rutas_copia: list[dict[str, Any]] = []
        self.copias: list[dict[str, Any]] = []
        self.validacion_vencorp: dict[str, Any] = {}
        self.manifiesto: dict[str, Any] = {}
        self.cubo: dict[str, str] = {
            "estado": "Stand by",
            "mensaje": "Actualización del cubo Excel suspendida hasta nuevo aviso.",
        }

    def _config_rutas(self) -> dict[str, str]:
        defaults = {
            "local": {
                "integral_procesado": r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_integral\Cobranzas Integrales Procesado",
                "cobranza_base": r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_integral",
            },
            "remoto": {
                "integral_procesado": r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Cobranzas Integrales Procesado",
                "cobranza_base": r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip",
            },
        }

        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                rutas = data.get("integral_diario_v2", {}).get("rutas_copia", {})
                selected = rutas.get(self.conexion, {})
                return {
                    "integral_procesado": selected.get("integral_procesado") or defaults[self.conexion]["integral_procesado"],
                    "cobranza_base": selected.get("cobranza_base") or defaults[self.conexion]["cobranza_base"],
                }
            except Exception:
                pass

        return defaults[self.conexion]

    def _add_check(self, grupo: str, nombre: str, ruta: Path, existe: bool, accion: str, detalle: str = "") -> None:
        self.rutas_copia.append({
            "grupo": grupo,
            "nombre": nombre,
            "ruta": str(ruta),
            "existe": bool(existe),
            "estado": "Correcto" if existe else "No existe",
            "accion": accion,
            "detalle": detalle,
        })

    def _validar_archivos(self):
        targets = [
            ("CSV limpio Fase G", self.clean_csv, "Referencia"),
            ("CSV oficial Fase H", self.official_csv, "Obligatorio"),
            ("Excel oficial Fase H", self.official_xlsx, "Obligatorio"),
            ("CSV crudo temporal", self.raw_csv, "Referencia"),
            ("CSV Cobranza % Consolidado", self.consolidado_csv, "Para copia b) SDD"),
        ]

        self.archivos = []
        faltantes_obligatorios = []

        for nombre, path, tipo in targets:
            info = _file_info(path)
            registros, columnas = _read_csv_count(path) if path.suffix.lower() == ".csv" and info["existe"] else (0, 0)
            item = {
                "nombre": nombre,
                "tipo": tipo,
                "ruta": info["ruta"],
                "existe": info["existe"],
                "tamano_bytes": info["tamano_bytes"],
                "modificado": info["modificado"],
                "registros": registros,
                "columnas": columnas,
            }
            self.archivos.append(item)

            if tipo == "Obligatorio" and not info["existe"]:
                faltantes_obligatorios.append(nombre)

        if faltantes_obligatorios:
            raise FileNotFoundError("Faltan archivos obligatorios: " + ", ".join(faltantes_obligatorios))

        return len(self.archivos), "Archivos principales validados."

    def _validar_vencorp(self):
        repo = VencorpRepo(self.conexion)
        meta = repo.columns_metadata()
        lookup = {_normalize(item["name"]): item["name"] for item in meta}

        def col(*names: str) -> str | None:
            for name in names:
                key = _normalize(name)
                if key in lookup:
                    return lookup[key]
            return None

        fecha_col = col("Fecha_De_Gestion", "Fecha De Gestion", "FechaGestion", "Fecha_Proceso")
        mes_col = col("Mes_Gestion", "MES_GESTION")
        origen_col = col("Origen_datos", "origen_datos", "ORIGEN_DATOS")

        where_parts = []
        params = []

        if fecha_col:
            where_parts.append(
                "COALESCE("
                f"TRY_CONVERT(date, [{fecha_col}], 103), "
                f"TRY_CONVERT(date, [{fecha_col}], 120), "
                f"TRY_CONVERT(date, [{fecha_col}])"
                ") = ?"
            )
            params.append(self.fecha["sql"])

        if mes_col:
            where_parts.append(f"CAST([{mes_col}] AS varchar(20)) = ?")
            params.append(self.mes_gestion)

        if origen_col:
            where_parts.append(f"LOWER(LTRIM(RTRIM(CAST([{origen_col}] AS varchar(100))))) = ?")
            params.append("integral")

        if not where_parts:
            raise ValueError("No se pudo construir criterio de validación Vencorp.")

        official_rows, official_cols = _read_csv_count(self.official_csv)

        table = f"[{VENCORP_SCHEMA}].[{VENCORP_TABLE}]"
        total_bd = repo.scalar(f"SELECT COUNT_BIG(1) FROM {table} WHERE {' AND '.join(where_parts)}", params)

        diferencia = int(official_rows) - int(total_bd)

        self.validacion_vencorp = {
            "tabla": f"{VENCORP_SCHEMA}.{VENCORP_TABLE}",
            "criterio": f"Fecha={self.fecha['sql']} / Mes={self.mes_gestion} / Origen=integral",
            "archivo_oficial": official_rows,
            "columnas_archivo": official_cols,
            "registros_bd": total_bd,
            "diferencia": diferencia,
            "estado": "Correcto" if diferencia == 0 and official_rows > 0 else "Revisar",
        }

        if diferencia != 0:
            self.advertencias.append("Diferencia entre CSV oficial y registros en Vencorp_Integral.")

        return total_bd, f"Diferencia: {diferencia}"

    def _validar_rutas_copia(self):
        cfg = self._config_rutas()

        base_procesado = Path(cfg["integral_procesado"])
        carpeta_mes = f"{self.fecha['mes_nombre']}_{self.mes_gestion}"
        destino_integral_dir = base_procesado / carpeta_mes / self.subcarpeta_integral

        base_cobranza = Path(cfg["cobranza_base"])
        carpeta_microvoz = f"Microvoz_{self.fecha['mes_nombre']}_{self.fecha['yy']}"
        destino_cobranza_dir = base_cobranza / carpeta_microvoz

        self.destino_integral_dir = destino_integral_dir
        self.destino_cobranza_dir = destino_cobranza_dir

        self.destino_integral_csv = destino_integral_dir / self.official_csv.name
        self.destino_cobranza_csv = destino_cobranza_dir / self.consolidado_csv.name

        self._add_check("Archivo origen a)", "CSV oficial Integral", self.official_csv, self.official_csv.exists(), "Copiar", "YYYYMMDD_Gestion.csv desde Integral\\04_oficial.")
        self._add_check("Destino a)", "Base Cobranzas Integrales Procesado", base_procesado, base_procesado.exists(), "Validar", "Ruta base del SDD para archivo oficial Integral.")
        self._add_check("Destino a)", f"Carpeta mes {carpeta_mes}", base_procesado / carpeta_mes, (base_procesado / carpeta_mes).exists(), "Buscar", "Formato: Abril_YYYYMM.")
        self._add_check("Destino a)", f"Subcarpeta {self.subcarpeta_integral}", destino_integral_dir, destino_integral_dir.exists(), "Copiar aquí", "Preventivo para Integral/Discador; Churn para Manual.")

        self._add_check("Archivo origen b)", "CSV Cobranza % Consolidado", self.consolidado_csv, self.consolidado_csv.exists(), "Copiar", "YYYYMMDD_Gestion.csv desde Consolidado\\Gestion\\04_compromiso.")
        self._add_check("Destino b)", "Base Cobranza %", base_cobranza, base_cobranza.exists(), "Validar", "Ruta base del SDD para Microvoz_MM_YY.")

        if base_cobranza.exists() and not destino_cobranza_dir.exists():
            try:
                destino_cobranza_dir.mkdir(parents=True, exist_ok=True)
                detalle = "No existía; fue creada según SDD."
            except Exception as exc:
                detalle = f"No se pudo crear: {exc}"
        else:
            detalle = "Ya existía." if destino_cobranza_dir.exists() else "No se puede crear porque no existe la base."

        self._add_check("Destino b)", f"Carpeta {carpeta_microvoz}", destino_cobranza_dir, destino_cobranza_dir.exists(), "Crear si no existe", detalle)

        faltantes = [x for x in self.rutas_copia if not x["existe"]]
        if faltantes:
            self.advertencias.append("Existen rutas o archivos de copia no disponibles. Revise checks en rojo.")

        return len(self.rutas_copia), f"Checks con observación: {len(faltantes)}"

    def _copy_file(self, origen: Path, destino: Path, descripcion: str, obligatorio: bool = True) -> None:
        item = {
            "descripcion": descripcion,
            "origen": str(origen),
            "destino": str(destino),
            "copiado": False,
            "estado": "No copiado",
            "detalle": "",
        }

        if not origen.exists():
            item["detalle"] = "No existe archivo origen."
            self.copias.append(item)
            if obligatorio:
                self.advertencias.append(f"No se pudo copiar {descripcion}: no existe origen.")
            return

        if not destino.parent.exists():
            item["detalle"] = "No existe carpeta destino."
            self.copias.append(item)
            if obligatorio:
                self.advertencias.append(f"No se pudo copiar {descripcion}: no existe destino.")
            return

        shutil.copy2(origen, destino)
        item["copiado"] = True
        item["estado"] = "Copiado"
        item["detalle"] = "Copia realizada correctamente."
        self.copias.append(item)

    def _copiar_archivos(self):
        self.final_dir.mkdir(parents=True, exist_ok=True)

        self._copy_file(self.official_csv, self.destino_integral_csv, "a) CSV oficial Integral hacia Cobranzas Integrales Procesado", obligatorio=True)
        self._copy_file(self.consolidado_csv, self.destino_cobranza_csv, "b) CSV Cobranza % hacia Microvoz_MM_YY", obligatorio=False)

        # Carpeta final local del proceso.
        self._copy_file(self.official_csv, self.final_dir / self.official_csv.name, "Copia local final CSV oficial", obligatorio=True)
        self._copy_file(self.official_xlsx, self.final_dir / self.official_xlsx.name, "Copia local final Excel oficial", obligatorio=True)

        copiadas = sum(1 for x in self.copias if x["copiado"])
        return copiadas, f"Copias realizadas: {copiadas}/{len(self.copias)}"

    def _generar_manifiesto(self):
        self.final_dir.mkdir(parents=True, exist_ok=True)
        path = self.final_dir / f"{self.fecha['yyyymmdd']}_manifest_integral.json"

        self.manifiesto = {
            "fecha_proceso": self.fecha["yyyymmdd"],
            "fecha_sql": self.fecha["sql"],
            "fecha_visual": self.fecha["visual"],
            "mes_gestion": self.mes_gestion,
            "conexion": self.conexion,
            "tipo_proceso": self.tipo_proceso,
            "tabla_vencorp": f"{VENCORP_SCHEMA}.{VENCORP_TABLE}",
            "validacion_vencorp": self.validacion_vencorp,
            "archivos": self.archivos,
            "rutas_copia": self.rutas_copia,
            "copias": self.copias,
            "cubo": self.cubo,
            "advertencias": self.advertencias,
            "generado_en": datetime.now().isoformat(timespec="seconds"),
        }

        path.write_text(json.dumps(self.manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")
        self.manifiesto_path = path

        return path.name, str(path)

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        pasos = [
            ("INT-FIN-FILE", "Validar archivos generados", self.fecha["yyyymmdd"], self._validar_archivos),
            ("INT-FIN-BD", "Validar conteos Vencorp_Integral", self.mes_gestion, self._validar_vencorp),
            ("INT-FIN-RUTAS", "Validar rutas de copia", self.conexion.upper(), self._validar_rutas_copia),
            ("INT-FIN-COPY", "Copiar archivos finales", "SDD punto 7", self._copiar_archivos),
            ("INT-FIN-MAN", "Generar manifiesto final", "06_final", self._generar_manifiesto),
        ]

        for codigo, paso, entrada, func in pasos:
            fila, warn = _step(codigo, paso, entrada, func)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)
                break

        estado = "Correcto"
        mensaje = "Proceso Integral validado y cerrado. Cubo Excel en stand by."

        if self.advertencias or self.validacion_vencorp.get("estado") == "Revisar":
            estado = "Revisar"
            mensaje = "Validación final terminada con observaciones. Revise checks en rojo y advertencias."

        return self._build(estado, mensaje, inicio_total, total_t0)

    def _build(self, estado: str, mensaje: str, inicio_total: str, total_t0: float) -> dict[str, Any]:
        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)

        self.tiempos.append({
            "#": None,
            "Código": "INT-FIN-TOTAL",
            "Paso": "Total fase J",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": f"{self.fecha['yyyymmdd']} / {self.mes_gestion}",
            "Salida": f"Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })

        return {
            "codigo": "J",
            "titulo": "Validación final",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerar(self.tiempos),
            "advertencias": self.advertencias,
            "archivos": self.archivos,
            "rutas_copia": self.rutas_copia,
            "copias": self.copias,
            "validacion_vencorp": self.validacion_vencorp,
            "cubo": self.cubo,
            "manifiesto": {
                "ruta": str(getattr(self, "manifiesto_path", "")),
                "existe": bool(getattr(self, "manifiesto_path", Path()).exists()) if hasattr(self, "manifiesto_path") else False,
            },
            "detalle": {
                "conexion": self.conexion.upper(),
                "fecha_proceso": self.fecha["yyyymmdd"],
                "fecha_sql": self.fecha["sql"],
                "fecha_visual": self.fecha["visual"],
                "mes_gestion": self.mes_gestion,
                "mes_nombre": self.fecha["mes_nombre"],
                "tipo_proceso": self.tipo_proceso,
                "subcarpeta_integral": self.subcarpeta_integral,
                "final_dir": str(self.final_dir),
            },
        }


def validar_final_integral_v2(form) -> dict[str, Any]:
    return IntegralValidacionFinalService(form).ejecutar()
