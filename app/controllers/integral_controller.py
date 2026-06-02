from __future__ import annotations

from flask import redirect


class IntegralController:
    """Compatibilidad con el módulo Integral anterior."""

    @staticmethod
    def index():
        return redirect("/integral-v2")

    @staticmethod
    def panel():
        return redirect("/integral-v2")

    @staticmethod
    def validar():
        return redirect("/integral-v2")
