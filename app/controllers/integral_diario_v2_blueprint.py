from __future__ import annotations

from flask import Blueprint

from app.controllers.integral_diario_v2_controller import IntegralDiarioV2Controller


integral_diario_v2_bp = Blueprint("integral_diario_v2", __name__)


@integral_diario_v2_bp.get("/integral-v2")
@integral_diario_v2_bp.get("/integral-diario-v2")
def vista_integral_v2():
    return IntegralDiarioV2Controller.index()


@integral_diario_v2_bp.post("/accion/integral-v2/validar")
def accion_integral_v2_validar():
    return IntegralDiarioV2Controller.validar()
