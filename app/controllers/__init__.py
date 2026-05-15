from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = "123456"

    # Nuevo blueprint de rutas generales
    from app.controllers.main_blueprint import main_bp
    from app.controllers.main_controller import fases_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(fases_bp)

    # Blueprint antiguo (aún contiene las rutas de fases, lo mantendremos hasta migrarlas todas)
    from app.controllers.main_controller import main_bp as old_main_bp

    # Para evitar conflicto de nombres, no registramos el antiguo si ya tenemos el nuevo con el mismo nombre.
    # Pero el blueprint antiguo se llama 'main' también. Para que funcionen ambos, debemos renombrar uno.
    # Solución temporal: no importar el antiguo, o importarlo con otro nombre y no registrarlo todavía.
    # Dado que estamos en transición, dejamos comentado el registro del antiguo para que no haya conflicto.
    # A medida que migremos las rutas, las eliminaremos del antiguo y finalmente lo borraremos.

    return app
