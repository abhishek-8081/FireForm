"""Extraction service.

Owns the write path that turns a ready input into a queued extraction: it
creates the extraction row, creates the async job, and dispatches the worker.
The route stays a thin HTTP handler and calls straight into here.

The worker itself is stubbed for now (app/tasks/extract.py); the real chunked
extraction is #630.
"""

from datetime import datetime, timezone

from sqlmodel import Session

from app.api.schemas.enums import ExtractionStatus
from app.db.repositories import create_extraction, create_job, update_job
from app.models import Extraction, Job
from app.tasks.extract import extract_task


class ExtractionService:
    def start_extraction(
        self,
        session: Session,
        input_id,
        model_override: str | None = None,
    ) -> tuple[Extraction, Job]:
        """Create the extraction row and job, then dispatch the worker.

        The extraction starts in ``processing`` so a poll right after the 202
        sees the in-flight shape. Mirrors the transcription flow: the job row is
        created first with a known job_id, dispatched, then its celery_task_id
        is backfilled once the broker returns a task id.
        """
        now = datetime.now(timezone.utc)
        extraction = Extraction(
            input_id=input_id,
            status=ExtractionStatus.processing,
            started_at=now,
            model_used=model_override,
            created_at=now,
            updated_at=now,
        )
        extraction = create_extraction(session, extraction)

        job = Job(celery_task_id="", job_type="extraction", status="queued", model=model_override)
        job = create_job(session, job)

        result = extract_task.delay(str(extraction.extract_id), job.job_id)
        job.celery_task_id = result.id
        job = update_job(session, job)

        return extraction, job
