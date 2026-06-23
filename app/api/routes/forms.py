import requests
from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

from app.api.deps import get_db
from app.api.schemas.forms import (
    FormFill,
    FormFillResponse,
    ModelsResponse,
    TranscriptionResponse,
)
from app.core.config import OLLAMA_HOST, OLLAMA_MODEL, WHISPER_HOST
from app.core.errors.base import AppError
from app.db.repositories import create_form, get_template
from app.models import FormSubmission, Template
from app.services.controller import Controller

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/fill", response_model=FormFillResponse)
def fill_form(form: FormFill, db: Session = Depends(get_db)):

    fetched_template = get_template(db, form.template_id)
    if not fetched_template:
        raise AppError("Template not found", status_code=404, error_code="TEMPLATE_NOT_FOUND")

    controller = Controller()
    try:
        path = controller.fill_form(
            user_input=form.input_text,
            fields=fetched_template.fields,
            pdf_form_path=fetched_template.pdf_path,
            model=form.model,
        )

        # `model` is a runtime override, not a column — keep it out of the DB row.
        submission = FormSubmission(
            **form.model_dump(exclude={"model"}), output_pdf_path=path
        )
        return create_form(db, submission)
    except Exception as e:
        raise AppError(str(e), status_code=500, error_code="FORM_FILL_ERROR")


@router.get("/models", response_model=ModelsResponse)
def list_models():
    """List the Whisper-independent extraction models available in the local
    Ollama instance, plus the configured default. Used by the Fill Form UI's
    model picker. Falls back to just the default if Ollama is unreachable."""
    default_model = OLLAMA_MODEL

    models: list[str] = []
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", []) if m.get("name")]
    except requests.exceptions.RequestException:
        models = []

    # Always surface the configured default, even if Ollama hasn't pulled it yet.
    if default_model not in models:
        models.insert(0, default_model)

    return ModelsResponse(models=models, default=default_model)


@router.post("/transcribe", response_model=TranscriptionResponse)
def transcribe(audio: UploadFile = File(...)):
    """Forward recorded audio to the local Whisper ASR sidecar and return text.

    Mirrors the Ollama wiring: WHISPER_HOST points at the whisper service
    (http://whisper:9000 inside Docker, http://localhost:9000 otherwise). The
    audio is streamed straight through to the local STT service and never
    persisted — no PII leaves the machine.
    """
    whisper_url = f"{WHISPER_HOST}/asr"

    files = {
        "audio_file": (
            audio.filename or "audio.wav",
            audio.file.read(),
            audio.content_type or "audio/wav",
        )
    }
    params = {"task": "transcribe", "output": "json", "encode": "true"}

    try:
        response = requests.post(whisper_url, params=params, files=files, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise AppError(
            f"Could not connect to the speech-to-text service at {whisper_url}. "
            "Please ensure the whisper service is running.",
            status_code=503,
            error_code="STT_UNAVAILABLE",
        )
    except requests.exceptions.RequestException as e:
        raise AppError(f"Transcription failed: {e}", status_code=502, error_code="TRANSCRIPTION_FAILED")

    try:
        text = (response.json().get("text") or "").strip()
    except ValueError:
        text = response.text.strip()

    return TranscriptionResponse(text=text)


@router.get("/submissions")
def get_submissions(db: Session = Depends(get_db)):
    from sqlmodel import select
    statement = (
        select(FormSubmission, Template.name)
        .join(Template, FormSubmission.template_id == Template.id, isouter=True)
        .order_by(FormSubmission.created_at.desc(), FormSubmission.id.desc())
    )
    results = db.exec(statement).all()
    return [
        {
            "id": sub.id,
            "template_id": sub.template_id,
            "template_name": name or "Unknown Template",
            "input_text": sub.input_text,
            "output_pdf_path": sub.output_pdf_path,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }
        for sub, name in results
    ]


@router.get("/submissions/analytics")
def get_submissions_analytics(db: Session = Depends(get_db)):
    from collections import Counter
    import re
    from sqlmodel import select

    statement = select(FormSubmission, Template.name).join(
        Template, FormSubmission.template_id == Template.id, isouter=True
    )
    results = db.exec(statement).all()

    total_submissions = len(results)

    template_counts = Counter()
    daily_counts = Counter()
    words = []

    stopwords = {
        "the", "and", "a", "of", "to", "in", "is", "that", "it", "was", "for", "on",
        "as", "with", "by", "at", "an", "be", "this", "are", "from", "or", "have",
        "has", "had", "but", "not", "he", "she", "they", "we", "i", "you", "my", "his",
        "her", "their", "our", "me", "him", "them", "us", "about", "there", "their",
        "were", "been", "would", "could", "should", "will", "can", "no", "yes", "any",
        "so", "very", "patient", "presents", "with", "reported", "history", "shows",
        "left", "right", "pain", "due", "after", "before", "emergency", "department",
        "medical", "clinical"
    }

    for sub, name in results:
        template_name = name or "Unknown Template"
        template_counts[template_name] += 1

        if sub.created_at:
            date_str = sub.created_at.strftime("%Y-%m-%d")
            daily_counts[date_str] += 1

        if sub.input_text:
            found_words = re.findall(r"\b[a-zA-Z]{3,15}\b", sub.input_text.lower())
            for w in found_words:
                if w not in stopwords:
                    words.append(w)

    sorted_daily = [{"date": k, "count": v} for k, v in sorted(daily_counts.items())]
    sorted_templates = [{"template_name": k, "count": v} for k, v in template_counts.most_common()]
    common_terms = [{"word": k, "count": v} for k, v in Counter(words).most_common(12)]

    return {
        "total_submissions": total_submissions,
        "by_template": sorted_templates,
        "by_date": sorted_daily,
        "common_terms": common_terms,
    }

