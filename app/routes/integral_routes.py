from __future__ import annotations

from flask import Blueprint, redirect


integral_bp = Blueprint("integral", __name__, url_prefix="/integral")


@integral_bp.get("/")
def index():
    return redirect("/integral-v2")


@integral_bp.get("/panel")
def panel():
    return redirect("/integral-v2")


@integral_bp.post("/validar")
def validar():
    return redirect("/integral-v2")
