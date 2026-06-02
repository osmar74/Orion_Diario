from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IntegralV2Params:
    conexion: str
    fecha: str
    entidad: str

    def validar(self) -> None:
        if self.conexion not in {"local", "remoto"}:
            raise ValueError("La conexión debe ser 'local' o 'remoto'.")

        if not str(self.fecha or "").strip():
            raise ValueError("Debe indicar la fecha del proceso Integral.")

        if not str(self.entidad or "").strip():
            raise ValueError("Debe indicar la entidad del proceso Integral.")

        self.fecha_sql()

    def fecha_sql(self) -> str:
        raw = str(self.fecha or "").strip()
        limpio = re.sub(r"[^0-9]", "", raw)

        if len(limpio) == 8:
            return datetime.strptime(limpio, "%Y%m%d").strftime("%Y-%m-%d")

        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")

        raise ValueError("Fecha inválida. Use formato YYYYMMDD o YYYY-MM-DD.")
