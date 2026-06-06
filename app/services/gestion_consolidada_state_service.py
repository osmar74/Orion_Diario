import json
from datetime import datetime
from pathlib import Path
from typing import Any


class GestionConsolidadaStateService:
    """
    Estado oficial backend para Consolidar Gestión v2.

    Guarda estado por:
    - fecha
    - conexión
    - fase

    Esto evita depender de localStorage como fuente principal.
    """

    ESTADOS_VALIDOS = {"Pendiente", "Ejecutando", "Correcto", "Revisar", "Error"}

    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}

        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.state_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _fecha_key(self, fecha: Any) -> str:
        limpia = "".join(ch for ch in str(fecha or "") if ch.isdigit())
        return limpia[:8] if len(limpia) >= 8 else "sin_fecha"

    def _conexion_key(self, conexion: Any) -> str:
        conn = str(conexion or "local").strip().lower()
        return "remoto" if conn == "remoto" else "local"

    def _key(self, fecha: Any, conexion: Any) -> str:
        return f"{self._fecha_key(fecha)}::{self._conexion_key(conexion)}"

    def obtener_estados(self, fecha: Any, conexion: Any = "local") -> dict[str, Any]:
        data = self._load()
        bloque = data.get(self._key(fecha, conexion), {})
        return bloque.get("fases", {})

    def actualizar_fase(
        self,
        fecha: Any,
        conexion: Any,
        codigo: str,
        estado: str,
        detalle: str = "",
        tiene_detalle: bool = False,
    ) -> dict[str, Any]:
        estado = estado if estado in self.ESTADOS_VALIDOS else "Pendiente"
        codigo = str(codigo or "").upper().strip()

        data = self._load()
        key = self._key(fecha, conexion)

        if key not in data:
            data[key] = {
                "fecha": self._fecha_key(fecha),
                "conexion": self._conexion_key(conexion),
                "fases": {},
            }

        data[key]["fases"][codigo] = {
            "codigo": codigo,
            "estado": estado,
            "detalle": str(detalle or ""),
            "tiene_detalle": bool(tiene_detalle),
            "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self._save(data)
        return data[key]["fases"][codigo]

    def reiniciar(self, fecha: Any, conexion: Any = "local") -> None:
        data = self._load()
        key = self._key(fecha, conexion)

        if key in data:
            data.pop(key, None)
            self._save(data)
