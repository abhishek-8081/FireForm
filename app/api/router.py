from fastapi import APIRouter

from app.api.routes import extraction, forms, form_templates, input, jobs, system, weather, zipcode
from app.core.config import API_PREFIX

api_router = APIRouter()
api_router.include_router(form_templates.router, prefix=API_PREFIX)
api_router.include_router(forms.router, prefix=API_PREFIX)
api_router.include_router(system.router, prefix=API_PREFIX)
api_router.include_router(jobs.router, prefix=API_PREFIX)
api_router.include_router(weather.router, prefix=API_PREFIX)
api_router.include_router(zipcode.router, prefix=API_PREFIX)
api_router.include_router(input.router, prefix=API_PREFIX)
api_router.include_router(extraction.router, prefix=API_PREFIX)