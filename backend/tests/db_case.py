"""Integracion contra PostgreSQL existente; todos los datos se revierten."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings, settings
from app.core.database import get_db
from app.models.canvas import CanvasSnapshot
from app.models.user import User
from main import app


@unittest.skipUnless(os.getenv("RUN_DB_TESTS") == "1", "Requiere RUN_DB_TESTS=1 y PostgreSQL")
class PostgresCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        config = Settings(**dotenv_values(Path(__file__).resolve().parents[1] / ".env"))
        # Docker tests use its internal DNS; keep local .env credentials unchanged.
        if os.getenv('TEST_POSTGRES_SERVER'):
            config = config.model_copy(update={'POSTGRES_SERVER': os.environ['TEST_POSTGRES_SERVER'],
                                              'POSTGRES_PORT': int(os.getenv('TEST_POSTGRES_PORT', '5432'))})
        self.engine = create_async_engine(config.SQLALCHEMY_DATABASE_URI)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.db = AsyncSession(bind=self.connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

        async def test_db():
            yield self.db

        app.dependency_overrides[get_db] = test_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.prefix = uuid4().hex

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.db.close()
        await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def request(self, method, path, status, token=None, body=None):
        response = await self.client.request(method, '/api/v1' + path,
                                             headers={"Authorization": f"Bearer {token}"} if token else {},
                                             **({"json": body} if body is not None else {}))
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 else None

    async def account(self, name):
        email = f'{self.prefix}-{name}@example.test'
        body = {"email": email, "password": "Safe-test-password-42", "full_name": name}
        user = await self.request('POST', '/auth/register', 201, body=body)
        self.assertNotIn('hashed_password', user)
        token = await self.request('POST', '/auth/login', 200, body={"email": email, "password": body['password']})
        return user, token['access_token']

