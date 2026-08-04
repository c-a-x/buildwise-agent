from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from app.knowledge.types import KnowledgeClause


class KnowledgeParseError(ValueError):
    """Raised when a knowledge file cannot be parsed without losing provenance."""


_ARTICLE_PATTERNS = (
    re.compile(r"^\s*(第\s*[0-9一二三四五六七八九十百]+(?:\.[0-9]+)*\s*条)\s*[:：.]?\s*(.*)$"),
    re.compile(r"^\s*((?:Article|ARTICLE)\s+[0-9]+(?:\.[0-9]+)?)\s*[:：.]?\s*(.*)$"),
    re.compile(r"^\s*([0-9]+(?:\.[0-9]+){1,})\s*[:：.]?\s*(.*)$"),
)
_CORE_FIELDS = {
    "id",
    "document_id",
    "title",
    "source",
    "article",
    "category",
    "content",
    "version",
    "effective_date",
    "metadata",
}
_CONTEXT_FIELDS = {"clauses", "articles", "documents", "items"}


def parse_knowledge_file(
    path: Path,
    *,
    source: str | None = None,
    title: str | None = None,
    category: str | None = None,
    version: str = "",
    effective_date: str | None = None,
) -> list[KnowledgeClause]:
    """Parse a JSON, PDF, or DOCX file into source-backed clauses.

    JSON may already contain clause records. PDF and DOCX are accepted only when
    the extracted text has explicit article headings; a generic full-document
    article is intentionally never invented.
    """

    if not path.exists() or not path.is_file():
        raise KnowledgeParseError(f"Knowledge file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return _parse_json(path, source=source, title=title, category=category, version=version, effective_date=effective_date)
    if suffix == ".pdf":
        _require_document_context(path, source=source, title=title, category=category)
        return _parse_extracted_text(
            _extract_pdf_text(path),
            document_id=_stable_document_id(path),
            source=source or "",
            title=title or "",
            category=category or "",
            version=version,
            effective_date=effective_date,
        )
    if suffix == ".docx":
        _require_document_context(path, source=source, title=title, category=category)
        return _parse_extracted_text(
            _extract_docx_text(path),
            document_id=_stable_document_id(path),
            source=source or "",
            title=title or "",
            category=category or "",
            version=version,
            effective_date=effective_date,
        )
    raise KnowledgeParseError(f"Unsupported knowledge file extension: {suffix or '<none>'}")


def _parse_json(
    path: Path,
    *,
    source: str | None,
    title: str | None,
    category: str | None,
    version: str,
    effective_date: str | None,
) -> list[KnowledgeClause]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KnowledgeParseError(f"Unable to read JSON knowledge file: {path}") from exc

    if isinstance(value, list):
        context: Mapping[str, object] = {}
        raw_items: Sequence[object] = value
    elif isinstance(value, dict):
        context = value
        raw_items = _json_items(value)
    else:
        raise KnowledgeParseError("JSON knowledge root must be a list or object")

    if not raw_items:
        raise KnowledgeParseError("JSON knowledge file contains no clauses")

    default_document_id = _text(context.get("document_id") or context.get("id")) or _stable_document_id(path)
    clauses: list[KnowledgeClause] = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise KnowledgeParseError(f"JSON clause at index {index} must be an object")
        item = dict(raw_item)
        item_content = _text(item.get("content"))
        item_article = _text(item.get("article"))
        item_document_id = _text(item.get("document_id")) or default_document_id
        # Existing demo JSON uses one stable id per clause. Preserve it as the
        # document_id when no file-level id was supplied.
        if not context and not item.get("document_id") and item.get("id"):
            item_document_id = _text(item.get("id"))
        item_source = _text(item.get("source")) or _text(context.get("source")) or source or path.name
        item_title = _text(item.get("title")) or _text(context.get("title")) or title or item_article or path.stem
        item_category = _text(item.get("category")) or _text(context.get("category")) or category or "未分类"
        item_version = _text(item.get("version")) or _text(context.get("version")) or version
        item_effective_date = _normalize_date(
            item.get("effective_date") or context.get("effective_date") or effective_date
        )
        metadata = _merge_metadata(context.get("metadata"), item.get("metadata"), item)

        if item_article:
            if not item_content:
                raise KnowledgeParseError(f"JSON clause {item_article} has empty content")
            clauses.append(
                _make_clause(
                    document_id=item_document_id,
                    source=item_source,
                    title=item_title,
                    article=item_article,
                    category=item_category,
                    content=item_content,
                    version=item_version,
                    effective_date=item_effective_date,
                    metadata=metadata,
                )
            )
            continue

        if not item_content:
            raise KnowledgeParseError(f"JSON clause at index {index} has no article or content")
        clauses.extend(
            _parse_extracted_text(
                item_content,
                document_id=item_document_id,
                source=item_source,
                title=item_title,
                category=item_category,
                version=item_version,
                effective_date=item_effective_date,
                base_metadata=metadata,
            )
        )
    return clauses


def _json_items(value: Mapping[str, object]) -> Sequence[object]:
    for key in _CONTEXT_FIELDS:
        candidate = value.get(key)
        if isinstance(candidate, list):
            return candidate
    if "content" in value or "article" in value:
        return [value]
    raise KnowledgeParseError("JSON object must contain clauses, articles, documents, items, or a clause")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf exposes several parser-specific exceptions
        raise KnowledgeParseError(f"Unable to parse PDF knowledge file: {path}") from exc
    return "\n".join(pages)


def _extract_docx_text(path: Path) -> str:
    try:
        from docx import Document

        document = Document(str(path))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
    except Exception as exc:  # python-docx can raise package/zip/XML errors
        raise KnowledgeParseError(f"Unable to parse DOCX knowledge file: {path}") from exc
    return "\n".join(paragraphs)


def _parse_extracted_text(
    text: str,
    *,
    document_id: str,
    source: str,
    title: str,
    category: str,
    version: str,
    effective_date: str | None,
    base_metadata: Mapping[str, object] | None = None,
) -> list[KnowledgeClause]:
    current_article: str | None = None
    current_content: list[str] = []
    clauses: list[KnowledgeClause] = []

    def flush() -> None:
        if current_article is None:
            return
        content = _clean_content(current_content)
        if not content:
            raise KnowledgeParseError(f"Article {current_article} has empty content")
        clauses.append(
            _make_clause(
                document_id=document_id,
                source=source,
                title=title,
                article=current_article,
                category=category,
                content=content,
                version=version,
                effective_date=_normalize_date(effective_date),
                metadata=dict(base_metadata or {}),
            )
        )

    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        match = _match_article(line)
        if match is not None:
            flush()
            current_article, inline_content = match
            current_content = [inline_content] if inline_content else []
        elif current_article is not None:
            current_content.append(line)

    flush()
    if not clauses:
        raise KnowledgeParseError("No explicit article heading found; refusing to invent an article")
    return clauses


def _match_article(line: str) -> tuple[str, str] | None:
    for pattern in _ARTICLE_PATTERNS:
        match = pattern.match(line)
        if match:
            article = re.sub(r"\s+", "", match.group(1)) if match.group(1).startswith("第") else match.group(1).strip()
            return article, match.group(2).strip()
    return None


def _make_clause(
    *,
    document_id: str,
    source: str,
    title: str,
    article: str,
    category: str,
    content: str,
    version: str,
    effective_date: str | None,
    metadata: Mapping[str, object],
) -> KnowledgeClause:
    return KnowledgeClause(
        document_id=document_id.strip(),
        source=source.strip(),
        title=title.strip(),
        article=article.strip(),
        category=category.strip(),
        content=content.strip(),
        version=version.strip(),
        effective_date=effective_date,
        metadata=dict(metadata),
    )


def _merge_metadata(*values: object) -> dict[str, object]:
    merged: dict[str, object] = {}
    for value in values[:-1]:
        if isinstance(value, dict):
            merged.update({str(key): item for key, item in value.items()})
    item = values[-1] if values else None
    if isinstance(item, dict):
        for key, value in item.items():
            if key not in _CORE_FIELDS and key not in _CONTEXT_FIELDS:
                merged.setdefault(str(key), value)
    return merged


def _normalize_date(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")
    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            raise KnowledgeParseError(f"Invalid effective_date: {value}") from exc


def _stable_document_id(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:20]
    return f"DOC-{digest}"


def _require_document_context(path: Path, *, source: str | None, title: str | None, category: str | None) -> None:
    missing = [name for name, value in (("source", source), ("title", title), ("category", category)) if not value]
    if missing:
        raise KnowledgeParseError(f"{path.suffix.upper()} requires explicit {', '.join(missing)}")


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _clean_line(value: str) -> str:
    return re.sub(r"[ \t\u00a0]+", " ", value).strip()


def _clean_content(lines: Sequence[str]) -> str:
    return "\n".join(line for line in (_clean_line(item) for item in lines) if line).strip()
