"""Aggregates every route module into a single API router.

Add new feature routers here; main.py only mounts this one router.
"""

from fastapi import APIRouter

from app.api.routes import forms, templates, weather, zipcode

api_router = APIRouter()
api_router.include_router(templates.router)
api_router.include_router(forms.router)
api_router.include_router(weather.router)
api_router.include_router(zipcode.router)