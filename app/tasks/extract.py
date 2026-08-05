import logging
from datetime import datetime, timezone
from uuid import UUID

from app.api.schemas.enums import ExtractionStatus
from app.core.celery import celery_app
from app.db.database import get_session
from app.db.repositories import get_extraction, get_job_by_uuid, update_extraction, update_job

logger = logging.getLogger(__name__)


@celery_app.task(name="extract_incident")
def extract_task(extract_id_str: str, job_id_str: str) -> dict:
    """Stub extraction worker.

    #629 ships the queue slice: the extraction row and job exist and the task
    runs, but the real chunked extraction (split the narrative into field
    groups, call the model, validate, stitch a contract, create the draft
    incident) lands in #630. For now the task only marks the job in-flight and
    leaves the extraction in its ``processing`` state, which is what
    GET /extract/{id} reports back to pollers.
    """
    session = next(get_session())
    extract_id = UUID(extract_id_str)
    try:
        extraction = get_extraction(session, extract_id)
        job = get_job_by_uuid(session, job_id_str)

        now = datetime.now(timezone.utc)
        if extraction:
            extraction.status = ExtractionStatus.processing
            extraction.started_at = extraction.started_at or now
            extraction.updated_at = now
            update_extraction(session, extraction)
        if job:
            job.status = "processing"
            job.updated_at = now
            update_job(session, job)

        logger.info(
            "extract_task stub ran for extraction %s; real worker is #630",
            extract_id_str,
        )
        return {"extract_id": extract_id_str, "job_id": job_id_str}
    finally:
        session.close()
