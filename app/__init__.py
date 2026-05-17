from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = "orion_secret_key_2026"

    from app.controllers.main_blueprint import main_bp
    from app.controllers.fases_blueprint import fases_ab_bp
    from app.controllers.ocr_blueprint import ocr_bp
    from app.controllers.procesamiento_blueprint import proc_bp
    from app.controllers.carga_blueprint import carga_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(fases_ab_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(proc_bp)
    app.register_blueprint(carga_bp)

    return app