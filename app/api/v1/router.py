"""Aggregates all /api/v1 route modules.

This router is included ADDITIVELY in app/api/router.py alongside the
existing /templates and /forms routers. Never put prefix="/api/v1" on the
top-level api_router — that would silently move the existing routes.
"""

from fastapi import APIRouter

from app.api.v1.routes import system

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(system.router)
