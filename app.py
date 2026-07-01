"""Flask application factory ported from Go cmd/rest-server/main.go."""

from __future__ import annotations

import os

from flask import Flask
from flask_cors import CORS

from routes.health import health_bp
from routes.tasks import tasks_bp
from store import TaskStore


def create_app() -> Flask:
    """Create and configure the Flask application.

    Mirrors the Go main(): sets up CORS, creates a ``TaskStore``, and
    registers the tasks and health blueprints.
    """
    app = Flask(__name__)

    # CORS — match Go's corsMiddleware()
    CORS(
        app,
        origins="*",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Origin", "Content-Type", "Accept", "Authorization"],
    )

    # Shared task store (in-memory, seeded with sample data)
    app.config["TASK_STORE"] = TaskStore()

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(tasks_bp)

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    application = create_app()
    application.run(host="0.0.0.0", port=port)
