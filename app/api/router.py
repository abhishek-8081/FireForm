"""Aggregates every route module into a single API router.

Add new feature routers here; main.py only mounts this one router.

IMPORTANT: Never add prefix="/api/v1" to api_router itself — that would
silently move the existing /templates and /forms routes and break the frontend.
New v1 endpoints live in app/api/v1/ and are included via v1_router below.
"""

from fastapi import APIRouter

from app.api.routes import forms, templates
from app.api.v1.router import v1_router
from app.api.routes import forms, templates, weather, zipcode

api_router = APIRouter()
api_router.include_router(templates.router)
api_router.include_router(forms.router)
api_router.include_router(v1_router)

api_router.include_router(weather.router)
api_router.include_router(zipcode.router)