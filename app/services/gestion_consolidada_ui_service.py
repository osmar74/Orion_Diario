class GestionConsolidadaUiService:
    """
    Servicio UI para Consolidar Gestión v2.
    Centraliza las fases para que sidebar y bitácora usen la misma fuente.
    """

    def obtener_fases(self, estados=None):
        estados = estados or {}

        fases = [
            {
                "codigo": "A",
                "nombre": "Preparar archivos",
                "titulo": "Preparar proceso",
                "descripcion": "Crea la estructura Consolidado/Gestion, localiza archivos ORION/ASTER y muestra rutas, nombres, fechas y totales.",
                "boton": "Ejecutar Fase A: Preparar proceso",
                "onclick": "gcEjecutarFaseA()",
                "resultado_id": "gcResultadoFaseA",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "B",
                "nombre": "Unir archivos",
                "titulo": "Unir archivos",
                "descripcion": "Une los Excel de ASTER y ORION, valida encabezados, normaliza Cliente Nro. y genera archivo de unión.",
                "boton": "Ejecutar Fase B: Unir ASTER + ORION",
                "onclick": "gcEjecutarFaseB()",
                "resultado_id": "gcResultadoFaseB",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "C",
                "nombre": "Verificar calidad",
                "titulo": "Verificar calidad",
                "descripcion": "Revisa descripción de gestión, TEL con Asesor/Grabador y duplicidad TEL por Cliente Nro.",
                "boton": "Ejecutar Fase C: Verificar calidad",
                "onclick": "gcEjecutarFaseC()",
                "resultado_id": "gcResultadoFaseC",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "D",
                "nombre": "Ajuste No contestan",
                "titulo": "Ajuste No contestan",
                "descripcion": "Aplica el porcentaje configurado para reemplazo de gestiones No contestan en Home/Mobile.",
                "boton": "Ejecutar Fase D: Ajuste No contestan",
                "onclick": "gcEjecutarFaseD()",
                "resultado_id": "gcResultadoFaseD",
                "resultado_pendiente": "Resultado pendiente.",
                "usa_porcentaje": True,
            },
            {
                "codigo": "E",
                "nombre": "Limpiar nota",
                "titulo": "Limpiar nota",
                "descripcion": "Limpia la columna Nota de la Gestión y genera el archivo depurado correspondiente.",
                "boton": "Ejecutar Fase E: Limpiar Nota de la Gestión",
                "onclick": "gcEjecutarFaseE()",
                "resultado_id": "gcResultadoFaseE",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "F",
                "nombre": "Compromiso",
                "titulo": "Compromiso",
                "descripcion": "Valida acuerdos de pago y Fecha_Compromiso. Cuando corresponde, transforma registros sin fecha a No Hubo Acuerdo.",
                "boton": "Ejecutar Fase F: Compromiso",
                "onclick": "gcEjecutarFaseF()",
                "resultado_id": "gcResultadoFaseF",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "G",
                "nombre": "Generar final",
                "titulo": "Generar final",
                "descripcion": "Genera el archivo final de Gestión, cruza CRM ORION/ASTER y deja preparado el archivo para carga.",
                "boton": "Ejecutar Fase G: Generar archivo final",
                "onclick": "gcEjecutarFaseG()",
                "resultado_id": "gcResultadoFaseG",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "H",
                "nombre": "Archivos generados",
                "titulo": "Archivos generados",
                "descripcion": "Lista los CSV/XLSX creados con nombre, ruta, fecha de creación, modificación, tamaño y filas.",
                "boton": "Ejecutar Fase H: Listar archivos generados",
                "onclick": "gcEjecutarFaseH()",
                "resultado_id": "gcResultadoFaseH",
                "resultado_pendiente": "Resultado pendiente.",
            },
            {
                "codigo": "I",
                "nombre": "Cargar información",
                "titulo": "Cargar información",
                "descripcion": "Carga el archivo final en SQL Server usando la conexión global seleccionada.",
                "boton": "Ejecutar Fase I: Cargar información SQL",
                "onclick": "gcEjecutarFaseI()",
                "resultado_id": "gcResultadoFaseI",
                "resultado_pendiente": "Resultado pendiente.",
            },
        ]

        for fase in fases:
            estado_backend = estados.get(fase["codigo"], {}) or {}
            estado = estado_backend.get("estado", "Pendiente")

            fase["estado"] = estado
            fase["estado_clase"] = self._estado_clase(estado)
            fase["detalle_estado"] = estado_backend.get("detalle", "")
            fase["tiene_detalle"] = bool(estado_backend.get("tiene_detalle", False))

        return fases

    def _estado_clase(self, estado):
        estado = str(estado or "Pendiente").strip().lower()

        if estado == "correcto":
            return "correcto"
        if estado == "revisar":
            return "revisar"
        if estado == "error":
            return "error"
        if estado == "ejecutando":
            return "running"

        return "pending"
