# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Callable


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


@dataclass
class IntegralPhaseTimer:
    codigo: str
    titulo: str

    def __enter__(self):
        self.inicio = _now()
        self._t0 = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.fin = _now()
        self.duracion_segundos = round(perf_counter() - self._t0, 2)
        return False

    def resultado(
        self,
        estado: str = "Correcto",
        mensaje: str = "",
        registros_entrada: Any = "-",
        registros_salida: Any = "-",
        tabla: list[dict[str, Any]] | None = None,
        advertencias: list[str] | None = None,
        detalle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "estado": estado,
            "mensaje": mensaje,
            "inicio": getattr(self, "inicio", ""),
            "fin": getattr(self, "fin", ""),
            "duracion_segundos": getattr(self, "duracion_segundos", 0),
            "registros_entrada": registros_entrada,
            "registros_salida": registros_salida,
            "tabla": tabla or [],
            "advertencias": advertencias or [],
            "detalle": detalle or {},
        }


def ejecutar_placeholder(
    codigo: str,
    titulo: str,
    mensaje: str = "Fase pendiente de implementación.",
    estado: str = "Pendiente",
) -> dict[str, Any]:
    inicio = _now()
    t0 = perf_counter()
    fin = _now()

    return {
        "codigo": codigo,
        "titulo": titulo,
        "estado": estado,
        "mensaje": mensaje,
        "inicio": inicio,
        "fin": fin,
        "duracion_segundos": round(perf_counter() - t0, 2),
        "registros_entrada": "-",
        "registros_salida": "-",
        "tabla": [],
        "advertencias": [],
        "detalle": {},
    }


def ejecutar_con_timer(
    codigo: str,
    titulo: str,
    func: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    with IntegralPhaseTimer(codigo, titulo) as timer:
        try:
            resultado = func() or {}
            estado = resultado.get("estado", "Correcto")
            mensaje = resultado.get("mensaje", "Fase ejecutada correctamente.")
            advertencias = resultado.get("advertencias", [])
        except Exception as exc:
            estado = "Error"
            mensaje = str(exc)
            resultado = {}
            advertencias = [str(exc)]

    base = timer.resultado(
        estado=estado,
        mensaje=mensaje,
        registros_entrada=resultado.get("registros_entrada", "-"),
        registros_salida=resultado.get("registros_salida", "-"),
        tabla=resultado.get("tabla", []),
        advertencias=advertencias,
        detalle=resultado.get("detalle", {}),
    )

    for key, value in resultado.items():
        if key not in base:
            base[key] = value

    return base
