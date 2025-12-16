from __future__ import annotations

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from werkzeug.exceptions import HTTPException

from .extensions import db
from .routes.health import blp as health_blp
from .routes.notes import blp as notes_blp


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.
    - Configures CORS
    - Sets up Flask-Smorest API/OpenAPI docs
    - Initializes SQLAlchemy with SQLite (file by default, fallback to in-memory on failure)
    - Registers blueprints
    - Adds JSON error handlers
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # CORS for all origins (can be restricted via env later)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # API docs config
    app.config["API_TITLE"] = "My Flask API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Database configuration: use env var or default sqlite file
    db_url = os.getenv("DATABASE_URL", "sqlite:///notes.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    api = Api(app)
    db.init_app(app)

    # Create tables (migrations-lite)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            # If creation fails (e.g., file system read-only), attempt to fallback to memory DB
            app.logger.exception("Failed to initialize database with '%s': %s", db_url, e)
            app.logger.warning("Falling back to in-memory SQLite database (data will not persist).")
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
            db.engine.dispose()
            db.init_app(app)
            with app.app_context():
                db.create_all()

    # Register blueprints
    api.register_blueprint(health_blp)
    api.register_blueprint(notes_blp)

    # Error handlers to return consistent JSON
    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        response = {
            "code": err.code or 500,
            "status": err.name,
            "message": err.description if hasattr(err, "description") else str(err),
        }
        return jsonify(response), err.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        app.logger.exception("Unexpected error: %s", err)
        response = {
            "code": 500,
            "status": "Internal Server Error",
            "message": "An unexpected error occurred.",
        }
        return jsonify(response), 500

    return app


# Keep a module-level app for the existing run.py entrypoint compatibility
app = create_app()
