from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    size_gb: float
    quantization: str | None = None
    loaded: bool


class CurrentLoad(BaseModel):
    active_requests: int
    queued_requests: int


class ComponentHealth(BaseModel):
    status: str
    response_time_ms: int | None = None
    detail: str | None = None
    model_loaded: str | None = None
    ollama_version: str | None = None
    models_available: list[ModelInfo] | None = None
    current_load: CurrentLoad | None = None
    disk_free_gb: float | None = None


class HealthComponents(BaseModel):
    database: ComponentHealth
    ollama: ComponentHealth
    whisper: ComponentHealth
    storage: ComponentHealth


class HealthStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: int | None = None
    components: HealthComponents | None = None


class SchemaVersion(BaseModel):
    version: str
    released_at: str
    changelog: str | None = None
    breaking_changes: bool | None = None


class SchemaFieldEntry(BaseModel):
    """One leaf field of the incident contract, as the catalog exposes it
    (contracts/schemas/template-record.yaml#/SchemaFieldEntry).

    Array hops show as `[]`, so a person's address reads
    `persons_involved[].address`.
    """

    path: str
    label: str | None = None
    field_type: str
    section: str
    description: str | None = None
    enum_values: list[str] | None = None
    pii: bool = False
    aliases: list[str] = []
    # Only set on search results, absent when the whole catalog is listed.
    score: float | None = None


class SchemaFieldSearchResponse(BaseModel):
    """GET /schema/fields response (path/system.yaml#/schema_fields)."""

    query: str | None = None
    total: int
    schema_version: str | None = None
    fields: list[SchemaFieldEntry]
