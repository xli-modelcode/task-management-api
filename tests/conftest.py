"""Shared pytest fixtures for task-management-api tests."""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so imports work when running
# ``python -m pytest tests/`` from the repository root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app import create_app


@pytest.fixture()
def app():
    """Create a fresh Flask app (and therefore a fresh TaskStore) per test."""
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture()
def client(app):
    """Return a Flask test client backed by the per-test app."""
    return app.test_client()
