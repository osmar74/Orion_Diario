import os
import shutil
from typing import Dict, List, Optional

from app.config import RED_BASE_PATHS
from app.services.log_service import LogService


class FileManager:
    """Gestión de archivos y carpetas para los procesos Orion/Aister."""

    def __init__(self, base_path: str, log_service: Optional[LogService] = None):
        self.base_path = base_path
        self.log_service = log_service

    def crear_estructura_diaria(self, fecha_str: str) -> Dict:
        """
        Crea la carpeta diaria con sus subcarpetas.

        Args:
            fecha_str: Cadena en formato 'YYYYMM_DD' (ej. '202605_12').

        Returns:
            Diccionario con 'success' (bool) y 'rutas' (dict de rutas creadas).
        """
        nombre_carpeta = f"orion_{fecha_str}"
        carpeta_principal = os.path.join(self.base_path, nombre_carpeta)

        subcarpetas: List[str] = ["Reporte_Imagen", "Causales", "Lotes", "Discador"]

        rutas_creadas = {"principal": carpeta_principal}

        if self.log_service:
            self.log_service.log(
                "2.1",
                "Crear estructura diaria",
                "info",
                f"Iniciando creación de estructura para {fecha_str}",
            )

        try:
            os.makedirs(carpeta_principal, exist_ok=True)

            for sub in subcarpetas:
                ruta_sub = os.path.join(carpeta_principal, sub)
                os.makedirs(ruta_sub, exist_ok=True)
                rutas_creadas[sub] = ruta_sub

            rutas_no_creadas = []

            for nombre, ruta in rutas_creadas.items():
                if not os.path.isdir(ruta):
                    rutas_no_creadas.append(f"{nombre}: {ruta}")

            if rutas_no_creadas:
                mensaje_error = (
                    "Se intentó crear la estructura, pero estas rutas no existen físicamente: "
                    + " | ".join(rutas_no_creadas)
                )

                if self.log_service:
                    self.log_service.log(
                        "2.1",
                        "Crear estructura diaria",
                        "error",
                        mensaje_error,
                    )

                return {
                    "success": False,
                    "error": mensaje_error,
                    "rutas": rutas_creadas,
                }

            if self.log_service:
                self.log_service.log(
                    "2.1",
                    "Crear estructura diaria",
                    "éxito",
                    f"Estructura creada y verificada correctamente: {rutas_creadas}",
                )

            return {"success": True, "rutas": rutas_creadas}

        except OSError as e:
            if self.log_service:
                self.log_service.log(
                    "2.1",
                    "Crear estructura diaria",
                    "error",
                    f"Error al crear estructura: {str(e)}",
                )
            return {
                "success": False,
                "error": f"Error al crear la estructura: {str(e)}",
            }

    def verificar_red_y_carpetas(
        self, fecha_str: str, red_base_path: Optional[str] = None
    ) -> Dict:
        """
        Verifica unidad de red, carpetas año/mes/subcarpetas y archivos.
        Si no encuentra archivos en la carpeta del mes original, intenta con el mes anterior.
        Busca archivos por DDMMYYYY y, si no hay, por DDMM.
        """
        partes = fecha_str.split("_")
        if len(partes) != 2:
            return {
                "success": False,
                "error": "Formato de fecha inválido. Use YYYYMM_DD.",
            }

        anio = partes[0][:4]
        mes_num = partes[0][4:]  # Dos dígitos del mes
        dia = partes[1]

        meses = {
            "01": "enero",
            "02": "febrero",
            "03": "marzo",
            "04": "abril",
            "05": "mayo",
            "06": "junio",
            "07": "julio",
            "08": "agosto",
            "09": "septiembre",
            "10": "octubre",
            "11": "noviembre",
            "12": "diciembre",
        }
        mes_nombre = meses.get(mes_num)
        if not mes_nombre:
            return {"success": False, "error": f"Mes inválido: {mes_num}"}

        fecha_archivo = f"{dia}{mes_num}{anio}"  # DDMMYYYY
        fecha_alternativa = f"{dia}{mes_num}"  # DDMM (para búsqueda secundaria)

        # Determinar ruta base de red
        if red_base_path is None:
            from app.config import RED_BASE_PATHS

            for path in RED_BASE_PATHS:
                if os.path.exists(path):
                    red_base_path = path
                    break
            else:
                red_base_path = RED_BASE_PATHS[0] if RED_BASE_PATHS else ""

        if self.log_service:
            self.log_service.log(
                "2.2",
                "Verificar red y carpetas",
                "info",
                f"Verificando con ruta base: {red_base_path}",
            )

        if not os.path.exists(red_base_path):
            if self.log_service:
                self.log_service.log(
                    "2.2",
                    "Verificar red y carpetas",
                    "error",
                    f"Unidad de red no accesible: {red_base_path}",
                )
            return {
                "success": False,
                "error": f"No se puede acceder a la unidad de red: {red_base_path}",
                "red_base_usada": red_base_path,
            }

        # Verificar carpeta del año
        ruta_anio = os.path.join(red_base_path, anio)
        if not os.path.isdir(ruta_anio):
            if self.log_service:
                self.log_service.log(
                    "2.2",
                    "Verificar red y carpetas",
                    "error",
                    f"Carpeta año {anio} no encontrada.",
                )
            return {
                "success": False,
                "error": f"No se encuentra la carpeta del año {anio} en la red.",
                "red_base_usada": red_base_path,
            }
        rutas = {"anio": ruta_anio}
        mensajes = [f"Carpeta año '{anio}' encontrada."]

        # --- Función interna para buscar archivos en una carpeta de mes ---
        def buscar_archivos_en_mes(ruta_mes, nombre_mes_usado):
            """Retorna (archivos_encontrados, rutas_subcarpetas, mensajes)."""
            encontrados = {}
            rutas_sub = {}
            msgs = []
            subcarpetas_esperadas = ["Causales", "Discador", "Lotes"]
            for sub in subcarpetas_esperadas:
                ruta_sub = os.path.join(ruta_mes, sub)
                if not os.path.isdir(ruta_sub):
                    msgs.append(f"Falta la subcarpeta {sub} en {nombre_mes_usado}.")
                    continue
                rutas_sub[sub] = ruta_sub
                try:
                    contenidos = os.listdir(ruta_sub)
                    archivos_fecha = [f for f in contenidos if fecha_archivo in f]
                    if archivos_fecha:
                        encontrados[sub] = archivos_fecha
                        msgs.append(
                            f"Encontrados {len(archivos_fecha)} archivo(s) en {sub} ({nombre_mes_usado}, fecha completa)."
                        )
                    else:
                        archivos_alternativos = [
                            f for f in contenidos if fecha_alternativa in f
                        ]
                        if archivos_alternativos:
                            encontrados[sub] = archivos_alternativos
                            msgs.append(
                                f"Encontrados {len(archivos_alternativos)} archivo(s) en {sub} ({nombre_mes_usado}, búsqueda alternativa DDMM)."
                            )
                        else:
                            encontrados[sub] = []
                            msgs.append(
                                f"No se encontraron archivos en {sub} ({nombre_mes_usado})."
                            )
                except OSError as e:
                    msgs.append(f"Error al listar {sub}: {e}")
            return encontrados, rutas_sub, msgs

        # --- Buscar en el mes original ---
        ruta_mes_original = None
        try:
            for entry in os.scandir(ruta_anio):
                if entry.is_dir() and entry.name.lower() == mes_nombre:
                    ruta_mes_original = entry.path
                    break
        except OSError as e:
            if self.log_service:
                self.log_service.log("2.2", "Verificar red y carpetas", "error", str(e))
            return {"success": False, "error": f"Error al leer carpeta año: {e}"}

        archivos_encontrados = {}
        if ruta_mes_original:
            rutas["mes"] = ruta_mes_original
            mensajes.append(f"Carpeta mes '{mes_nombre}' encontrada.")
            archivos_encontrados, rutas_sub, msgs_busqueda = buscar_archivos_en_mes(
                ruta_mes_original, mes_nombre
            )
            rutas.update(rutas_sub)  # <-- AÑADIR ESTO
            mensajes.extend(msgs_busqueda)

        # Si no se encontraron archivos (o no existe la carpeta del mes original) y no es enero, intentar mes anterior
        if (
            not any(archivos_encontrados.values()) or not ruta_mes_original
        ) and mes_num != "01":
            mes_anterior_num = str(int(mes_num) - 1).zfill(2)
            mes_anterior_nombre = meses.get(mes_anterior_num)
            ruta_mes_anterior: Optional[str] = None

            if mes_anterior_nombre:
                try:
                    for entry in os.scandir(ruta_anio):
                        if entry.is_dir() and entry.name.lower() == mes_anterior_nombre:
                            ruta_mes_anterior = entry.path
                            break
                except OSError:
                    pass

            if ruta_mes_anterior and mes_anterior_nombre:
                mensajes.append(
                    f"No se encontraron archivos en '{mes_nombre}'. "
                    f"Buscando en mes anterior: '{mes_anterior_nombre}'."
                )
                archivos_encontrados, rutas_sub, msgs_busqueda = buscar_archivos_en_mes(
                    ruta_mes_anterior, mes_anterior_nombre
                )
                rutas.update(rutas_sub)
                mensajes.extend(msgs_busqueda)
                rutas["mes"] = ruta_mes_anterior

        # Verificar si al final no hay archivos en ninguna subcarpeta
        if not any(archivos_encontrados.values()):
            mensajes.append(
                "No se encontraron archivos en ninguna subcarpeta del mes consultado."
            )
        else:
            mensajes.append("Búsqueda de archivos completada.")

        if self.log_service:
            self.log_service.log(
                "2.2",
                "Verificar red y carpetas",
                "éxito",
                f"Verificación completada. Archivos: {archivos_encontrados}",
            )

        return {
            "success": True,
            "rutas_validadas": rutas,
            "mensajes": mensajes,
            "archivos_encontrados": archivos_encontrados,
            "red_base_usada": red_base_path,
        }

    def distribuir_archivos(
        self, rutas_red: Dict, carpeta_diaria: str, archivos_encontrados: Dict
    ) -> Dict:
        """
        Copia archivos desde las carpetas de red a la estructura local.

        Args:
            rutas_red: Diccionario con rutas de red (Causales, Discador, Lotes).
            carpeta_diaria: Ruta local de la carpeta diaria raíz.
            archivos_encontrados: Diccionario con listas de nombres de archivo
                                  por subcarpeta.

        Returns:
            Dict con success, copiados y errores.
        """
        if self.log_service:
            self.log_service.log(
                "2.3",
                "Distribuir archivos",
                "info",
                "Iniciando copia de archivos desde red a local.",
            )

        copiados = []
        copiados_detalle = []
        errores = []

        destinos = {
            "Causales": os.path.join(carpeta_diaria, "Causales"),
            "Lotes": os.path.join(carpeta_diaria, "Lotes"),
            "Discador": os.path.join(carpeta_diaria, "Discador"),
        }


        for categoria in ["Causales", "Lotes", "Discador"]:
            if categoria not in rutas_red or categoria not in archivos_encontrados:
                errores.append(f"Faltan datos de {categoria} para distribuir.")
                continue

            origen_dir = rutas_red[categoria]
            destino_dir = destinos[categoria]
            archivos = archivos_encontrados[categoria]

            os.makedirs(destino_dir, exist_ok=True)

            if not archivos:
                errores.append(f"No hay archivos que copiar en {categoria}.")
                continue

            for archivo in archivos:
                origen = os.path.join(origen_dir, archivo)
                destino = os.path.join(destino_dir, archivo)

                if not os.path.isfile(origen):
                    errores.append(f"No existe archivo origen en {categoria}: {origen}")
                    continue

                try:
                    shutil.copy2(origen, destino)
                    copiados.append(destino)
                    copiados_detalle.append(
                        {
                            "categoria": categoria,
                            "archivo": archivo,
                            "origen": origen,
                            "destino": destino,
                        }
                    )
                except OSError as e:
                    errores.append(f"Error copiando {archivo}: {e}")

        success = len(errores) == 0
        if self.log_service:
            if success:
                self.log_service.log(
                    "2.3",
                    "Distribuir archivos",
                    "éxito",
                    f"{len(copiados)} archivos copiados.",
                )
            else:
                self.log_service.log(
                    "2.3",
                    "Distribuir archivos",
                    "advertencia",
                    f"Copiados: {len(copiados)}, Errores: {errores}",
                )

        return {
            "success": success,
            "copiados": copiados,
            "copiados_detalle": copiados_detalle,
            "errores": errores,
        }
