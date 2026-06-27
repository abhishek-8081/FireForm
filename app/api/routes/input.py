from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from sqlmodel import Session

from app.api.deps import get_db
from app.api.schemas.enums import InputStatus
from app.api.schemas.input import InputRecordResponse, TextInputRequest, TextInputResponse
from app.core.config import INPUT_POLL_INTERVAL_SECONDS
from app.core.errors.base import AppError
from app.db.repositories import create_input, get_input as repo_get_input
from app.services.input import InputService

router = APIRouter(prefix="/input", tags=["input"])


@router.post("/text", response_model=TextInputResponse, status_code=201)
def submit_text_input(body: TextInputRequest, db: Session = Depends(get_db)):
    if len(body.narrative) > 50_000:
        raise AppError(
            "Narrative exceeds maximum length of 50,000 characters",
            status_code=413,
            error_code="NARRATIVE_TOO_LONG",
            detail={"max_characters": 50_000, "received_characters": len(body.narrative)},
        )

    svc = InputService()
    try:
        record = svc.build_text_input(
            narrative=body.narrative,
            station_id=body.station_id,
            responder_badge=body.responder_badge,
            incident_date_hint=body.incident_date_hint,
        )
    except ValueError as exc:
        raise RequestValidationError(
            errors=[
                {
                    "loc": ("body", "narrative"),
                    "msg": str(exc),
                    "input": body.narrative,
                    "type": "value_error",
                }
            ]
        )

    record = create_input(db, record)

    return TextInputResponse(
        input_id=record.input_id,
        status=record.status,
        input_type=record.input_type,
        character_count=record.character_count,
        word_count=record.word_count,
        created_at=record.created_at,
    )


@router.get("/{input_id}", response_model=InputRecordResponse)
def get_input(input_id: UUID, db: Session = Depends(get_db)):
    record = repo_get_input(db, input_id)
    if record is None:
        raise AppError(
            f"Input with ID {input_id} not found",
            status_code=404,
            error_code="INPUT_NOT_FOUND",
        )

    retry_after = (
        INPUT_POLL_INTERVAL_SECONDS
        if record.status in (InputStatus.queued, InputStatus.transcribing)
        else None
    )
    return InputRecordResponse(
        input_id=record.input_id,
        input_type=record.input_type,
        status=record.status,
        transcript=record.transcript,
        original_filename=record.original_filename,
        audio_duration_seconds=record.audio_duration_seconds,
        character_count=record.character_count,
        word_count=record.word_count,
        station_id=record.station_id,
        responder_badge=record.responder_badge,
        incident_date_hint=record.incident_date_hint,
        error_detail=record.error_detail,
        retry_after_seconds=retry_after,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
