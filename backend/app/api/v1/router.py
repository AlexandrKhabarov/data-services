from fastapi import APIRouter

from app.api.v1.endpoints import accounts, analyze, health

api_router = APIRouter()

api_router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
