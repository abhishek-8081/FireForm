from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.api.schemas.enums import ExtractionStatus, InputStatus
from app.api.schemas.extraction import (
    ExtractionCompleted,
    ExtractionJobResponse,
    ExtractionProcessing,
    ExtractionRequest,
)
from app.api.schemas.incident_contract import IncidentContract
from app.core.config import (
    ESTIMATED_EXTRACTION_SECONDS,
    EXTRACTION_POLL_INTERVAL_SECONDS,
)
from app.core.errors.base import AppError
from app.db.repositories import (
    get_extraction,
    get_extraction_by_input,
    get_incident_by_extract,
    get_input,
)
from app.services.extraction import ExtractionService
from app.services.llm import check_ollama_available

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("/{input_id}", response_model=ExtractionJobResponse, status_code=202)
def create_extraction(
    input_id: UUID,
    body: ExtractionRequest | None = None,
    db: Session = Depends(get_db),
):
    record = get_input(db, input_id)
    if record is None:
        raise AppError(
            f"Input with ID {input_id} not found",
            status_code=404,
            error_code="INPUT_NOT_FOUND",
        )

    if record.status != InputStatus.ready:
        raise AppError(
            f"Input is in '{record.status}' state. Wait until status is 'ready'.",
            status_code=409,
            error_code="INPUT_NOT_READY",
            detail={"current_status": record.status},
        )

    existing = get_extraction_by_input(db, input_id)
    if existing is not None:
        raise AppError(
            "An extraction already exists for this input",
            status_code=409,
            error_code="EXTRACTION_EXISTS",
            detail={"existing_extract_id": str(existing.extract_id)},
        )

    if not check_ollama_available():
        raise AppError(
            "Ollama LLM service is not available",
            status_code=503,
            error_code="LLM_UNAVAILABLE",
        )

    model_override = body.model_override if body else None
    svc = ExtractionService()
    extraction, job = svc.start_extraction(db, input_id, model_override=model_override)

    return ExtractionJobResponse(
        extract_id=extraction.extract_id,
        input_id=input_id,
        job_id=job.job_id,
        status=extraction.status,
        queued_at=extraction.created_at,
        estimated_seconds=ESTIMATED_EXTRACTION_SECONDS,
        poll_url=f"/api/v1/extract/{extraction.extract_id}",
    )


@router.get("/{extract_id}", response_model=ExtractionCompleted | ExtractionProcessing)
def get_extraction_result(extract_id: UUID, db: Session = Depends(get_db)):
    extraction = get_extraction(db, extract_id)
    if extraction is None:
        raise AppError(
            f"Extraction with ID {extract_id} not found",
            status_code=404,
            error_code="EXTRACT_NOT_FOUND",
        )

    if extraction.status == ExtractionStatus.completed:
        incident = get_incident_by_extract(db, extract_id)
        contract = IncidentContract.model_validate(
            (incident.incident_contract if incident else None) or {}
        )
        return ExtractionCompleted(
            extract_id=extraction.extract_id,
            input_id=extraction.input_id,
            incident_id=incident.incident_id if incident else None,
            status="completed",
            incident_contract=contract,
            completed_at=extraction.completed_at,
            model_used=extraction.model_used,
            processing_time_seconds=extraction.processing_time_seconds,
            corrections=extraction.corrections,
        )

    retry_after = (
        EXTRACTION_POLL_INTERVAL_SECONDS
        if extraction.status == ExtractionStatus.processing
        else None
    )
    partial = (
        IncidentContract.model_validate(extraction.partial_result)
        if extraction.partial_result
        else None
    )
    return ExtractionProcessing(
        extract_id=extraction.extract_id,
        input_id=extraction.input_id,
        status=extraction.status,
        started_at=extraction.started_at,
        retry_after_seconds=retry_after,
        error_type=extraction.error_type,
        error_detail=extraction.error_detail,
        partial_result=partial,
    )
