from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.api.deps import get_db
from app.api.schemas.enums import InputStatus, InputType
from app.api.schemas.input import InputRecordResponse, TextInputRequest, TextInputResponse
from app.core.config import INPUT_POLL_INTERVAL_SECONDS
from app.core.errors.base import AppError
from app.models import Input

router = APIRouter(prefix="/input", tags=["input"])


@router.post("/text", response_model=TextInputResponse, status_code=201)
def submit_text_input(body: TextInputRequest, db: Session = Depends(get_db)):
    narrative = body.narrative

    if len(narrative) > 50_000:
        raise AppError(
            "Narrative exceeds maximum length of 50,000 characters",
            status_code=413,
            error_code="NARRATIVE_TOO_LONG",
            detail={"max_characters": 50_000, "received_characters": len(narrative)},
        )

    words = narrative.split()
    if len(words) < 10:
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": [
                    {
                        "field": "narrative",
                        "issue": "Must contain at least 10 words",
                        "value": narrative,
                    }
                ],
            },
        )

    now = datetime.now(timezone.utc)
    record = Input(
        input_type=InputType.text,
        status=InputStatus.ready,
        transcript=narrative,
        character_count=len(narrative),
        word_count=len(words),
        station_id=body.station_id,
        responder_badge=body.responder_badge,
        incident_date_hint=body.incident_date_hint,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

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
    record = db.exec(select(Input).where(Input.input_id == input_id)).first()
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
