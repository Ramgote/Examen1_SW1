from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.canvas import router as canvas_router
from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.endpoints.xmi import router as xmi_router
from app.api.v1.endpoints.generation import router as generation_router
from app.api.v1.endpoints.assistant import router as assistant_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(canvas_router)
api_router.include_router(ws_router)
api_router.include_router(xmi_router)
api_router.include_router(generation_router)
api_router.include_router(assistant_router)
