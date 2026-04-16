from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import templates, forms
from api.db.init_db import init_db
from api.errors.handlers import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database and seed it if necessary
    print("Initializing database...")
    init_db()
    yield
    # Shutdown logic goes here if needed

app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.include_router(templates.router)
app.include_router(forms.router)