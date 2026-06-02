from app.controllers.gestion_consolidada_blueprint import gestion_consolidada_bp
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
    from app.routes.integral_routes import integral_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(fases_ab_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(proc_bp)
    app.register_blueprint(carga_bp)
    app.register_blueprint(aster_bp)
    app.register_blueprint(integral_bp)

    app.register_blueprint(gestion_consolidada_bp)

    from app.controllers.orion_aster_config_blueprint import orion_aster_config_bp
    app.register_blueprint(orion_aster_config_bp)

    from app.controllers.orion_diario_v2_blueprint import orion_diario_v2_bp
    app.register_blueprint(orion_diario_v2_bp)

    from app.controllers.aster_diario_v2_blueprint import aster_diario_v2_bp
    app.register_blueprint(aster_diario_v2_bp)

    from app.controllers.integral_diario_v2_blueprint import integral_diario_v2_bp
    app.register_blueprint(integral_diario_v2_bp)

    return app