from flask import render_template, request

from app.models.integral_models import IntegralProcessParams
from app.repositories.integral_source_repository import IntegralSourceRepository
from app.repositories.integral_destination_repository import IntegralDestinationRepository
from app.services.integral_validation_service import IntegralValidationService

# Ajustar estos imports según las funciones reales existentes en tu proyecto.
# La idea es reutilizar tus conexiones actuales local/remoto.
from app.database.mysql_connection import get_mysql_connection
from app.database.sqlserver_connection import get_sqlserver_connection


class IntegralController:
    """
    Controller del módulo Integral.
    Su tarea es recibir request, llamar servicios y devolver HTML renderizado.
    """

    @staticmethod
    def index():
        return render_template("integral/index.html")

    @staticmethod
    def panel():
        return render_template("integral/partials/panel.html")

    @staticmethod
    def validar():
        try:
            params = IntegralProcessParams(
                conexion=request.form.get("conexion", "local"),
                fecha=request.form.get("fecha", "").strip(),
                entidad=request.form.get("entidad", "").strip(),
            )

            mysql_conn = get_mysql_connection(conexion=params.conexion)
            sqlserver_conn = get_sqlserver_connection(conexion=params.conexion)

            source_repo = IntegralSourceRepository(mysql_conn)
            destination_repo = IntegralDestinationRepository(sqlserver_conn)

            service = IntegralValidationService(source_repo, destination_repo)
            resultado = service.validar_conteos(params)

            mysql_conn.close()
            sqlserver_conn.close()

            return render_template(
                "integral/partials/resultado_validacion.html",
                resultado=resultado
            )

        except Exception as e:
            return render_template(
                "integral/partials/error.html",
                mensaje=str(e)
            ), 500