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


from db_case import PostgresCase


class Sprint1Tests(PostgresCase):
    async def test_roles_authentication_and_project_lifecycle(self):
        owner, owner_token = await self.account('owner')
        editor, editor_token = await self.account('editor')
        viewer, viewer_token = await self.account('viewer')
        outsider, outsider_token = await self.account('outsider')
        await self.request('GET', '/projects', 401)
        await self.request('GET', '/auth/me', 401, 'invalid')
        expired = jwt.encode({"sub": owner['id'], "type": "access", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.SECRET_KEY, algorithm='HS256')
        await self.request('GET', '/auth/me', 401, expired)
        await self.request('POST', '/auth/login', 401, body={"email": owner['email'], "password": "wrong-password"})
        await self.request('POST', '/auth/register', 409, body={"email": owner['email'].upper(), "password": "Safe-test-password-42", "full_name": "Duplicate"})
        await self.request('POST', '/auth/register', 422, body={"email": f'{self.prefix}@example.test', "password": "é" * 40, "full_name": "Bytes"})
        await self.request('POST', '/projects', 422, owner_token, {"name": "Spoof", "owner_id": outsider['id']})
        project = await self.request('POST', '/projects', 201, owner_token, {"name": "Sprint test", "description": "Rollback"})
        path = '/projects/' + project['id']
        self.assertEqual(project['owner_id'], owner['id'])
        from uuid import UUID
        snapshot = await self.db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == UUID(project['id'])))
        self.assertIsNotNone(snapshot)
        await self.request('GET', path, 404, outsider_token)
        self.assertEqual(await self.request('GET', '/projects', 200, outsider_token), [])
        await self.request('PUT', path + '/members', 200, owner_token, {"email": editor['email'], "role": "EDITOR"})
        await self.request('PUT', path + '/members', 200, owner_token, {"email": viewer['email'], "role": "VIEWER"})
        for token in (editor_token, viewer_token):
            await self.request('GET', path, 200, token)
            await self.request('DELETE', path, 403, token)
            await self.request('PUT', path + '/members', 403, token, {"email": outsider['email'], "role": "EDITOR"})
        await self.request('PUT', path, 200, editor_token, {"name": "Editor changed"})
        await self.request('PUT', path, 403, viewer_token, {"name": "Forbidden"})
        await self.request('PUT', path + '/members', 422, owner_token, {"email": editor['email'], "role": "OWNER"})
        await self.request('PUT', path + '/members', 409, owner_token, {"email": owner['email'], "role": "VIEWER"})
        await self.request('DELETE', path + '/members/' + owner['id'], 409, owner_token)
        await self.request('PUT', path + '/members', 200, owner_token, {"email": editor['email'], "role": "VIEWER"})
        await self.request('PUT', path, 403, editor_token, {"name": "No longer editor"})
        await self.request('DELETE', path + '/members/' + viewer['id'], 204, owner_token)
        await self.request('GET', path, 404, viewer_token)
        db_user = await self.db.get(User, UUID(outsider['id']))
        db_user.is_active = False
        await self.db.flush()
        await self.request('GET', '/auth/me', 401, outsider_token)
        await self.request('DELETE', path, 204, owner_token)
        await self.request('GET', path, 404, owner_token)
        self.assertIsNone(await self.db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == UUID(project['id']))))
