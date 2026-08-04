from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.db.seed import seed_database  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.knowledge.parsers import KnowledgeParseError, parse_knowledge_file  # noqa: E402
from app.services.knowledge_service import KnowledgeService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导入授权规范条款并更新 BuildWise 知识库")
    parser.add_argument("--input", action="append", dest="inputs", help="JSON、PDF 或 DOCX 文件，可重复指定")
    parser.add_argument("--source", help="PDF/DOCX 的授权来源")
    parser.add_argument("--title", help="PDF/DOCX 的文档标题")
    parser.add_argument("--category", help="PDF/DOCX 的分类")
    parser.add_argument("--version", default="", help="文档版本")
    parser.add_argument("--effective-date", help="生效日期，格式 YYYY-MM-DD")
    parser.add_argument("--rebuild", action="store_true", help="清空当前 Chroma collection 后重建")
    parser.add_argument("--clear", action="store_true", help="与 --rebuild 联用，明确清空 Chroma collection")
    return parser


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), ROOT, BACKEND):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return (Path.cwd() / candidate).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.clear and not arguments.rebuild:
        parser.error("--clear 必须与 --rebuild 一起使用")

    input_paths = [_resolve_path(value) for value in arguments.inputs] if arguments.inputs else [settings.knowledge_json_path]
    clauses = []
    parse_failures: list[dict[str, str]] = []
    for path in input_paths:
        try:
            clauses.extend(
                parse_knowledge_file(
                    path,
                    source=arguments.source,
                    title=arguments.title,
                    category=arguments.category,
                    version=arguments.version,
                    effective_date=arguments.effective_date,
                )
            )
        except KnowledgeParseError as exc:
            parse_failures.append({"path": str(path), "error": str(exc)})

    result: dict[str, object] = {
        "provider": settings.retrieval_provider,
        "input_files": [str(path) for path in input_paths],
        "parsed_count": len(clauses),
        "parse_failures": parse_failures,
    }
    if parse_failures:
        print(json.dumps(result, ensure_ascii=False))
        return 2

    # Preserve the historical command behavior: it also initializes the local
    # SQLite demo data. It never deletes the database; --clear only affects the
    # Chroma projection through KnowledgeService.clear/reindex operations.
    seed_database()
    with SessionLocal() as db:
        service_result = KnowledgeService(db).ingest_clauses(clauses, clear=arguments.rebuild)
    result.update(service_result)
    result.setdefault("created", 0)
    result.setdefault("updated", 0)
    result.setdefault("skipped", 0)
    result.setdefault("deleted", 0)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
