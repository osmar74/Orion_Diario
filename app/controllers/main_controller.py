from flask import Blueprint, render_template
from app.services.file_manager import FileManager
from app.config import DATA_DIR

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html', titulo='Orion Procesos')


@main_bp.route('/test-fase2')
def test_fase2():
    """Ruta temporal para probar la creación de carpetas diarias."""
    fm = FileManager(DATA_DIR)
    # Usamos una fecha de ejemplo: 2026-05-12 -> 202605_12
    resultado = fm.crear_estructura_diaria('202605_12')

    if resultado['success']:
        rutas = resultado['rutas']
        html = "<h2>Carpetas creadas correctamente ✅</h2><ul>"
        for key, ruta in rutas.items():
            html += f"<li><strong>{key}:</strong> {ruta}</li>"
        html += "</ul>"
        return html
    else:
        return f"<h2>Error ❌</h2><p>{resultado['error']}</p>"