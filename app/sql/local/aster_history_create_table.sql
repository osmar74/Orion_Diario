CREATE TABLE IF NOT EXISTS aster_load_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora_registro TEXT NOT NULL,
    fecha_proceso TEXT,
    archivo_excel TEXT,
    conexion TEXT,
    total_general_aster INTEGER,
    filas_excel INTEGER,
    registros_insertados INTEGER,
    estado TEXT,
    mensaje TEXT,
    archivo_reporte_entidades TEXT,
    ruta_reporte_entidades TEXT
)
