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

            if self.log_service:
                self.log_service.log(
                    "2.1",
                    "Crear estructura diaria",
                    "éxito",
                    f"Estructura creada correctamente: {rutas_creadas}",
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
        self, fecha_str: str, red_base_path: str = None
    ) -> Dict:
        """
        Verifica que la unidad de red y las carpetas año/mes/subcarpetas existan,
        y que contengan archivos con la fecha del proceso.
        Si no se pasa red_base_path, busca automáticamente entre las rutas configuradas.

        Args:
            fecha_str: 'YYYYMM_DD' (ej. '202605_06').
            red_base_path: Ruta UNC o unidad mapeada a utilizar (opcional).

        Returns:
            Dict con success, rutas_validadas, mensajes, archivos_encontrados
            y red_base_usada.
        """
        partes = fecha_str.split("_")
        if len(partes) != 2:
            return {
                "success": False,
                "error": "Formato de fecha inválido. Use YYYYMM_DD.",
            }

        anio = partes[0][:4]
        mes_num = partes[0][4:]
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

        fecha_archivo = f"{dia}{mes_num}{anio}"

        rutas = {}
        mensajes = []

        # Determinar ruta base
        if red_base_path is None:
            # Intentar cada ruta configurada
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
                f"Verificando red y carpetas para fecha {fecha_str} "
                f"con ruta base {red_base_path}",
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
        rutas["anio"] = ruta_anio
        mensajes.append(f"Carpeta año '{anio}' encontrada.")

        ruta_mes = None
        try:
            for entry in os.scandir(ruta_anio):
                if entry.is_dir() and entry.name.lower() == mes_nombre:
                    ruta_mes = entry.path
                    break
        except OSError as e:
            if self.log_service:
                self.log_service.log("2.2", "Verificar red y carpetas", "error", str(e))
            return {"success": False, "error": f"Error al leer carpeta año: {e}"}

        if not ruta_mes:
            if self.log_service:
                self.log_service.log(
                    "2.2",
                    "Verificar red y carpetas",
                    "error",
                    f'Carpeta mes "{mes_nombre}" no encontrada.',
                )
            return {
                "success": False,
                "error": f'No se encuentra la carpeta del mes "{mes_nombre}" dentro de {anio}.',
                "red_base_usada": red_base_path,
            }
        rutas["mes"] = ruta_mes
        mensajes.append(f"Carpeta mes '{mes_nombre}' encontrada.")

        subcarpetas_esperadas = ["Causales", "Discador", "Lotes"]
        archivos_encontrados = {}
        for sub in subcarpetas_esperadas:
            ruta_sub = os.path.join(ruta_mes, sub)
            if not os.path.isdir(ruta_sub):
                if self.log_service:
                    self.log_service.log(
                        "2.2",
                        "Verificar red y carpetas",
                        "error",
                        f"Falta la subcarpeta {sub}",
                    )
                return {
                    "success": False,
                    "error": f"Falta la subcarpeta {sub} en {ruta_mes}.",
                    "red_base_usada": red_base_path,
                }
            rutas[sub] = ruta_sub

            try:
                contenidos = os.listdir(ruta_sub)
                archivos_fecha = [f for f in contenidos if fecha_archivo in f]
                archivos_encontrados[sub] = archivos_fecha
                if not archivos_fecha:
                    mensajes.append(
                        f"Advertencia: No se encontraron archivos con fecha {fecha_archivo} en {sub}."
                    )
                else:
                    mensajes.append(
                        f"Encontrados {len(archivos_fecha)} archivo(s) en {sub}."
                    )
            except OSError as e:
                if self.log_service:
                    self.log_service.log(
                        "2.2", "Verificar red y carpetas", "error", str(e)
                    )
                return {"success": False, "error": f"Error al listar {sub}: {e}"}

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
        errores = []

        destinos = {
            "Causales": os.path.join(carpeta_diaria, "Causales"),
            "Lotes": os.path.join(carpeta_diaria, "Lotes"),
            "Discador": carpeta_diaria,
        }

        for categoria in ["Causales", "Lotes", "Discador"]:
            if categoria not in rutas_red or categoria not in archivos_encontrados:
                errores.append(f"Faltan datos de {categoria} para distribuir.")
                continue

            origen_dir = rutas_red[categoria]
            destino_dir = destinos[categoria]
            archivos = archivos_encontrados[categoria]

            if not archivos:
                errores.append(f"No hay archivos que copiar en {categoria}.")
                continue

            for archivo in archivos:
                origen = os.path.join(origen_dir, archivo)
                destino = os.path.join(destino_dir, archivo)
                try:
                    shutil.copy2(origen, destino)
                    copiados.append(destino)
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

        return {"success": success, "copiados": copiados, "errores": errores}
