from uuid import UUID

from sqlmodel import Session, select

from app.models import Template, FormSubmission, Job, Input, Extraction, Incident
from app.api.schemas.enums import ReportStatus

# Templates
def create_template(session: Session, template: Template) -> Template:
    session.add(template)
    session.commit()
    session.refresh(template)
    return template

def get_template(session: Session, template_id: int) -> Template | None:
    return session.get(Template, template_id)


def list_templates(session: Session) -> list[Template]:
    statement = select(Template).order_by(Template.created_at.desc(), Template.id.desc())
    return list(session.exec(statement))

# Forms
def create_form(session: Session, form: FormSubmission) -> FormSubmission:
    session.add(form)
    session.commit()
    session.refresh(form)
    return form


# Jobs
def create_job(session: Session, job: Job) -> Job:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job(session: Session, job_id: int) -> Job | None:
    return session.get(Job, job_id)


def get_job_by_uuid(session: Session, job_uuid: str) -> Job | None:
    statement = select(Job).where(Job.job_id == job_uuid)
    return session.exec(statement).first()


def get_job_by_celery_id(session: Session, celery_task_id: str) -> Job | None:
    statement = select(Job).where(Job.celery_task_id == celery_task_id)
    return session.exec(statement).first()


def update_job(session: Session, job: Job) -> Job:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def delete_template(session: Session, template: Template) -> None:
    session.delete(template)
    session.commit()


def get_form_submission(session: Session, submission_id: int) -> FormSubmission | None:
    return session.get(FormSubmission, submission_id)


def delete_form_submission(session: Session, submission: FormSubmission) -> None:
    session.delete(submission)
    session.commit()


# Inputs
def create_input(session: Session, input_obj: Input) -> Input:
    session.add(input_obj)
    session.commit()
    session.refresh(input_obj)
    return input_obj


def get_input(session: Session, input_id: UUID) -> Input | None:
    return session.get(Input, input_id)


def update_input(session: Session, input_obj: Input) -> Input:
    session.add(input_obj)
    session.commit()
    session.refresh(input_obj)
    return input_obj


# Extractions
def create_extraction(session: Session, extraction: Extraction) -> Extraction:
    session.add(extraction)
    session.commit()
    session.refresh(extraction)
    return extraction


def get_extraction(session: Session, extract_id: UUID) -> Extraction | None:
    return session.get(Extraction, extract_id)


def get_extraction_by_input(session: Session, input_id: UUID) -> Extraction | None:
    statement = select(Extraction).where(Extraction.input_id == input_id)
    return session.exec(statement).first()


def update_extraction(session: Session, extraction: Extraction) -> Extraction:
    session.add(extraction)
    session.commit()
    session.refresh(extraction)
    return extraction


# Incidents
def create_incident(session: Session, incident: Incident) -> Incident:
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def get_incident(session: Session, incident_id: UUID) -> Incident | None:
    return session.get(Incident, incident_id)


def get_incident_by_extract(session: Session, extract_id: UUID) -> Incident | None:
    statement = select(Incident).where(Incident.extract_id == extract_id)
    return session.exec(statement).first()


def update_incident(session: Session, incident: Incident) -> Incident:
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def create_draft_incident(session: Session, extract_id: UUID) -> Incident:
    """Create the draft incident row linked to a completed extraction.

    Called when an extraction completes: the new row owns the contract document
    and starts in draft status. POST /incidents later finalizes this same row.
    """
    incident = Incident(extract_id=extract_id, status=ReportStatus.draft)
    return create_incident(session, incident)

