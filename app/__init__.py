from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = (
        "123456"  # Cambia por una cadena aleatoria en producción
    )

    from app.controllers.main_controller import main_bp

    app.register_blueprint(main_bp)

    return app
