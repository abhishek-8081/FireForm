import uuid as uuid_mod

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class Template(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    fields: dict = Field(sa_column=Column(JSON, nullable=False))
    pdf_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FormSubmission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="template.id")
    input_text: str
    output_pdf_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(default_factory=lambda: str(uuid_mod.uuid4()), index=True, unique=True)
    celery_task_id: str = Field(index=True)
    job_type: str = Field(default="form_generation")
    template_id: int | None = Field(default=None, foreign_key="template.id")
    input_text: str | None = None
    status: str = Field(default="queued")
    progress_percent: int = Field(default=0)
    result_url: str | None = None
    error: dict | None = Field(default=None, sa_column=Column(JSON))
    model: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))