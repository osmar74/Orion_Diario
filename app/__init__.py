from flask import Flask

from app.config import SECRET_KEY


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    from app.controllers.main_blueprint import main_bp
    from app.controllers.fases_blueprint import fases_ab_bp
    from app.controllers.ocr_blueprint import ocr_bp
    from app.controllers.procesamiento_blueprint import proc_bp
    from app.controllers.carga_blueprint import carga_bp
    from app.controllers.aster_blueprint import aster_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(fases_ab_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(proc_bp)
    app.register_blueprint(carga_bp)
    app.register_blueprint(aster_bp)

    return app