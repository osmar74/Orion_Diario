from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegralProcessParams:
    conexion: str
    fecha: str
    entidad: str

    def validar(self) -> None:
        if self.conexion not in ("local", "remoto"):
            raise ValueError("La conexión debe ser 'local' o 'remoto'.")

        if not self.fecha:
            raise ValueError("Debe seleccionar una fecha de proceso.")

        if not self.entidad:
            raise ValueError("Debe indicar la entidad del proceso Integral.")
