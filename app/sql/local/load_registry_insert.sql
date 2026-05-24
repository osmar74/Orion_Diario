INSERT OR IGNORE INTO load_history (
    tipo,
    conexion,
    tabla_destino,
    nombre_archivo,
    ruta_archivo,
    archivo_hash,
    registros_archivo,
    registros_insertados,
    fecha_carga
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
