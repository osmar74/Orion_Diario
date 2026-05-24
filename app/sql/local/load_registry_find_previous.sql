SELECT
    id,
    tipo,
    conexion,
    tabla_destino,
    nombre_archivo,
    ruta_archivo,
    archivo_hash,
    registros_archivo,
    registros_insertados,
    fecha_carga
FROM load_history
WHERE tipo = ?
  AND conexion = ?
  AND tabla_destino = ?
  AND archivo_hash = ?
ORDER BY id DESC
LIMIT 1
