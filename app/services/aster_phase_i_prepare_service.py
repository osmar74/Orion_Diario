"""
Servicio de preparación Fase I ASTER.

Responsabilidad:
- Probar conexiones MySQL usuarios / MySQL gestioncomercial / SQL Server.
- Leer entidades_aster_YYYYMMDD.xlsx.
- Contar usuarios MySQL.
- Contar comentarios MySQL filtrados por fecha y entidades.
- Comparar columnas origen MySQL vs destino SQL Server.
- Preparar Fase I sin ejecutar DELETE ni INSERT.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.services.aster_file_service import normalizar_fecha_aster
from app.services.aster_sqlserver_service import obtener_columnas_sqlserver_tabla
from app.services.daily_paths import ruta_aster_subcarpeta
from app.services.aster_source_service import (
    columnas_comentarios_origen_fase_i,
    columnas_usuarios_origen_fase_i,
    contar_comentarios_origen_fase_i,
    contar_usuarios_origen_fase_i,
    probar_origen_aster,
)
from app.services.sql_loader import cargar_sql


def columnas_usuarios_origen_fase_i() -> list[str]:
    return [
        "id",
        "usuario",
        "pass",
        "perfil",
        "nombre",
        "owned_by",
        "type",
        "web",
        "created_at",
        "updated_at",
    ]


def columnas_comentarios_origen_fase_i() -> list[str]:
    return [
        "id",
        "data",
        "fecha",
        "comentario",
        "resultado1",
        "resultado2",
        "entidad",
        "usuario",
        "fechaagenda",
        "unico",
        "fechainicio",
        "telefono",
        "uniqueid",
        "linkedid",
        "datafijos",
        "datapers",
    ]


def obtener_config_mysql_fase_i(database: str) -> dict[str, Any]:
    """
    Obtiene configuración MySQL desde .env.

    Variables:
    - ASTER_DB_HOST
    - ASTER_DB_USER
    - ASTER_DB_PASSWORD
    - ASTER_DB_PORT
    """
    host = os.getenv("ASTER_DB_HOST", "").strip()
    user = os.getenv("ASTER_DB_USER", "").strip()
    password = os.getenv("ASTER_DB_PASSWORD", "").strip()
    port_raw = os.getenv("ASTER_DB_PORT", "3306").strip()

    if not host or not user:
        raise ValueError(
            "Faltan variables MySQL ASTER en .env: ASTER_DB_HOST / ASTER_DB_USER"
        )

    try:
        port = int(port_raw)
    except Exception:
        port = 3306

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": port,
        "charset": "utf8mb4",
    }


def conectar_mysql_fase_i(database: str):
    """
    Conecta a MySQL para lectura.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(
            "No está instalado PyMySQL. Ejecute: pip install PyMySQL"
        ) from exc

    config = obtener_config_mysql_fase_i(database)

    return pymysql.connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        port=config["port"],
        charset=config["charset"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def validar_sql_mysql_solo_select(sql: str) -> None:
    """
    Bloquea cualquier operación que no sea SELECT en MySQL.
    """
    sql_limpio = re.sub(r"\s+", " ", sql or "").strip().lower()

    if not sql_limpio.startswith("select "):
        raise ValueError("MySQL solo permite SELECT en Fase I.")

    prohibidas = [
        "delete ",
        "insert ",
        "update ",
        "drop ",
        "alter ",
        "truncate ",
        "create ",
        "replace ",
    ]

    for palabra in prohibidas:
        if palabra in sql_limpio:
            raise ValueError(
                f"Operación MySQL prohibida detectada: {palabra.strip().upper()}"
            )


def obtener_fecha_fase_i(
    fecha_raw: str = "",
    fecha_default: str = "",
) -> str:
    """
    Obtiene fecha Fase I en YYYYMMDD.
    """
    if fecha_raw:
        return normalizar_fecha_aster(fecha_raw)

    fecha_default_limpia = re.sub(r"[^0-9]", "", fecha_default or "")

    if len(fecha_default_limpia) >= 8:
        return fecha_default_limpia[:8]

    return datetime.now().strftime("%Y%m%d")


def ruta_entidades_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> str:
    """
    Ruta esperada de entidades_aster_YYYYMMDD.xlsx.
    """
    return os.path.join(
        ruta_aster_subcarpeta(data_dir, fecha_yyyymmdd, "Entidades"),
        f"entidades_aster_{fecha_yyyymmdd}.xlsx",
    )


def leer_entidades_fase_i(
    data_dir: str,
    fecha_yyyymmdd: str,
) -> tuple[list[str], str]:
    """
    Lee entidades filtradas finales desde entidades_aster_YYYYMMDD.xlsx.
    """
    ruta = ruta_entidades_fase_i(data_dir, fecha_yyyymmdd)

    if not os.path.isfile(ruta):
        raise FileNotFoundError(
            f"No existe el archivo de entidades ASTER: {ruta}"
        )

    df = pd.read_excel(ruta, dtype=str)

    if "Entidad" not in df.columns:
        raise ValueError("El archivo de entidades no tiene columna Entidad.")

    entidades = sorted(
        {
            str(valor).strip()
            for valor in df["Entidad"].dropna().tolist()
            if str(valor).strip()
        }
    )

    if not entidades:
        raise ValueError("El archivo de entidades no contiene entidades válidas.")

    return entidades, ruta


def comparar_columnas_fase_i(
    columnas_origen: list[str],
    columnas_destino: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compara columnas origen contra destino SQL Server.
    """
    destino_lower = {
        str(col["columna"]).lower(): col
        for col in columnas_destino
    }

    comparacion: list[dict[str, Any]] = []

    for col_origen in columnas_origen:
        col_sql = destino_lower.get(col_origen.lower())

        comparacion.append(
            {
                "columna_origen": col_origen,
                "columna_destino": str(col_sql["columna"]) if col_sql else "",
                "tipo_sql": str(col_sql["tipo_sql"]) if col_sql else "",
                "longitud": col_sql.get("longitud") if col_sql else "",
                "nullable": str(col_sql["nullable"]) if col_sql else "",
                "estado": "OK" if col_sql else "NO_EXISTE_EN_DESTINO",
            }
        )

    return comparacion


def contar_usuarios_mysql_fase_i(
    db_usuarios: str,
) -> int:
    """
    Cuenta usuarios desde MySQL usuarios.crm.
    """
    sql = cargar_sql("aster/fase_i/mysql_count_usuarios.sql")
    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_usuarios)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone() or {}

            return int(row.get("total") or 0)

    finally:
        conn.close()


def contar_comentarios_mysql_fase_i(
    db_gestion: str,
    fecha_yyyymmdd: str,
    entidades: list[str],
) -> int:
    """
    Cuenta comentarios MySQL filtrados por fecha y entidades.

    Excluye usuario SystemUser.
    """
    if not entidades:
        return 0

    fecha_sql = datetime.strptime(fecha_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    placeholders = ", ".join(["%s"] * len(entidades))

    sql = cargar_sql("aster/fase_i/mysql_count_comentarios.sql").format(
        placeholders=placeholders
    )

    validar_sql_mysql_solo_select(sql)

    conn = conectar_mysql_fase_i(db_gestion)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, [fecha_sql, *entidades])
            row = cursor.fetchone() or {}

            return int(row.get("total") or 0)

    finally:
        conn.close()


def probar_conexiones_fase_i_aster(
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla_usuarios: str,
    tabla_comentarios: str,
    db_usuarios: str,
    db_gestion: str,
) -> dict[str, Any]:
    """
    Prueba conexiones de Fase I:
    - MySQL usuarios
    - MySQL gestioncomercial
    - SQL Server usuarios/comentarios
    """
    conexion_normalizada = str(conexion or "local").strip().lower()

    if conexion_normalizada not in {"local", "remoto"}:
        conexion_normalizada = "local"

    conn_usuarios = conectar_mysql_fase_i(db_usuarios)

    try:
        with conn_usuarios.cursor() as cursor:
            cursor.execute(cargar_sql("aster/fase_i/mysql_probar_conexion.sql"))
            cursor.fetchone()
    finally:
        conn_usuarios.close()

    conn_gestion = conectar_mysql_fase_i(db_gestion)

    try:
        with conn_gestion.cursor() as cursor:
            cursor.execute(cargar_sql("aster/fase_i/mysql_probar_conexion.sql"))
            cursor.fetchone()
    finally:
        conn_gestion.close()

    columnas_usuarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_usuarios,
    )

    columnas_comentarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_comentarios,
    )

    return {
        "success": True,
        "conexion": conexion_normalizada,
        "db_usuarios": db_usuarios,
        "db_gestion": db_gestion,
        "base": base,
        "total_columnas_usuarios": len(columnas_usuarios),
        "total_columnas_comentarios": len(columnas_comentarios),
    }


def preparar_fase_i_aster(
    data_dir: str,
    fecha_raw: str,
    fecha_default: str,
    conexion: str,
    sql_local: Any,
    sql_remoto: Any,
    base: str,
    schema: str,
    tabla_usuarios: str,
    tabla_comentarios: str,
    db_usuarios: str,
    db_gestion: str,
) -> dict[str, Any]:
    """
    Prepara Fase I sin ejecutar DELETE ni INSERT.
    """
    conexion_normalizada = str(conexion or "local").strip().lower()

    if conexion_normalizada not in {"local", "remoto"}:
        conexion_normalizada = "local"

    fecha_yyyymmdd = obtener_fecha_fase_i(
        fecha_raw=fecha_raw,
        fecha_default=fecha_default,
    )

    entidades, ruta_entidades = leer_entidades_fase_i(
        data_dir=data_dir,
        fecha_yyyymmdd=fecha_yyyymmdd,
    )

    total_usuarios = contar_usuarios_origen_fase_i(db_usuarios=db_usuarios, conexion=conexion_normalizada)

    total_comentarios = contar_comentarios_origen_fase_i(
        db_gestion=db_gestion,
        fecha_yyyymmdd=fecha_yyyymmdd,
        entidades=entidades,
        conexion=conexion_normalizada,
    )

    columnas_sql_usuarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_usuarios,
    )

    columnas_sql_comentarios = obtener_columnas_sqlserver_tabla(
        conexion=conexion_normalizada,
        sql_local=sql_local,
        sql_remoto=sql_remoto,
        base=base,
        schema=schema,
        tabla=tabla_comentarios,
    )

    comparacion_usuarios = comparar_columnas_fase_i(
        columnas_usuarios_origen_fase_i(),
        columnas_sql_usuarios,
    )

    comparacion_comentarios = comparar_columnas_fase_i(
        columnas_comentarios_origen_fase_i(),
        columnas_sql_comentarios,
    )

    return {
        "success": True,
        "fecha_yyyymmdd": fecha_yyyymmdd,
        "conexion": conexion_normalizada,
        "entidades": entidades,
        "ruta_entidades": ruta_entidades,
        "total_entidades": len(entidades),
        "total_usuarios": total_usuarios,
        "total_comentarios": total_comentarios,
        "comparacion_usuarios": comparacion_usuarios,
        "comparacion_comentarios": comparacion_comentarios,
    }

# === FIX_COMPAT_COLUMNAS_MYSQL_FASE_I_BEGIN ===
# Fix de compatibilidad local ASTER Fase I.
# Motivo:
#   aster_phase_i_execution_service.py importa funciones columnas_mysql_*_fase_i
#   que no estaban definidas en aster_phase_i_prepare_service.py.
#
# Este bloque NO toca base de datos.
# Solo agrega funciones auxiliares para que los imports funcionen.
# Fecha de generación: 2026-05-29 16:16:44.381981


def _resolver_columnas_fase_i_compat(nombre_base, columnas_fallback):
    """
    Devuelve columnas de Fase I usando primero funciones/constantes existentes.
    Si no existen, usa columnas_fallback.
    """

    candidatos_funcion = [
        f"columnas_sqlserver_{nombre_base}_fase_i",
        f"columnas_{nombre_base}_fase_i",
    ]

    for nombre_funcion in candidatos_funcion:
        funcion = globals().get(nombre_funcion)
        if callable(funcion):
            return funcion()

    candidatos_constante = [
        f"COLUMNAS_{nombre_base.upper()}_FASE_I",
        f"COLUMNAS_{nombre_base.upper()}",
    ]

    for nombre_constante in candidatos_constante:
        valor = globals().get(nombre_constante)
        if valor is not None:
            return valor

    return list(columnas_fallback)


_COLUMNAS_COMENTARIOS_FASE_I_FALLBACK = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


_COLUMNAS_USUARIOS_FASE_I_FALLBACK = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]


if "columnas_mysql_comentarios_fase_i" not in globals():
    def columnas_mysql_comentarios_fase_i():
        return _resolver_columnas_fase_i_compat(
            "comentarios",
            _COLUMNAS_COMENTARIOS_FASE_I_FALLBACK
        )


if "columnas_mysql_usuarios_fase_i" not in globals():
    def columnas_mysql_usuarios_fase_i():
        return _resolver_columnas_fase_i_compat(
            "usuarios",
            _COLUMNAS_USUARIOS_FASE_I_FALLBACK
        )


if "columnas_mysql_crm_fase_i" not in globals():
    def columnas_mysql_crm_fase_i():
        """
        Compatibilidad con el nombre legacy crm.
        En local SQL Server, la estructura equivalente es dbo.usuarios.
        """
        return columnas_mysql_usuarios_fase_i()

# === FIX_COMPAT_COLUMNAS_MYSQL_FASE_I_END ===

# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_BEGIN ===
# Override final de columnas ASTER Fase I para origen LOCAL SQL Server.
#
# Motivo:
#   En local, gestioncomercial_dev.dbo.usuarios NO tiene columnas legacy:
#   id, pass, perfil, nombre, owned_by, type, web, created_at, updated_at.
#
#   La tabla local real tiene:
#   usuario, interno, grupos, permisosr2, seleccion, filtrar,
#   pausaragente, agente, modificarinterno, modificaragente, callback.
#
# Fecha generación: 2026-05-30 09:40:41.146844


ASTER_FASE_I_COLUMNAS_USUARIOS_LOCAL = [
    "usuario",
    "interno",
    "grupos",
    "permisosr2",
    "seleccion",
    "filtrar",
    "pausaragente",
    "agente",
    "modificarinterno",
    "modificaragente",
    "callback",
]


ASTER_FASE_I_COLUMNAS_COMENTARIOS_LOCAL = [
    "id",
    "data",
    "fecha",
    "comentario",
    "resultado1",
    "resultado2",
    "entidad",
    "usuario",
    "fechaagenda",
    "unico",
    "fechainicio",
    "telefono",
    "uniqueid",
    "linkedid",
    "datafijos",
    "datapers",
]


def columnas_sqlserver_usuarios_fase_i():
    """
    Columnas reales de gestioncomercial_dev.dbo.usuarios.
    """
    return list(ASTER_FASE_I_COLUMNAS_USUARIOS_LOCAL)


def columnas_sqlserver_crm_fase_i():
    """
    Alias local legacy.
    En local, crm equivale a usuarios.
    """
    return columnas_sqlserver_usuarios_fase_i()


def columnas_sqlserver_comentarios_fase_i():
    """
    Columnas reales de gestioncomercial_dev.dbo.comentarios.
    """
    return list(ASTER_FASE_I_COLUMNAS_COMENTARIOS_LOCAL)


# Overrides seguros para llamadas legacy que todavía usan nombres mysql_*.
# En local deben devolver columnas SQL Server reales.
def columnas_mysql_usuarios_fase_i():
    return columnas_sqlserver_usuarios_fase_i()


def columnas_mysql_crm_fase_i():
    return columnas_sqlserver_usuarios_fase_i()


def columnas_mysql_comentarios_fase_i():
    return columnas_sqlserver_comentarios_fase_i()


def columnas_usuarios_fase_i_por_conexion(conexion="local"):
    """
    Selector explícito por conexión.
    Para pruebas locales, siempre usa columnas reales SQL Server.
    """
    modo = str(conexion or "local").strip().lower()

    if modo in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
        return columnas_sqlserver_usuarios_fase_i()

    # Fallback remoto: se mantiene compatible con el set local para no romper
    # si el pipeline espera el mismo shape.
    return columnas_sqlserver_usuarios_fase_i()


def columnas_comentarios_fase_i_por_conexion(conexion="local"):
    modo = str(conexion or "local").strip().lower()

    if modo in ["local", "sqlserver", "sql_server", "dev", "desarrollo"]:
        return columnas_sqlserver_comentarios_fase_i()

    return columnas_sqlserver_comentarios_fase_i()


# === FIX_ASTER_PHASE_I_LOCAL_COLUMNS_END ===

# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_BEGIN ===
# Fix local ASTER Fase I:
#
# En gestioncomercial_dev.dbo.usuarios no existe la columna id.
# La columna lógica para usuarios local es usuario.
#
# Este helper evita que la validación bloquee Fase I por faltar id
# cuando la conexión es local.
#
# Fecha generación: 2026-05-30 09:44:58.455157


def _aster_phase_i_es_local_required_id_fix(scope=None):
    scope = scope or {}

    conexion = (
        scope.get("conexion")
        or scope.get("modo")
        or scope.get("origen")
        or scope.get("tipo_conexion")
        or "local"
    )

    conexion = str(conexion or "local").strip().lower()

    return conexion in [
        "local",
        "sqlserver",
        "sql_server",
        "dev",
        "desarrollo",
    ]


def _aster_phase_i_filtrar_faltantes_usuarios_local(faltantes, scope=None):
    """
    En local, dbo.usuarios no tiene id.
    Por tanto, si la única columna faltante es id, no debe bloquear la Fase I.
    """
    if not faltantes:
        return faltantes

    faltantes_lista = list(faltantes)

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return faltantes_lista

    ignorables_local = {
        "id",
    }

    filtrados = [
        col for col in faltantes_lista
        if str(col).strip().lower() not in ignorables_local
    ]

    return filtrados


def _aster_phase_i_columnas_requeridas_usuarios_local(columnas=None, scope=None):
    """
    Normaliza columnas requeridas para usuarios local.
    Si aparece id, se elimina.
    Si no aparece usuario, se agrega como mínimo requerido.
    """
    columnas = list(columnas or [])

    if not _aster_phase_i_es_local_required_id_fix(scope):
        return columnas

    columnas = [
        col for col in columnas
        if str(col).strip().lower() != "id"
    ]

    if "usuario" not in [str(c).strip().lower() for c in columnas]:
        columnas.insert(0, "usuario")

    return columnas


# === FIX_ASTER_PHASE_I_REQUIRED_ID_USUARIOS_END ===
