import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# La suite aislada no necesita credenciales ni un servidor PostgreSQL real.
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"
os.environ["POSTGRES_PASSWORD"] = "test-only-password"

from fastapi.testclient import TestClient
from asyncpg import ConnectionDoesNotExistError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import make_url

from app.api.v1.endpoints import health
from app.core.config import Settings
from main import app


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_live_does_not_connect_to_database(self):
        with patch.object(health, "engine") as engine:
            engine.connect.side_effect = AssertionError("Unexpected DB access")
            response = self.client.get("/api/v1/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def readiness(self, revisions=None, error=None):
        connection = AsyncMock()
        result = MagicMock()
        result.scalars.return_value = revisions or []
        connection.execute.return_value = result
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=connection, side_effect=error)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.object(health, "engine") as engine:
            engine.connect.return_value = context
            return self.client.get("/api/v1/health/ready")

    def test_ready_requires_current_migrations(self):
        response = self.readiness(health.expected_heads)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["migrations"], "ok")

    def test_old_migration_is_not_ready(self):
        self.assertEqual(self.readiness(["old_revision"]).status_code, 503)

    def test_database_failures_do_not_leak_details(self):
        for error in (SQLAlchemyError("secret connection details"), ConnectionDoesNotExistError(), OSError("host"), TimeoutError()):
            with self.subTest(error=type(error).__name__):
                response = self.readiness(error=error)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"status": "not_ready"})

    def test_cors_allows_frontend_and_rejects_unknown_origin(self):
        for origin, expected in (("http://localhost:5173", 200), ("https://unknown.example", 400)):
            response = self.client.options("/api/v1/health/live", headers={
                "Origin": origin, "Access-Control-Request-Method": "GET",
            })
            self.assertEqual(response.status_code, expected)

    def test_password_special_characters_survive_url_encoding(self):
        password = "p@ss:/word%?#"
        settings = Settings(_env_file=None, POSTGRES_PASSWORD=password)
        self.assertEqual(make_url(settings.SQLALCHEMY_DATABASE_URI).password, password)


if __name__ == "__main__":
    unittest.main()
