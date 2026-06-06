from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class IntegralPasoResultado:
    orden: int
    codigo: str
    nombre: str
    estado: str = "pendiente"
    inicio: str = ""
    fin: str = ""
    segundos: float = 0.0
    registros_entrada: int | None = None
    registros_salida: int | None = None
    mensaje: str = ""
    detalle: dict[str, Any] = field(default_factory=dict)

@dataclass
class IntegralParametros:
    fecha_proceso: str
    tipo_proceso: str = "discador"
    conexion: str = "local"
    entidades: list[str] = field(default_factory=list)
    archivo: str = ""
    modo: str = "validar"

    @property
    def fecha_iso(self) -> str:
        value = str(self.fecha_proceso or "").strip()
        if len(value) == 8 and value.isdigit():
            return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
        return value

    @property
    def fecha_yyyymmdd(self) -> str:
        return self.fecha_iso.replace("-", "")

    @property
    def fecha_ddmmyyyy(self) -> str:
        y, m, d = self.fecha_iso.split("-")
        return f"{d}{m}{y}"

    @property
    def mes_gestion(self) -> int:
        return int(self.fecha_yyyymmdd[:6])

    def validar(self) -> None:
        if self.tipo_proceso not in {"discador", "manual"}:
            raise ValueError("tipo_proceso debe ser discador o manual")
        if self.conexion not in {"local", "remoto"}:
            raise ValueError("conexion debe ser local o remoto")
        if not self.fecha_iso or len(self.fecha_iso) != 10:
            raise ValueError("fecha_proceso debe venir como YYYYMMDD o YYYY-MM-DD")
