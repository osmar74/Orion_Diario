INSERT INTO aster_load_history (
    fecha_hora_registro,
    fecha_proceso,
    archivo_excel,
    conexion,
    total_general_aster,
    filas_excel,
    registros_insertados,
    estado,
    mensaje,
    archivo_reporte_entidades,
    ruta_reporte_entidades
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
