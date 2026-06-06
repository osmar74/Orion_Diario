from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any

def normalizar_fecha(valor: str) -> str:
    raw = str(valor or "").strip()
    if not raw: raise ValueError("Debe indicar fecha de proceso.")
    if re.fullmatch(r"\d{8}", raw): return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    for sep in ("-", "/"):
        p = raw.split(sep)
        if len(p)==3:
            yyyy, mm, dd = (p if len(p[0])==4 else (p[2], p[1], p[0]))
            return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"
    raise ValueError(f"Formato de fecha inválido: {raw}.")

def fecha_compacta_yyyymmdd(fecha_sql: str) -> str: return normalizar_fecha(fecha_sql).replace("-", "")
def fecha_compacta_ddmmyyyy(fecha_sql: str) -> str:
    y,m,d = normalizar_fecha(fecha_sql).split("-"); return f"{d}{m}{y}"
def mes_gestion(fecha_sql: str) -> int:
    y,m,_ = normalizar_fecha(fecha_sql).split("-"); return int(f"{y}{m}")

@dataclass(frozen=True)
class IntegralV2SddParams:
    fecha_proceso: str
    tipo_proceso: str = "discador"
    conexion: str = "local"
    modo: str = "dry_run"
    entidades: list[str] = field(default_factory=list)
    archivo: str = ""
    def fecha_sql(self) -> str: return normalizar_fecha(self.fecha_proceso)
    def tipo_normalizado(self) -> str:
        v=str(self.tipo_proceso or "discador").strip().lower()
        if v not in {"discador","manual"}: raise ValueError("Tipo debe ser discador o manual.")
        return v
    def conexion_normalizada(self) -> str: return "remoto" if str(self.conexion).strip().lower()=="remoto" else "local"
    def modo_normalizado(self) -> str: return "ejecutar" if str(self.modo).strip().lower() in {"ejecutar","execute","real"} else "dry_run"
    def validar_basico(self) -> None: self.fecha_sql(); self.tipo_normalizado(); self.conexion_normalizada(); self.modo_normalizado()

@dataclass
class IntegralPasoResultado:
    orden:int; codigo:str; nombre:str; estado:str; inicio:str; fin:str; duracion_segundos:float; registros_entrada:int|None=None; registros_salida:int|None=None; mensaje:str=""; detalle:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return self.__dict__

@dataclass
class IntegralPipelineResultado:
    ok:bool; fecha_proceso:str; fecha_sql:str; tipo_proceso:str; conexion:str; modo:str; entidades:list[str]=field(default_factory=list); pasos:list[IntegralPasoResultado]=field(default_factory=list); total_segundos:float=0.0; advertencias:list[str]=field(default_factory=list); errores:list[str]=field(default_factory=list); salidas:dict[str,Any]=field(default_factory=dict)
    def to_dict(self):
        d=self.__dict__.copy(); d["pasos"]=[p.to_dict() for p in self.pasos]; return d
