from flask import Blueprint

from app.controllers.integral_controller import IntegralController


integral_bp = Blueprint(
    "integral",
    __name__,
    url_prefix="/integral"
)


@integral_bp.route("/", methods=["GET"])
def index():
    return IntegralController.index()


@integral_bp.route("/panel", methods=["GET"])
def panel():
    return IntegralController.panel()


@integral_bp.route("/validar", methods=["POST"])
def validar():
    return IntegralController.validar()