"""JSON-safe response schemas shared by the UI and future EduAI API routes."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiSchema(BaseModel):
    """Base schema whose instances can be serialized directly as JSON data."""

    model_config = ConfigDict(extra="ignore")


class CatalogRecord(ApiSchema):
    catalog_id: int
    item_type: Literal["Course", "Semester", "Subject"]
    name: str
    course: str = ""
    semester: str = ""
    subject: str = ""
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentRecord(ApiSchema):
    document_id: str
    owner_eduai_id: str
    visibility: Literal["private", "shared"]
    course: str = ""
    semester: str = ""
    subject: str = ""
    document_type: str = "Study material"
    title: str
    original_filename: str
    status: Optional[Literal["indexing", "ready", "failed"]] = None
    chunk_count: int = 0
    created_at: Optional[datetime] = None


class StoredDocumentRecord(DocumentRecord):
    """Internal SQL record; storage paths are kept out of public API schemas."""

    storage_path: str
    mime_type: str


class Citation(ApiSchema):
    title: str
    page: Optional[int] = None


class ChatMessage(ApiSchema):
    message_id: Optional[int] = None
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] = Field(default_factory=list)
    course: str = ""
    semester: str = ""
    subject: str = ""
    feedback: Optional[Literal["helpful", "not_helpful"]] = None
    created_at: Optional[datetime] = None


class ChatSession(ApiSchema):
    session_id: str
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int
    title: str


class PracticeSession(ApiSchema):
    practice_id: str
    course: str = ""
    semester: str = ""
    subject: str = ""
    question_type: str
    question_count: int
    created_at: Optional[datetime] = None


class AdminEvent(ApiSchema):
    admin_eduai_id: str
    action: str
    target: str
    created_at: Optional[datetime] = None


class AdminMetrics(ApiSchema):
    active_users: int
    courses: int
    materials: int
    questions: int


class ModelStatus(ApiSchema):
    embedding_ready: bool
    qwen_ready: bool
    ocr_ready: bool
    reranker_ready: bool = False
    reranker_enabled: bool = True
    vision_ready: bool = False
    vision_enabled: bool = True
    vision_model: str = ""
    gpu_layers: int = 0
    embedding_path: str
    qwen_path: str
    ocr_path: str


class VectorCitation(ApiSchema):
    document_id: str
    title: str
    original_filename: Optional[str] = None
    page: Optional[int] = None


class VectorMatch(ApiSchema):
    id: str
    rank: int
    content: str
    # Chroma's similarity_search_with_score returns a distance: lower is closer.
    distance: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    citation: VectorCitation


class VectorSearchResponse(ApiSchema):
    query: str
    collection: str
    result_count: int
    results: list[VectorMatch] = Field(default_factory=list)


class IngestionResult(DocumentRecord):
    status: Literal["ready"] = "ready"


def json_dict(schema: type[ApiSchema], value: Any) -> dict[str, Any]:
    """Validate a record and turn values such as datetimes into JSON primitives."""
    return schema.model_validate(value).model_dump(mode="json")


def json_dicts(schema: type[ApiSchema], values: list[Any]) -> list[dict[str, Any]]:
    """Validate and serialize a collection of records for JSON/API responses."""
    return [json_dict(schema, value) for value in values]
