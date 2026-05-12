import os
import shutil
from typing import Dict, List
from app.config import RED_BASE_PATH


class FileManager:
    """Gestión de archivos y carpetas para los procesos Orion/Aister."""

    def __init__(self, base_path: str):
        self.base_path = base_path

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

        try:
            # Crear la carpeta principal
            os.makedirs(carpeta_principal, exist_ok=True)

            # Crear cada subcarpeta
            for sub in subcarpetas:
                ruta_sub = os.path.join(carpeta_principal, sub)
                os.makedirs(ruta_sub, exist_ok=True)
                rutas_creadas[sub] = ruta_sub

            return {"success": True, "rutas": rutas_creadas}

        except OSError as e:
            return {
                "success": False,
                "error": f"Error al crear la estructura: {str(e)}",
            }

    def verificar_red_y_carpetas(self, fecha_str: str) -> Dict:
        """
        Verifica que la unidad de red y las carpetas año/mes/subcarpetas existan,
        y que contengan archivos con la fecha del proceso.

        Args:
            fecha_str: 'YYYYMM_DD' (ej. '202605_06').

        Returns:
            Dict con success, rutas_validadas, mensajes y archivos_encontrados.
        """
        # Separar año, mes y día
        partes = fecha_str.split("_")
        if len(partes) != 2:
            return {
                "success": False,
                "error": "Formato de fecha inválido. Use YYYYMM_DD.",
            }

        anio = partes[0][:4]
        mes_num = partes[0][4:]  # Dos dígitos del mes
        dia = partes[1]

        # Mapeo de número de mes a nombre en español
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

        fecha_archivo = f"{dia}{mes_num}{anio}"  # formato DDMMYYYY

        rutas = {}
        mensajes = []

        # 1. Verificar acceso a la ruta base de red
        if not os.path.exists(RED_BASE_PATH):
            return {
                "success": False,
                "error": f"No se puede acceder a la unidad de red: {RED_BASE_PATH}",
            }

        # 2. Verificar carpeta del año
        ruta_anio = os.path.join(RED_BASE_PATH, anio)
        if not os.path.isdir(ruta_anio):
            return {
                "success": False,
                "error": f"No se encuentra la carpeta del año {anio} en la red.",
            }
        rutas["anio"] = ruta_anio
        mensajes.append(f"Carpeta año '{anio}' encontrada.")

        # 3. Buscar carpeta del mes con nombre literal (ignorar mayúsculas)
        ruta_mes = None
        try:
            for entry in os.scandir(ruta_anio):
                if entry.is_dir() and entry.name.lower() == mes_nombre:
                    ruta_mes = entry.path
                    break
        except OSError as e:
            return {"success": False, "error": f"Error al leer carpeta año: {e}"}

        if not ruta_mes:
            return {
                "success": False,
                "error": f'No se encuentra la carpeta del mes "{mes_nombre}" dentro de {anio}.',
            }
        rutas["mes"] = ruta_mes
        mensajes.append(f"Carpeta mes '{mes_nombre}' encontrada.")

        # 4. Verificar subcarpetas: Causales, Discador, Lotes
        subcarpetas_esperadas = ["Causales", "Discador", "Lotes"]
        archivos_encontrados = {}
        for sub in subcarpetas_esperadas:
            ruta_sub = os.path.join(ruta_mes, sub)
            if not os.path.isdir(ruta_sub):
                return {
                    "success": False,
                    "error": f"Falta la subcarpeta {sub} en {ruta_mes}.",
                }
            rutas[sub] = ruta_sub

            # 5. Buscar archivos con la fecha del proceso
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
                return {"success": False, "error": f"Error al listar {sub}: {e}"}

        return {
            "success": True,
            "rutas_validadas": rutas,
            "mensajes": mensajes,
            "archivos_encontrados": archivos_encontrados,
        }

    def distribuir_archivos(
        self,
        rutas_red: Dict,
        carpeta_diaria: str,
        archivos_encontrados: Dict
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
        copiados = []
        errores = []

        destinos = {
            'Causales': os.path.join(carpeta_diaria, 'Causales'),
            'Lotes': os.path.join(carpeta_diaria, 'Lotes'),
            # Discador va a la raíz
            'Discador': carpeta_diaria
        }

        for categoria in ['Causales', 'Lotes', 'Discador']:
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
        return {
            'success': success,
            'copiados': copiados,
            'errores': errores
        }

