from __future__ import annotations

from flask import render_template, request

from app.models.integral_v2_models import IntegralV2Params
from app.services.integral_v2_validation_service import IntegralV2ValidationService


class IntegralDiarioV2Controller:
    """
    Controller del módulo Integral v2.
    Recibe request, llama servicios y devuelve HTML renderizado por Jinja.
    """

    @staticmethod
    def index():
        return render_template("integral_v2/index.html")

    @staticmethod
    def validar():
        try:
            params = IntegralV2Params(
                conexion=(request.form.get("conexion") or "local").strip().lower(),
                fecha=(request.form.get("fecha") or "").strip(),
                entidad=(request.form.get("entidad") or "").strip(),
            )

            resultado = IntegralV2ValidationService().validar_conteos(params)

            return render_template(
                "integral_v2/partials/_resultado_validacion.html",
                resultado=resultado,
            )

        except Exception as exc:
            return render_template(
                "integral_v2/partials/_error.html",
                mensaje=str(exc),
            ), 500
