from app.models.integral_models import IntegralProcessParams
from app.repositories.integral_source_repository import IntegralSourceRepository
from app.repositories.integral_destination_repository import IntegralDestinationRepository


class IntegralValidationService:
    """
    Servicio de validación.
    No renderiza HTML.
    No conoce Flask.
    Solo coordina reglas de negocio y devuelve datos limpios.
    """

    def __init__(self, source_repository: IntegralSourceRepository, destination_repository: IntegralDestinationRepository):
        self.source_repository = source_repository
        self.destination_repository = destination_repository

    def validar_conteos(self, params: IntegralProcessParams) -> dict:
        params.validar()

        usuarios_origen = self.source_repository.contar_usuarios()
        comentarios_origen = self.source_repository.contar_comentarios(
            fecha=params.fecha,
            entidad=params.entidad
        )

        usuarios_destino = self.destination_repository.contar_usuarios()
        comentarios_destino = self.destination_repository.contar_comentarios(
            fecha=params.fecha,
            entidad=params.entidad
        )

        return {
            "conexion": params.conexion,
            "fecha": params.fecha,
            "entidad": params.entidad,
            "usuarios": {
                "origen": usuarios_origen,
                "destino": usuarios_destino,
                "coincide": usuarios_origen == usuarios_destino,
            },
            "comentarios": {
                "origen": comentarios_origen,
                "destino": comentarios_destino,
                "coincide": comentarios_origen == comentarios_destino,
            }
        }