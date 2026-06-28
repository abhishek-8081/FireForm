from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from sqlmodel import Session

from app.api.deps import get_db
from app.api.schemas.enums import InputStatus
from app.api.schemas.input import (
    InputRecordResponse,
    TextInputRequest,
    TextInputResponse,
    VoiceInputResponse,
)
from app.core.config import AUDIO_DIR, ESTIMATED_TRANSCRIPTION_SECONDS, INPUT_POLL_INTERVAL_SECONDS
from app.core.errors.base import AppError
from app.db.repositories import create_input, create_job, get_input as repo_get_input, update_job
from app.models import Job
from app.services.input import InputService
from app.services.whisper import check_whisper_available
from app.tasks.transcribe import transcribe_audio_task

router = APIRouter(prefix="/input", tags=["input"])

_ALLOWED_AUDIO_EXTS = {"wav", "mp3", "m4a", "ogg", "webm"}
_MAX_AUDIO_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("/voice", response_model=VoiceInputResponse, status_code=201)
def submit_voice_input(
    audio_file: UploadFile = File(...),
    station_id: str | None = Form(default=None),
    responder_badge: str | None = Form(default=None),
    incident_date_hint: date | None = Form(default=None),
    db: Session = Depends(get_db),
):
    # validate format
    filename = audio_file.filename or ""
    ext = Path(filename).suffix.lstrip(".").lower()
    if not ext or ext not in _ALLOWED_AUDIO_EXTS:
        raise AppError(
            "Audio format not supported. Accepted formats: wav, mp3, m4a, ogg, webm",
            status_code=415,
            error_code="UNSUPPORTED_FORMAT",
            detail={"accepted_formats": ["wav", "mp3", "m4a", "ogg", "webm"]},
        )

    # validate size
    content = audio_file.file.read()
    if len(content) > _MAX_AUDIO_BYTES:
        raise AppError(
            "Audio file exceeds maximum size of 500MB",
            status_code=413,
            error_code="FILE_TOO_LARGE",
            detail={"max_size_bytes": _MAX_AUDIO_BYTES, "received_size_bytes": len(content)},
        )

    # check Whisper availability before queuing
    if not check_whisper_available():
        raise AppError(
            "Whisper transcription service is not available",
            status_code=503,
            error_code="LLM_UNAVAILABLE",
        )

    # build and persist the Input record
    svc = InputService()
    record = svc.build_voice_input(
        original_filename=filename,
        station_id=station_id,
        responder_badge=responder_badge,
        incident_date_hint=incident_date_hint,
    )
    record = create_input(db, record)

    # save audio to DATA_DIR/audio/{input_id}.{ext}
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = AUDIO_DIR / f"{record.input_id}.{ext}"
    audio_path.write_bytes(content)

    # create Job before dispatch to avoid race
    job = Job(celery_task_id="", job_type="transcription", status="queued")
    job = create_job(db, job)

    # dispatch and backfill celery_task_id
    result = transcribe_audio_task.delay(str(record.input_id), str(audio_path), job.job_id)
    job.celery_task_id = result.id
    job = update_job(db, job)

    return VoiceInputResponse(
        input_id=record.input_id,
        status=record.status,
        input_type=record.input_type,
        job_id=job.job_id,
        poll_url=f"/api/v1/input/{record.input_id}",
        estimated_processing_seconds=ESTIMATED_TRANSCRIPTION_SECONDS,
        created_at=record.created_at,
    )


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
