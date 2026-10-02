from flask import Flask
from flask_cors import CORS

from .config import Config
from .db import init_db


def create_app(config: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    cfg = config or Config
    app.config.from_object(cfg)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    init_db(app)

    from .routes.catalog import bp as catalog_bp
    from .routes.estimate import bp as estimate_bp
    from .routes.insurance import bp as insurance_bp
    from .routes.bills import bp as bills_bp
    from .routes.claims import bp as claims_bp
    from .routes.exposure import bp as exposure_bp
    from .routes.chat import bp as chat_bp
    from .routes.demo import bp as demo_bp

    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(estimate_bp, url_prefix="/api")
    app.register_blueprint(insurance_bp, url_prefix="/api")
    app.register_blueprint(bills_bp, url_prefix="/api")
    app.register_blueprint(claims_bp, url_prefix="/api")
    app.register_blueprint(exposure_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(demo_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {
            "success": True,
            "data": {"status": "ok", "product": "Healthcare Cost Estimator"},
            "warnings": [],
            "assumptions": [],
        }

    return app
