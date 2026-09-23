import asyncio
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from asyncpg import PostgresError
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine

router = APIRouter(prefix="/health", tags=["Estado del sistema"])
alembic_config = Config(str(Path(__file__).resolve().parents[4] / "alembic.ini"))
expected_heads = set(ScriptDirectory.from_config(alembic_config).get_heads())


@router.get("/live")
async def live():
    """Comprueba el proceso HTTP sin depender de PostgreSQL."""
    return {"status": "ok"}


@router.get("/ready", responses={503: {"description": "Base de datos no preparada"}})
async def ready():
    """Consulta PostgreSQL y verifica la revision Alembic sin modificar datos."""
    try:
        async with asyncio.timeout(5):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                revisions = set((await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )).scalars())
        if revisions != expected_heads:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
    except (SQLAlchemyError, PostgresError, OSError, TimeoutError):
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ok", "database": "ok", "migrations": "ok"}
