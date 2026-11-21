"""Mount all v1 endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, societies, universities, events, policy, generation, exports, dashboard, health, memory

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(universities.router)
api_router.include_router(societies.router)
api_router.include_router(events.router)
api_router.include_router(policy.router)
api_router.include_router(generation.router)
api_router.include_router(exports.router)
api_router.include_router(dashboard.router)
api_router.include_router(memory.router)
