# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.services.integral_connection_service import construir_contexto_integral_v2


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
    }


def _data_dir() -> Path:
    return Path(os.getenv("INTEGRAL_DATA_DIR") or os.getenv("DATA_DIR") or r"E:\data")


def _config_rutas_copia(conexion: str) -> dict[str, str]:
    defaults = {
        "local": {
            "integral_entrada": r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_integral\Cobranzas Integrales",
            "integral_procesado": r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_integral\Cobranzas Integrales Procesado",
            "cobranza_base": r"D:\Develop\ETL\Nicaragua_Proceso\unidad_red_integral",
        },
        "remoto": {
            "integral_entrada": r"\\10.24.90.118\Vencorp\COBRANZA %\2024\ Prueba_carga_diaria_Aster_voip\Cobranzas Integrales",
            "integral_procesado": r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip\Cobranzas Integrales Procesado",
            "cobranza_base": r"Z:\COBRANZA %\2024\Prueba _carga_diaria_Aster_voip",
        },
    }

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            rutas = data.get("integral_diario_v2", {}).get("rutas_copia", {})
            selected = rutas.get(conexion, {})
            base = defaults[conexion].copy()
            base.update({k: v for k, v in selected.items() if str(v).strip()})
            return base
        except Exception:
            pass

    return defaults[conexion]


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


class IntegralEntornoService:
    def __init__(self, form):
        self.form = form
        self.contexto = construir_contexto_integral_v2(form)
        self.conexion = _normalizar_conexion(self.contexto.get("conexion") or form.get("conexion") or "local")
        self.fecha = _fecha_tokens(self.contexto.get("fecha_proceso") or form.get("fecha_proceso") or "20260429")
        self.tipo = str(form.get("tipo_proceso") or form.get("tipo") or "discador").strip().lower()
        self.rutas_cfg = _config_rutas_copia(self.conexion)
        self.data_base = _data_dir() / self.fecha["yyyymmdd"]
        self.tiempos: list[dict[str, Any]] = []
        self.advertencias: list[str] = []
        self.carpetas_locales: list[dict[str, Any]] = []
        self.rutas_base: list[dict[str, Any]] = []

    def _add_dir(self, grupo: str, nombre: str, path: Path, crear: bool) -> None:
        creado = False
        if crear and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            creado = True

        self.carpetas_locales.append({
            "grupo": grupo,
            "nombre": nombre,
            "ruta": str(path),
            "existe": path.exists(),
            "creada": creado,
            "estado": "Correcto" if path.exists() else "No existe",
        })

    def _crear_carpetas_locales(self):
        carpetas = [
            ("Base", "Fecha proceso", self.data_base),
            ("Integral", "00_entrada", self.data_base / "Integral" / "00_entrada"),
            ("Integral", "01_trabajo", self.data_base / "Integral" / "01_trabajo"),
            ("Integral", "02_validado", self.data_base / "Integral" / "02_validado"),
            ("Integral", "03_preventivo", self.data_base / "Integral" / "03_preventivo"),
            ("Integral", "04_oficial", self.data_base / "Integral" / "04_oficial"),
            ("Integral", "05_cubo", self.data_base / "Integral" / "05_cubo"),
            ("Integral", "06_final", self.data_base / "Integral" / "06_final"),
            ("Integral", "07_temporal", self.data_base / "Integral" / "07_temporal"),
            ("Consolidado", "04_compromiso", self.data_base / "Consolidado" / "Gestion" / "04_compromiso"),
        ]

        for grupo, nombre, path in carpetas:
            self._add_dir(grupo, nombre, path, crear=True)

        return len(carpetas), "Carpetas locales de trabajo creadas/verificadas."

    def _validar_rutas_base(self):
        mes_folder = f"{self.fecha['mes_nombre']}_{self.fecha['mes_gestion']}"
        microvoz_folder = f"Microvoz_{self.fecha['mes_nombre']}_{self.fecha['yy']}"

        checks = [
            ("Entrada Integral", "integral_entrada", Path(self.rutas_cfg["integral_entrada"]), "Lectura/búsqueda de archivos Integral."),
            ("Procesado Integral", "integral_procesado", Path(self.rutas_cfg["integral_procesado"]), "Base destino SDD para Cobranzas Integrales Procesado."),
            ("Mes procesado", f"{mes_folder}", Path(self.rutas_cfg["integral_procesado"]) / mes_folder, "Carpeta mensual: Abril_YYYYMM."),
            ("Preventivo", "Preventivo", Path(self.rutas_cfg["integral_procesado"]) / mes_folder / "Preventivo", "Destino Integral/Discador."),
            ("Churn", "Churn", Path(self.rutas_cfg["integral_procesado"]) / mes_folder / "Churn", "Destino Manual."),
            ("Cobranza base", "cobranza_base", Path(self.rutas_cfg["cobranza_base"]), "Base destino SDD para Microvoz_MM_YY."),
            ("Microvoz", microvoz_folder, Path(self.rutas_cfg["cobranza_base"]) / microvoz_folder, "Se crea en Fase J si no existe y la base existe."),
        ]

        self.rutas_base = []
        for grupo, nombre, path, detalle in checks:
            existe = path.exists()
            self.rutas_base.append({
                "grupo": grupo,
                "nombre": nombre,
                "ruta": str(path),
                "existe": existe,
                "estado": "Correcto" if existe else "Sin conexión / No existe",
                "detalle": detalle,
            })

        faltantes = [x for x in self.rutas_base if not x["existe"]]
        if faltantes:
            self.advertencias.append("Hay rutas base no disponibles. No detiene el flujo local, pero deben revisarse antes de la copia final.")

        return len(checks), f"Rutas base verificadas. Observaciones: {len(faltantes)}"

    def ejecutar(self) -> dict[str, Any]:
        inicio_total = _now()
        total_t0 = perf_counter()

        for codigo, paso, entrada, func in [
            ("INT-ENV-DIR", "Crear/verificar carpetas locales", str(self.data_base), self._crear_carpetas_locales),
            ("INT-ENV-RUTAS", "Validar rutas base LOCAL/REMOTO", self.conexion.upper(), self._validar_rutas_base),
        ]:
            fila, warn = _step(codigo, paso, entrada, func)
            self.tiempos.append(fila)
            if warn:
                self.advertencias.append(warn)

        estado = "Correcto" if not self.advertencias else "Revisar"
        mensaje = "Entorno preparado." if estado == "Correcto" else "Entorno preparado con observaciones de rutas."

        fin_total = _now()
        total_seg = round(perf_counter() - total_t0, 2)

        self.tiempos.append({
            "#": None,
            "Código": "INT-ENV-TOTAL",
            "Paso": "Total fase B",
            "Estado": estado,
            "Inicio": inicio_total,
            "Fin": fin_total,
            "Seg.": f"{total_seg:.2f}",
            "Entrada": f"{self.fecha['yyyymmdd']} / {self.conexion.upper()}",
            "Salida": f"Advertencias {len(self.advertencias)}",
            "Mensaje": mensaje,
        })

        return {
            "codigo": "B",
            "titulo": "Carpetas y rutas",
            "estado": estado,
            "mensaje": mensaje,
            "inicio": inicio_total,
            "fin": fin_total,
            "duracion_segundos": total_seg,
            "tiempos": _enumerar(self.tiempos),
            "advertencias": self.advertencias,
            "carpetas_locales": self.carpetas_locales,
            "rutas_base": self.rutas_base,
            "detalle": {
                "conexion": self.conexion.upper(),
                "fecha_proceso": self.fecha["yyyymmdd"],
                "fecha_sql": self.fecha["sql"],
                "mes_gestion": self.fecha["mes_gestion"],
                "mes_nombre": self.fecha["mes_nombre"],
                "tipo_proceso": self.tipo,
                "data_base": str(self.data_base),
            },
        }


def preparar_entorno_integral_v2(form) -> dict[str, Any]:
    return IntegralEntornoService(form).ejecutar()
