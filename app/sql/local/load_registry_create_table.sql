CREATE TABLE IF NOT EXISTS load_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    conexion TEXT NOT NULL,
    tabla_destino TEXT NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    archivo_hash TEXT NOT NULL,
    registros_archivo INTEGER NOT NULL,
    registros_insertados INTEGER NOT NULL,
    fecha_carga TEXT NOT NULL,
    UNIQUE(tipo, conexion, tabla_destino, archivo_hash)
)
