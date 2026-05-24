CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fase TEXT NOT NULL,
    accion TEXT NOT NULL,
    resultado TEXT NOT NULL CHECK(resultado IN ('éxito', 'error', 'info', 'advertencia')),
    detalle TEXT,
    datos_extra TEXT
)
