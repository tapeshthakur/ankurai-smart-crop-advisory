from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import settings
from database.db import init_db
from routes.auth_routes import auth_bp
from routes.ai_routes import ai_bp
from routes.advisory_routes import advisory_bp
from routes.crop_routes import crop_bp
from routes.disease_routes import disease_bp
from routes.irrigation_routes import irrigation_bp
from routes.market_routes import market_bp
from routes.pest_routes import pest_bp
from routes.system_routes import system_bp
from routes.farm_routes import farm_bp
from leaf_disease.inference import warmup_leaf_disease_model
from leaf_disease.routes import leaf_disease_bp
from utils.logger import setup_logging


def create_app() -> Flask:
    setup_logging()
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = settings.jwt_secret_key
    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins}})

    JWTManager(app)
    init_db()

    app.register_blueprint(ai_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(advisory_bp)
    app.register_blueprint(crop_bp)
    app.register_blueprint(disease_bp)
    app.register_blueprint(leaf_disease_bp)
    app.register_blueprint(irrigation_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(pest_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(farm_bp)
    if os.getenv("FLASK_SKIP_STARTUP_MODEL_WARMUP") != "1":
        warmup_leaf_disease_model()

    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
