# APP/backend/app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from db import init_db
from routes.job_routes import job_bp
from routes.scrape_routes import scrape_bp  # NEW

def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    init_db()
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

    app.register_blueprint(job_bp, url_prefix="/api")
    app.register_blueprint(scrape_bp, url_prefix="/api")  # NEW

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="Bad request"), 400
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found"), 404
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(error="Method not allowed"), 405
    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Internal server error"), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=(Config.FLASK_ENV == "development"))
