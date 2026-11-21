"""Session-only state. The application deliberately has no persistence layer."""

from pydantic import BaseModel, Field


class CaseRecord(BaseModel):
    kind: str = "other"
    goal: str = ""
    facts: dict[str, str] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    allegations: list[str] = Field(default_factory=list)
    notice_quotes: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    skipped_fields: list[str] = Field(default_factory=list)
    revision: int = 0
    draft: str = ""
    draft_revision: int = -1
    manually_edited: bool = False
    pending_draft: str | None = None
    generated_draft: str = ""
    pending_generated_draft: str | None = None
    conversation_language: str = "English"
    document_language: str = "English"
    messages: list[dict[str, str]] = Field(default_factory=list)
    last_question: str | None = None
    last_field: str | None = None
    provider_status: str = "Demo rules — no language model connected"
