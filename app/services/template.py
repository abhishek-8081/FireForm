import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session

from app.api.schemas.templates import (
    MakeFillableResponse,
    TemplateCreate,
    TemplateResponse,
    TemplateUploadResponse,
)
from app.core.config import BASE_DIR, DEFAULT_TEMPLATE_DIR
from app.db.repositories import (
    create_template,
    delete_template,
    get_jobs_by_template,
    get_submissions_by_template,
    list_templates,
)
from app.models import Template
from app.services.controller import Controller

PROJECT_ROOT = BASE_DIR


def _resolve_target_directory(directory: str) -> Path:
    dir_value = (directory or DEFAULT_TEMPLATE_DIR).strip()
    if not dir_value:
        raise HTTPException(status_code=400, detail="Directory is required.")

    candidate = Path(dir_value)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate != PROJECT_ROOT and PROJECT_ROOT not in candidate.parents:
        raise HTTPException(status_code=400, detail="Directory must be inside the project.")

    return candidate


def _resolve_project_file(file_path: str) -> Path:
    raw_path = (file_path or "").strip()
    if not raw_path:
        raise HTTPException(status_code=400, detail="Path is required.")

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate != PROJECT_ROOT and PROJECT_ROOT not in candidate.parents:
        raise HTTPException(status_code=400, detail="Path must be inside the project.")

    return candidate


# PDF field-type codes -> the type values the frontend field builder uses.
_FIELD_TYPE_BY_FT = {"/Tx": "string", "/Btn": "checkbox", "/Ch": "list", "/Sig": "signature"}


def _pdf_text(value) -> str:
    """Decode a pdfrw string (field name / tooltip) to plain text."""
    if value is None:
        return ""
    if hasattr(value, "to_unicode"):
        return value.to_unicode().strip()
    return str(value).strip()


def _humanize(name: str) -> str:
    """Turn a raw field name into a readable description (JobTitle -> Job Title)."""
    text = re.sub(r"_+", " ", name)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_pdf_fields(pdf_path: str) -> list[dict] | None:
    """Fillable widgets in the same order Filler.fill_form writes them
    (top-to-bottom, left-to-right per page), so seeded rows line up with the
    fill order. Returns None if the PDF can't be read."""
    try:
        from pdfrw import PdfReader
        candidate = Path(pdf_path)
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        pdf = PdfReader(str(candidate))
        fields: list[dict] = []
        for page in pdf.pages:
            widgets = [a for a in (page.Annots or []) if a.Subtype == "/Widget" and a.T]
            widgets.sort(key=lambda a: (-float(a.Rect[1]), float(a.Rect[0])))
            for annot in widgets:
                name = _pdf_text(annot.T)
                fields.append({
                    "name": name,
                    "description": _pdf_text(annot.TU) or _humanize(name),
                    "type": _FIELD_TYPE_BY_FT.get(str(annot.FT), "string"),
                })
        return fields
    except Exception:
        return None


def _count_pdf_widgets(pdf_path: str) -> int | None:
    """Number of fillable widgets in a PDF, or None if unreadable."""
    fields = _extract_pdf_fields(pdf_path)
    return None if fields is None else len(fields)


class TemplateService:
    def __init__(self):
        self.controller = Controller()

    def list_templates(self, session: Session) -> list[Template]:
        return list_templates(session)

    def resolve_pdf_path(self, path: str) -> Path:
        return _resolve_project_file(path)

    def save_uploaded_pdf(self, directory: str, filename: str, content: bytes) -> TemplateUploadResponse:
        target_dir = _resolve_target_directory(directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename
        if target_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            target_path = target_dir / f"{target_path.stem}_{timestamp}{target_path.suffix}"

        with target_path.open("wb") as output_file:
            output_file.write(content)

        relative_path = target_path.relative_to(PROJECT_ROOT).as_posix()
        extracted = _extract_pdf_fields(relative_path)
        return TemplateUploadResponse(
            filename=target_path.name,
            pdf_path=relative_path,
            field_count=None if extracted is None else len(extracted),
            fields=extracted or [],
        )

    def create_template(self, session: Session, template: TemplateCreate) -> TemplateResponse:
        tpl = Template(**template.model_dump())
        created = create_template(session, tpl)
        return TemplateResponse(
            id=created.id,
            name=created.name,
            pdf_path=created.pdf_path,
            fields=created.fields,
            field_count=_count_pdf_widgets(created.pdf_path),
        )

    def make_fillable(self, resolved_pdf_path: str) -> MakeFillableResponse:
        new_absolute = self.controller.prepare_fillable(resolved_pdf_path)
        new_path = Path(new_absolute)
        if not new_path.is_absolute():
            new_path = (PROJECT_ROOT / new_path).resolve()
        relative_path = new_path.relative_to(PROJECT_ROOT).as_posix()

        return MakeFillableResponse(
            pdf_path=relative_path,
            field_count=_count_pdf_widgets(relative_path),
        )

    def delete_template(self, session: Session, template: Template) -> None:
        # Batched like the original route: only session.delete() per row here,
        # single commit at the end (via the delete_template repo call) so the
        # cascade stays atomic instead of partially committing on failure.
        submissions = get_submissions_by_template(session, template.id)
        for sub in submissions:
            if sub.output_pdf_path:
                try:
                    resolved_out = _resolve_project_file(sub.output_pdf_path)
                    if resolved_out.exists() and resolved_out.is_file():
                        resolved_out.unlink()
                except Exception:
                    pass
            session.delete(sub)

        jobs = get_jobs_by_template(session, template.id)
        for job in jobs:
            session.delete(job)

        if template.pdf_path:
            try:
                resolved_pdf = _resolve_project_file(template.pdf_path)
                if resolved_pdf.exists() and resolved_pdf.is_file():
                    resolved_pdf.unlink()
            except Exception:
                pass

        delete_template(session, template)
