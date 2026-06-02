from __future__ import annotations

from app.models.integral_v2_models import IntegralV2Params
from app.repositories.integral_v2_destination_repository import IntegralV2DestinationRepository
from app.repositories.integral_v2_source_repository import IntegralV2SourceRepository
from app.services.integral_v2_connection_service import IntegralV2ConnectionFactory


class IntegralV2ValidationService:
    """
    Servicio de validación Integral v2.
    No conoce Flask y no renderiza HTML.
    """

    def validar_conteos(self, params: IntegralV2Params) -> dict:
        params.validar()
        fecha_sql = params.fecha_sql()

        factory = IntegralV2ConnectionFactory(params.conexion)

        usuarios_conn = None
        comentarios_conn = None
        destino_conn = None

        try:
            usuarios_conn = factory.abrir_origen_usuarios()
            comentarios_conn = factory.abrir_origen_comentarios()
            destino_conn = factory.abrir_destino()

            source_repo = IntegralV2SourceRepository(
                conexion=params.conexion,
                usuarios_conn=usuarios_conn,
                comentarios_conn=comentarios_conn,
            )
            destination_repo = IntegralV2DestinationRepository(destino_conn)

            usuarios_origen = source_repo.contar_usuarios()
            comentarios_origen = source_repo.contar_comentarios(fecha_sql, params.entidad)
            usuarios_destino = destination_repo.contar_usuarios()
            comentarios_destino = destination_repo.contar_comentarios(fecha_sql, params.entidad)

            return {
                "ok": True,
                "conexion": params.conexion,
                "modo_origen": factory.modo_origen(),
                "fecha": params.fecha,
                "fecha_sql": fecha_sql,
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
                },
                "destino_database": factory.cfg_destino_sqlserver().get("database", ""),
            }

        finally:
            for conn in (usuarios_conn, comentarios_conn, destino_conn):
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
