"""Aggregates every route module into a single API router.

Add new feature routers here; main.py only mounts this one router.
"""

from fastapi import APIRouter

from app.api.routes import forms, templates

api_router = APIRouter()
api_router.include_router(templates.router)
api_router.include_router(forms.router)
