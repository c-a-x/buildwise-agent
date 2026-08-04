from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class KnowledgeClause:
    """A source-backed provision normalized for storage and retrieval."""

    document_id: str
    source: str
    title: str
    article: str
    category: str
    content: str
    version: str
    effective_date: str | None
    metadata: dict[str, object] = field(default_factory=dict)
