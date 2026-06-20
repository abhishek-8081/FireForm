from pydantic import BaseModel, field_validator


class FormFill(BaseModel):
    template_id: int
    input_text: str
    model: str | None = None

    @field_validator("input_text")
    def validate_input_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Input text cannot be empty")
        return value


class FormFillResponse(BaseModel):
    id: int
    template_id: int
    input_text: str
    output_pdf_path: str

    class Config:
        from_attributes = True


class TranscriptionResponse(BaseModel):
    text: str


class ModelsResponse(BaseModel):
    models: list[str]
    default: str


class AsyncFormFill(BaseModel):
    template_ids: list[int]
    input_text: str
    model: str | None = None

    @field_validator("input_text")
    def validate_input_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Input text cannot be empty")
        return value

    @field_validator("template_ids")
    def validate_template_ids(cls, value):
        if not value:
            raise ValueError("template_ids cannot be empty")
        return value


class JobResponse(BaseModel):
    id: int
    celery_task_id: str
    template_id: int
    status: str
    output_pdf_path: str | None = None
    error: str | None = None

    class Config:
        from_attributes = True


class AsyncFormFillResponse(BaseModel):
    jobs: list[JobResponse]